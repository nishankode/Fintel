from datetime import datetime, timedelta, timezone

import jwt

from app.core.settings import get_settings

settings = get_settings()

def create_access_token(user_id: int) -> str:

    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    }

    token = jwt.encode(
        payload=payload,
        key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token

def decode_access_token(token: str) -> dict:

    payload = jwt.decode(
        jwt=token,
        key=settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm]
    )

    return payload