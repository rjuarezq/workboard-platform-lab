from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import SessionDependency
from app.core.security import create_access_token
from app.errors import AccountAlreadyExistsError, InvalidCredentialsError
from app.schemas import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    WorkspaceResponse,
)
from app.services import AccountService

router = APIRouter(prefix="/auth", tags=["authentication"])
_service = AccountService()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(command: RegisterRequest, session: SessionDependency) -> RegisterResponse:
    try:
        user, workspace = _service.register(session, command)
    except AccountAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from error

    return RegisterResponse(
        user_id=user.id,
        workspace=WorkspaceResponse(id=workspace.id, name=workspace.name, role="owner"),
    )


@router.post("/login", response_model=AccessTokenResponse)
def login(command: LoginRequest, session: SessionDependency) -> AccessTokenResponse:
    try:
        user = _service.authenticate(session, str(command.email), command.password)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from error

    return AccessTokenResponse(access_token=create_access_token(user.id))
