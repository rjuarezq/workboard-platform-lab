from uuid import UUID

from app.models import MembershipRole, WorkspaceMembership


def register_and_login(client, email: str, workspace_name: str) -> dict[str, str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "workspace_name": workspace_name,
        },
    )
    assert registered.status_code == 201

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert logged_in.status_code == 200
    return {
        "token": logged_in.json()["access_token"],
        "user_id": registered.json()["user_id"],
        "workspace_id": registered.json()["workspace"]["id"],
    }


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_project(client, token: str, workspace_id: str, name: str) -> str:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=authorization(token),
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_task(client, token: str, project_id: str) -> str:
    response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=authorization(token),
        json={"title": "Prepare release"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_cross_workspace_task_update_returns_not_found(api) -> None:
    alice = register_and_login(api.client, "alice@example.com", "Alpha")
    bob = register_and_login(api.client, "bob@example.com", "Beta")
    project_id = create_project(api.client, bob["token"], bob["workspace_id"], "Beta project")
    task_id = create_task(api.client, bob["token"], project_id)

    response = api.client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task_id}",
        headers=authorization(alice["token"]),
        json={"title": "Attempted update", "version": 1},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_stale_task_version_returns_conflict(api) -> None:
    alice = register_and_login(api.client, "alice@example.com", "Alpha")
    project_id = create_project(api.client, alice["token"], alice["workspace_id"], "Alpha project")
    task_id = create_task(api.client, alice["token"], project_id)

    first_update = api.client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task_id}",
        headers=authorization(alice["token"]),
        json={"status": "in_progress", "version": 1},
    )
    stale_update = api.client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task_id}",
        headers=authorization(alice["token"]),
        json={"title": "Stale update", "version": 1},
    )

    assert first_update.status_code == 200
    assert first_update.json()["version"] == 2
    assert stale_update.status_code == 409
    assert stale_update.json()["code"] == "task_version_conflict"
    assert stale_update.json()["current_version"] == 2


def test_viewer_cannot_update_visible_task(api) -> None:
    owner = register_and_login(api.client, "owner@example.com", "Alpha")
    viewer = register_and_login(api.client, "viewer@example.com", "Viewer workspace")
    project_id = create_project(api.client, owner["token"], owner["workspace_id"], "Alpha project")
    task_id = create_task(api.client, owner["token"], project_id)

    with api.sessions() as session:
        session.add(
            WorkspaceMembership(
                user_id=UUID(viewer["user_id"]),
                workspace_id=UUID(owner["workspace_id"]),
                role=MembershipRole.VIEWER,
            )
        )
        session.commit()

    response = api.client.patch(
        f"/api/v1/projects/{project_id}/tasks/{task_id}",
        headers=authorization(viewer["token"]),
        json={"title": "Viewer change", "version": 1},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Action is not allowed"}
