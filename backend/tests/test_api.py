from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_task_access import authorization, create_project, create_task, register_and_login

from app.models import MembershipRole, Task, User, WorkspaceMembership


@pytest.fixture
def board(api):
    owner = register_and_login(api.client, "owner@example.com", "Alpha")
    project = create_project(api.client, owner["token"], owner["workspace_id"], "Release")
    task = create_task(api.client, owner["token"], project)
    return owner, project, task


def test_health(api):
    assert api.client.get("/health").json() == {"status": "ok"}


def test_registration_hashes_password_and_duplicate_is_atomic(api, board):
    owner, _, _ = board
    response = api.client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "correct-horse-battery-staple",
            "workspace_name": "Duplicate",
        },
    )
    assert response.status_code == 409
    with api.sessions() as session:
        user = session.get(User, UUID(owner["user_id"]))
        assert user.password_hash.startswith("$argon2")
        assert "correct-horse" not in user.password_hash
    workspaces = api.client.get("/api/v1/workspaces", headers=authorization(owner["token"]))
    assert workspaces.json() == [{"id": owner["workspace_id"], "name": "Alpha", "role": "owner"}]


@pytest.mark.parametrize(
    "email,password",
    [
        ("missing@example.com", "wrong-password"),
        ("owner@example.com", "wrong-password"),
    ],
)
def test_invalid_login_is_generic(api, board, email, password):
    response = api.client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/api/v1/workspaces", None),
        ("GET", f"/api/v1/workspaces/{uuid4()}/projects", None),
        ("POST", f"/api/v1/workspaces/{uuid4()}/projects", {"name": "No"}),
        ("GET", f"/api/v1/projects/{uuid4()}/tasks", None),
        ("POST", f"/api/v1/projects/{uuid4()}/tasks", {"title": "No"}),
        ("PATCH", f"/api/v1/projects/{uuid4()}/tasks/{uuid4()}", {"title": "No", "version": 1}),
    ],
)
def test_every_protected_route_requires_auth(api, method, path, body):
    assert api.client.request(method, path, json=body).status_code == 401


def test_invalid_and_deleted_user_tokens(api):
    from app.core.security import create_access_token

    for token in ("broken-token", create_access_token(uuid4())):
        response = api.client.get("/api/v1/workspaces", headers=authorization(token))
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize("role", [MembershipRole.VIEWER, MembershipRole.EDITOR])
def test_membership_permissions_and_persistence(api, board, role):
    owner, project, task = board
    member = register_and_login(api.client, "member@example.com", "Personal")
    with api.sessions() as session:
        session.add(
            WorkspaceMembership(
                user_id=UUID(member["user_id"]), workspace_id=UUID(owner["workspace_id"]), role=role
            )
        )
        session.commit()
    headers = authorization(member["token"])
    projects_url = f"/api/v1/workspaces/{owner['workspace_id']}/projects"
    tasks_url = f"/api/v1/projects/{project}/tasks"
    assert api.client.get(projects_url, headers=headers).json()[0]["id"] == project
    assert api.client.get(tasks_url, headers=headers).json()[0]["id"] == task
    expected = 403 if role == MembershipRole.VIEWER else 201
    assert (
        api.client.post(projects_url, headers=headers, json={"name": "New"}).status_code == expected
    )
    assert (
        api.client.post(tasks_url, headers=headers, json={"title": "New"}).status_code == expected
    )
    updated = api.client.patch(
        f"{tasks_url}/{task}",
        headers=headers,
        json={"title": "Updated", "status": "done", "version": 1},
    )
    assert updated.status_code == (403 if role == MembershipRole.VIEWER else 200)
    with api.sessions() as session:
        persisted = session.get(Task, UUID(task))
        assert persisted.title == (
            "Prepare release" if role == MembershipRole.VIEWER else "Updated"
        )
        assert persisted.version == (1 if role == MembershipRole.VIEWER else 2)


