from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.errors import ForbiddenActionError, ResourceNotFoundError
from app.schemas import ProjectCreate, ProjectResponse, WorkspaceResponse
from app.services import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
_service = WorkspaceService()


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(session: SessionDependency, user: CurrentUser) -> list[WorkspaceResponse]:
    memberships = _service.list_for_actor(session, user.id)
    return [
        WorkspaceResponse(id=workspace.id, name=workspace.name, role=role)
        for workspace, role in memberships
    ]


@router.post(
    "/{workspace_id}/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED
)
def create_project(
    workspace_id: UUID,
    command: ProjectCreate,
    session: SessionDependency,
    user: CurrentUser,
) -> ProjectResponse:
    try:
        project = _service.create_project(session, user.id, workspace_id, command)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        ) from error
    except ForbiddenActionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Action is not allowed"
        ) from error
    return ProjectResponse.model_validate(project)


@router.get("/{workspace_id}/projects", response_model=list[ProjectResponse])
def list_projects(
    workspace_id: UUID, session: SessionDependency, user: CurrentUser
) -> list[ProjectResponse]:
    try:
        projects = _service.list_projects(session, user.id, workspace_id)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        ) from error
    return [ProjectResponse.model_validate(project) for project in projects]
