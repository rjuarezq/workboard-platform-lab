from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import MembershipRole, Project, Task, User, Workspace, WorkspaceMembership

READ_ROLES = tuple(MembershipRole)
WRITE_ROLES = (MembershipRole.OWNER, MembershipRole.EDITOR)


class AccountRepository:
    def get_user_by_email(self, session: Session, email: str) -> User | None:
        return session.scalar(select(User).where(User.email == email))

    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def add_account(self, session: Session, user: User, workspace: Workspace) -> None:
        session.add_all(
            [
                user,
                workspace,
                WorkspaceMembership(
                    user=user,
                    workspace=workspace,
                    role=MembershipRole.OWNER,
                ),
            ]
        )


class WorkspaceRepository:
    def list_for_actor(
        self, session: Session, actor_id: UUID
    ) -> Sequence[tuple[Workspace, MembershipRole]]:
        statement = (
            select(Workspace, WorkspaceMembership.role)
            .join(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == actor_id)
            .order_by(Workspace.name)
        )
        return session.execute(statement).all()

    def get_for_actor(
        self,
        session: Session,
        workspace_id: UUID,
        actor_id: UUID,
        roles: tuple[MembershipRole, ...],
    ) -> Workspace | None:
        statement = (
            select(Workspace)
            .join(WorkspaceMembership)
            .where(
                Workspace.id == workspace_id,
                WorkspaceMembership.user_id == actor_id,
                WorkspaceMembership.role.in_(roles),
            )
        )
        return session.scalar(statement)

    def add_project(self, session: Session, project: Project) -> None:
        session.add(project)

    def list_projects_for_actor(
        self, session: Session, workspace_id: UUID, actor_id: UUID
    ) -> Sequence[Project]:
        statement = (
            select(Project)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Project.workspace_id)
            .where(Project.workspace_id == workspace_id, WorkspaceMembership.user_id == actor_id)
            .order_by(Project.name)
        )
        return session.scalars(statement).all()


class TaskRepository:
    def find_project_for_actor(
        self,
        session: Session,
        project_id: UUID,
        actor_id: UUID,
        roles: tuple[MembershipRole, ...],
    ) -> Project | None:
        statement = (
            select(Project)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Project.workspace_id)
            .where(
                Project.id == project_id,
                WorkspaceMembership.user_id == actor_id,
                WorkspaceMembership.role.in_(roles),
            )
        )
        return session.scalar(statement)

    def list_for_actor(self, session: Session, project_id: UUID, actor_id: UUID) -> Sequence[Task]:
        statement = (
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Project.workspace_id)
            .where(Task.project_id == project_id, WorkspaceMembership.user_id == actor_id)
            .order_by(Task.created_at, Task.id)
        )
        return session.scalars(statement).all()

    def find_for_actor(
        self, session: Session, project_id: UUID, task_id: UUID, actor_id: UUID
    ) -> Task | None:
        statement = (
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Project.workspace_id)
            .where(
                Task.id == task_id,
                Task.project_id == project_id,
                WorkspaceMembership.user_id == actor_id,
            )
            .execution_options(populate_existing=True)
        )
        return session.scalar(statement)

    def add_task(self, session: Session, task: Task) -> None:
        session.add(task)

    def update_for_actor(
        self,
        session: Session,
        *,
        project_id: UUID,
        task_id: UUID,
        actor_id: UUID,
        expected_version: int,
        changes: dict[str, object],
    ) -> Task | None:
        is_editor = (
            select(WorkspaceMembership.id)
            .join(Project, Project.workspace_id == WorkspaceMembership.workspace_id)
            .where(
                Project.id == project_id,
                WorkspaceMembership.user_id == actor_id,
                WorkspaceMembership.role.in_(WRITE_ROLES),
            )
            .exists()
        )
        statement = (
            update(Task)
            .where(
                Task.id == task_id,
                Task.project_id == project_id,
                Task.version == expected_version,
                is_editor,
            )
            .values(**changes, version=Task.version + 1, updated_at=func.now())
            .returning(Task)
        )
        return session.execute(statement).scalar_one_or_none()