def test_foreign_and_missing_resources_have_identical_responses(api, board):
    owner, project, task = board
    outsider = register_and_login(api.client, "outsider@example.com", "Other")
    headers = authorization(outsider["token"])
    routes = [
        ("GET", f"/api/v1/workspaces/{owner['workspace_id']}/projects", None),
        ("POST", f"/api/v1/workspaces/{owner['workspace_id']}/projects", {"name": "No"}),
        ("GET", f"/api/v1/projects/{project}/tasks", None),
        ("POST", f"/api/v1/projects/{project}/tasks", {"title": "No"}),
        ("PATCH", f"/api/v1/projects/{project}/tasks/{task}", {"title": "No", "version": 1}),
    ]
    for method, path, body in routes:
        missing = path.replace(owner["workspace_id"], str(uuid4())).replace(project, str(uuid4()))
        foreign_response = api.client.request(method, path, headers=headers, json=body)
        missing_response = api.client.request(method, missing, headers=headers, json=body)
        assert foreign_response.status_code == missing_response.status_code == 404
        assert foreign_response.json() == missing_response.json()
    with api.sessions() as session:
        assert session.get(Task, UUID(task)).version == 1
        assert len(session.scalars(select(Task)).all()) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"title": None},
        {"status": None},
        {"title": ""},
        {"status": "invalid"},
        {"role": "owner"},
        {"workspace_id": str(uuid4())},
        {"description": "x" * 10001},
        {"title": "valid", "version": 0},
    ],
)
def test_invalid_updates_do_not_mutate_task(api, board, changes):
    owner, project, task = board
    response = api.client.patch(
        f"/api/v1/projects/{project}/tasks/{task}",
        headers=authorization(owner["token"]),
        json={"version": 1, **changes},
    )
    assert response.status_code == 422
    with api.sessions() as session:
        assert session.get(Task, UUID(task)).version == 1


def test_description_can_be_cleared_and_stale_write_preserves_state(api, board):
    owner, project, task = board
    headers = authorization(owner["token"])
    url = f"/api/v1/projects/{project}/tasks/{task}"
    first = api.client.patch(url, headers=headers, json={"description": "Details", "version": 1})
    assert first.status_code == 200
    cleared = api.client.patch(url, headers=headers, json={"description": None, "version": 2})
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    stale = api.client.patch(url, headers=headers, json={"title": "Lost write", "version": 1})
    assert stale.status_code == 409
    assert stale.json()["current_version"] == 3
    with api.sessions() as session:
        persisted = session.get(Task, UUID(task))
        assert persisted.title == "Prepare release"
        assert persisted.description is None
        assert persisted.version == 3


def test_task_cannot_be_updated_through_another_project(api, board):
    owner, _, task = board
    other = create_project(api.client, owner["token"], owner["workspace_id"], "Other")
    response = api.client.patch(
        f"/api/v1/projects/{other}/tasks/{task}",
        headers=authorization(owner["token"]),
        json={"title": "No", "version": 1},
    )
    assert response.status_code == 404


def test_conflict_reports_fresh_version_with_cached_session(api, board):
    from app.errors import TaskVersionConflictError
    from app.schemas import TaskUpdate
    from app.services import TaskService

    owner, project, task = board
    with api.sessions() as reader:
        cached_task = reader.get(Task, UUID(task))
        assert cached_task.version == 1
        response = api.client.patch(
            f"/api/v1/projects/{project}/tasks/{task}",
            headers=authorization(owner["token"]),
            json={"title": "Other writer", "version": 1},
        )
        assert response.status_code == 200
        with pytest.raises(TaskVersionConflictError) as conflict:
            TaskService().update_task(
                reader,
                UUID(owner["user_id"]),
                UUID(project),
                UUID(task),
                TaskUpdate(title="Stale writer", version=1),
            )
        assert conflict.value.current_version == 2
        reader.rollback()
    with api.sessions() as session:
        assert session.get(Task, UUID(task)).title == "Other writer"
