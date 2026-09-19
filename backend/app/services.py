from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.errors import (
    AccountAlreadyExistsError,
    ForbiddenActionError,
    InvalidCredentialsError,
    ResourceNotFoundError,
    TaskVersionConflictError,
)
from app.models import MembershipRole, Project, Task, User, Workspace
from app.repositories import (
    READ_ROLES,
    WRITE_ROLES,
    AccountRepository,
    TaskRepository,
    WorkspaceRepository,
)
from app.schemas import ProjectCreate, RegisterRequest, TaskCreate, TaskUpdate


class AccountService:
    def __init__(self, repository: AccountRepository | None = None) -> None:
        self._repository = repository or AccountRepository()

    def register(self, session: Session, command: RegisterRequest) -> tuple[User, Workspace]:
        if self._repository.get_user_by_email(session, str(command.email)):
            raise AccountAlreadyExistsError

        user = User(email=str(command.email), password_hash=hash_password(command.password))
        workspace = Workspace(name=command.workspace_name.strip())
        self._repository.add_account(session, user, workspace)
        self._commit_or_raise_duplicate(session)
        return user, workspace

    def authenticate(self, session: Session, email: str, password: str) -> User:
        user = self._repository.get_user_by_email(session, email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        return user

    def _commit_or_raise_duplicate(self, session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AccountAlreadyExistsError from error


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository | None = None) -> None:
        self._repository = repository or WorkspaceRepository()

    def list_for_actor(
        self, session: Session, actor_id: UUID
    ) -> Sequence[tuple[Workspace, MembershipRole]]:
        return self._repository.list_for_actor(session, actor_id)

    def create_project(
        self, session: Session, actor_id: UUID, workspace_id: UUID, command: ProjectCreate
    ) -> Project:
        workspace = self._repository.get_for_actor(session, workspace_id, actor_id, READ_ROLES)
        if workspace is None:
            raise ResourceNotFoundError
        if self._repository.get_for_actor(session, workspace_id, actor_id, WRITE_ROLES) is None:
            raise ForbiddenActionError

        project = Project(workspace_id=workspace.id, name=command.name.strip())
        self._repository.add_project(session, project)
        session.commit()
        return project

    def list_projects(
        self, session: Session, actor_id: UUID, workspace_id: UUID
    ) -> Sequence[Project]:
        workspace = self._repository.get_for_actor(session, workspace_id, actor_id, READ_ROLES)
        if workspace is None:
            raise ResourceNotFoundError
        return self._repository.list_projects_for_actor(session, workspace_id, actor_id)


class TaskService:
    def __init__(self, repository: TaskRepository | None = None) -> None:
        self._repository = repository or TaskRepository()

    def list_tasks(self, session: Session, actor_id: UUID, project_id: UUID) -> Sequence[Task]:
        project = self._repository.find_project_for_actor(session, project_id, actor_id, READ_ROLES)
        if project is None:
            raise ResourceNotFoundError
        return self._repository.list_for_actor(session, project_id, actor_id)

    def create_task(
        self, session: Session, actor_id: UUID, project_id: UUID, command: TaskCreate
    ) -> Task:
        project = self._repository.find_project_for_actor(session, project_id, actor_id, READ_ROLES)
        if project is None:
            raise ResourceNotFoundError
        if (
            self._repository.find_project_for_actor(session, project_id, actor_id, WRITE_ROLES)
            is None
        ):
            raise ForbiddenActionError

        task = Task(
            project_id=project.id,
            created_by_id=actor_id,
            title=command.title.strip(),
            description=command.description,
            status=command.status,
        )
        self._repository.add_task(session, task)
        session.commit()
        return task

    def update_task(
        self,
        session: Session,
        actor_id: UUID,
        project_id: UUID,
        task_id: UUID,
        command: TaskUpdate,
    ) -> Task:
        existing = self._repository.find_for_actor(session, project_id, task_id, actor_id)
        if existing is None:
            raise ResourceNotFoundError
        if (
            self._repository.find_project_for_actor(session, project_id, actor_id, WRITE_ROLES)
            is None
        ):
            raise ForbiddenActionError

        updated = self._repository.update_for_actor(
            session,
            project_id=project_id,
            task_id=task_id,
            actor_id=actor_id,
            expected_version=command.version,
            changes=command.changes(),
        )
        if updated is not None:
            session.commit()
            return updated

        current = self._repository.find_for_actor(session, project_id, task_id, actor_id)
        if current is None:
            raise ResourceNotFoundError
        raise TaskVersionConflictError(task_id=task_id, current_version=current.version)
