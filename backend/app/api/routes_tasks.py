from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentUser, SessionDependency
from app.errors import ForbiddenActionError, ResourceNotFoundError, TaskVersionConflictError
from app.schemas import TaskCreate, TaskResponse, TaskUpdate, VersionConflictResponse
from app.services import TaskService

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])
_service = TaskService()


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    project_id: UUID, session: SessionDependency, user: CurrentUser
) -> list[TaskResponse]:
    try:
        tasks = _service.list_tasks(session, user.id, project_id)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from error
    return [TaskResponse.model_validate(task) for task in tasks]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: UUID,
    command: TaskCreate,
    session: SessionDependency,
    user: CurrentUser,
) -> TaskResponse:
    try:
        task = _service.create_task(session, user.id, project_id, command)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from error
    except ForbiddenActionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Action is not allowed"
        ) from error
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    responses={status.HTTP_409_CONFLICT: {"model": VersionConflictResponse}},
)
def update_task(
    project_id: UUID,
    task_id: UUID,
    command: TaskUpdate,
    session: SessionDependency,
    user: CurrentUser,
) -> TaskResponse | JSONResponse:
    try:
        task = _service.update_task(session, user.id, project_id, task_id, command)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        ) from error
    except ForbiddenActionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Action is not allowed"
        ) from error
    except TaskVersionConflictError as error:
        detail = VersionConflictResponse(
            message="Task changed before this update could be applied",
            current_version=error.current_version,
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=detail.model_dump())
    return TaskResponse.model_validate(task)
