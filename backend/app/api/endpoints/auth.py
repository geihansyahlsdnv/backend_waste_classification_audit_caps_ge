from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...db.session import get_db
from ...db.models import User
from ...schemas.auth import UserCreate, UserLogin, UserResponse, Token
from ...core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    check_permissions
)

router = APIRouter()

ALLOWED_REGISTER_ROLES = {"operator", "supervisor"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    
    if await db.scalar(select(User).where(User.username == user_in.username)):
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    
    if await db.scalar(select(User).where(User.email == user_in.email)):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    
    safe_role = user_in.role if user_in.role in ALLOWED_REGISTER_ROLES else "operator"

    # Create User
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=safe_role
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Data konflik, username atau email sudah digunakan")
    return user

@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    user = await db.scalar(select(User).where(User.username == user_in.username))
    
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    # Generate token n user_id dan role
    access_token = create_access_token(user_id=user.id, role=user.role)
    return Token(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(check_permissions("operator", "admin", "supervisor")),
    db: AsyncSession = Depends(get_db)
):
    # current_user payload JWT via check_permissions
    user = await db.scalar(select(User).where(User.id == current_user["user_id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user