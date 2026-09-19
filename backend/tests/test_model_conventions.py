from datetime import UTC, datetime, timedelta
from uuid import RFC_4122, UUID

import pytest
from sqlalchemy import select
from test_task_access import create_project, create_task, register_and_login

from app.core.identifiers import uuid7
from app.core.time import UtcDateTime
from app.models import Project, Task, User, Workspace, WorkspaceMembership


def test_uuid7_has_rfc_version_variant_and_current_utc_timestamp():
    before_ms = int(datetime.now(UTC).timestamp() * 1000)
    identifier = uuid7()
    after_ms = int(datetime.now(UTC).timestamp() * 1000)

    embedded_timestamp_ms = identifier.int >> 80
    assert identifier.version == 7
    assert identifier.variant == RFC_4122
    assert before_ms <= embedded_timestamp_ms <= after_ms


def test_all_domain_entities_receive_uuid7_identifiers(api):
    account = register_and_login(api.client, "ids@example.com", "UUID7 workspace")
    project_id = create_project(api.client, account["token"], account["workspace_id"], "UUID7")
    create_task(api.client, account["token"], project_id)

    with api.sessions() as session:
        entities = [
            session.scalar(select(User)),
            session.scalar(select(Workspace)),
            session.scalar(select(WorkspaceMembership)),
            session.scalar(select(Project)),
            session.scalar(select(Task)),
        ]

    assert all(entity is not None and entity.id.version == 7 for entity in entities)


def test_orm_and_api_dates_are_utc_aware(api):
    account = register_and_login(api.client, "utc@example.com", "UTC workspace")
    project_id = create_project(api.client, account["token"], account["workspace_id"], "UTC")
    task_id = create_task(api.client, account["token"], project_id)

    response = api.client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {account['token']}"},
    )
    task_payload = response.json()[0]

    with api.sessions() as session:
        task = session.get(Task, UUID(task_id))
        assert task is not None
        assert task.created_at.tzinfo is UTC
        assert task.updated_at.tzinfo is UTC

    assert datetime.fromisoformat(task_payload["created_at"]).utcoffset() == timedelta(0)
    assert datetime.fromisoformat(task_payload["updated_at"]).utcoffset() == timedelta(0)


def test_utc_type_rejects_naive_values_and_normalizes_offsets():
    column_type = UtcDateTime()
    with pytest.raises(ValueError, match="timezone"):
        column_type.process_bind_param(datetime(2026, 1, 1, 12), dialect=None)  # type: ignore[arg-type]

    lima_time = datetime.fromisoformat("2026-01-15T10:30:00-05:00")
    normalized = column_type.process_bind_param(lima_time, dialect=None)  # type: ignore[arg-type]
    assert normalized == datetime(2026, 1, 15, 15, 30, tzinfo=UTC)
    assert (
        column_type.process_result_value(
            datetime(2026, 1, 15, 15, 30),
            dialect=None,  # type: ignore[arg-type]
        ).tzinfo
        is UTC
    )
