from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidAccessToken, parse_access_token
from app.database import get_session
from app.models import User
from app.repositories import AccountRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
SessionDependency = Annotated[Session, Depends(get_session)]


def get_current_user(session: SessionDependency, token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        user_id = parse_access_token(token)
    except InvalidAccessToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from error

    user = AccountRepository().get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
