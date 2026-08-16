from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from typing import Annotated
import jwt

from app.db.dependencies import DBDependency
from app.models import User
from app.auth.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

def get_current_user(
    db: DBDependency,
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except(
        jwt.InvalidTokenError,
        ValueError,
        TypeError
    ):
        raise credentials_exception

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user

CurrentUserDependency = Annotated[User, Depends(get_current_user)]