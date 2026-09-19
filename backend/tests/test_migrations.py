from io import StringIO
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.core.settings import get_settings
from app.database import Base


def migration_config():
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def test_upgrade_matches_models_and_is_repeatable(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("WORKBOARD_DATABASE_URL", url)
    get_settings.cache_clear()
    config = migration_config()
    engine = create_engine(url)
    try:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            connection.execute(
                text("INSERT INTO workspaces (id, name) VALUES (:id, :name)"),
                {"id": "a" * 32, "name": "Keep me"},
            )
        command.upgrade(config, "head")
        command.check(config)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT name FROM workspaces")) == "Keep me"
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]
        command.upgrade(config, "head")
        assert set(Base.metadata.tables).issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_postgresql_offline_sql_has_expected_schema(monkeypatch):
    monkeypatch.setenv(
        "WORKBOARD_DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/test"
    )
    get_settings.cache_clear()
    config = migration_config()
    config.output_buffer = StringIO()
    try:
        command.upgrade(config, "head", sql=True)
        sql = config.output_buffer.getvalue()
        for table in Base.metadata.tables:
            assert f"CREATE TABLE {table}" in sql
        assert "UUID NOT NULL" in sql
        assert "TIMESTAMP WITH TIME ZONE" in sql
        assert "uq_workspace_membership" in sql
        assert "CREATE UNIQUE INDEX ix_users_email" in sql
        assert "FOREIGN KEY(project_id) REFERENCES projects (id)" in sql
        config.output_buffer = StringIO()
        command.downgrade(config, "0001:base", sql=True)
        assert "DROP TABLE tasks" in config.output_buffer.getvalue()
    finally:
        get_settings.cache_clear()
