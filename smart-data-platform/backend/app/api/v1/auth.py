from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core import create_access_token, get_password_hash, verify_password, settings
from app.models import User, Role
from app.schemas import (
    LoginRequest,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
    RoleCreate,
    RoleResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: DBSession,
) -> Token:
    """Authenticate user and return access token."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(access_token=access_token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserCreate,
    db: DBSession,
) -> User:
    """Register a new user."""
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        is_active=request.is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> User:
    """Get current user profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> User:
    """Update current user profile."""
    if request.email:
        result = await db.execute(
            select(User).where(User.email == request.email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = request.email

    if request.full_name:
        current_user.full_name = request.full_name

    if request.password:
        current_user.hashed_password = get_password_hash(request.password)

    await db.commit()
    await db.refresh(current_user)

    return current_user


# Admin endpoints for user management
admin_router = APIRouter(prefix="/users", tags=["User Management"])


@admin_router.get("", response_model=list[UserResponse])
async def list_users(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """List all users (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars())


@admin_router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> Role:
    """Create a new role (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(select(Role).where(Role.name == request.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role already exists")

    role = Role(
        name=request.name,
        description=request.description,
        permissions=request.permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return role


@admin_router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    db: DBSession,
    current_user: CurrentUser,
) -> list[Role]:
    """List all roles."""
    result = await db.execute(select(Role))
    return list(result.scalars())
