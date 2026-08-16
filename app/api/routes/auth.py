import logging

from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.schemas.auth import UserRegisterRequest, UserRegisteredResponse, TokenResponse
from app.db.dependencies import DBDependency
from app.models import User
from app.auth import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserRegisteredResponse)
def register(
    user_request: UserRegisterRequest,
    db: DBDependency
):

    # Checking if username is already registered
    existing_username = db.scalar(
        select(User).where(User.username == user_request.username)
    )
    if existing_username:
        logger.warning(
            "Registration failed: username already exists"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    # Checking if email is already registered
    existing_email = db.scalar(
        select(User).where(User.email == user_request.email)
    )
    if existing_email:
        logger.warning(
            "Registration failed: email already exists"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Creating User object and adding user to database
    user = User(
        username=user_request.username,
        email=user_request.email,
        hashed_password=hash_password(user_request.password),
        is_active=True
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()

        logger.warning(
            "Registration failed: database uniqueness conflict"
        )

    logger.info(
        "User registered successfully: user_id=%s",
        user.id
    )

    return user

@router.post("/login", response_model=TokenResponse)
def login_user(
    db: DBDependency,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # Getting user data
    user = db.scalar(
        select(User).where(User.username == form_data.username)
    )

    if not user:
        logging.warning(
            "Login failed: user not found"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={'WWW-Authenticate': "Bearer"}
        )

    if not verify_password(
        form_data.password,
        user.hashed_password
    ):
        logging.warning(
            "Login failed: invalid password for user_id-%s",
            user.id
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={'WWW-Authenticate': "Bearer"}
        )

    if not user.is_active:
        logging.warning(
            "Login failed: inactive user_id=%s",
            user.id
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Creating access token
    access_token = create_access_token(user.id)

    logger.info(
        "User logged in successfully: user_id=%s",
        user.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
