from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.settings import get_settings
from app.database import get_engine, get_session_factory
from app.main import create_app


@dataclass
class ApiHarness:
    client: TestClient
    sessions: sessionmaker[Session]


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    monkeypatch.setenv("WORKBOARD_JWT_SECRET", "test-secret-that-is-long-enough-for-jwt")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def api(tmp_path, monkeypatch) -> Iterator[ApiHarness]:
    monkeypatch.setenv("WORKBOARD_DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = get_engine()

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with TestClient(create_app()) as client:
            yield ApiHarness(client=client, sessions=get_session_factory())
    finally:
        engine.dispose()
        get_session_factory.cache_clear()
        get_engine.cache_clear()
