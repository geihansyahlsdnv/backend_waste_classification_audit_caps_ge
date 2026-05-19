from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...db.session import get_db
from ...db.models import User, ClassificationResult
from ...schemas.auth import (
    UserCreate, UserLogin, UserResponse, Token,
    UserUpdate, PasswordChange
)
from ...core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    check_permissions
)

router = APIRouter()

# Self-registration is locked to operator only.
# Admins promote operators to supervisor via PATCH /admin/users/{id}/role
ALLOWED_REGISTER_ROLES = {"operator"}

# System account used to receive anonymized audit data when a user deletes themselves.
# Created lazily on first self-deletion.
DELETED_USER_USERNAME = "_deleted_user"
DELETED_USER_EMAIL = "deleted@system.local"


async def _get_or_create_deleted_user(db: AsyncSession) -> User:
    """Return the system 'deleted_user' account, creating it if missing."""
    deleted = await db.scalar(select(User).where(User.username == DELETED_USER_USERNAME))
    if deleted:
        return deleted

    deleted = User(
        username=DELETED_USER_USERNAME,
        email=DELETED_USER_EMAIL,
        hashed_password=get_password_hash("disabled-account-no-login"),
        role="operator",
        is_active=False,
    )
    db.add(deleted)
    await db.commit()
    await db.refresh(deleted)
    return deleted


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Block registration with reserved system username
    if user_in.username == DELETED_USER_USERNAME:
        raise HTTPException(status_code=400, detail="Username tidak diperbolehkan")

    if await db.scalar(select(User).where(User.username == user_in.username)):
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    
    if await db.scalar(select(User).where(User.email == user_in.email)):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    # Force operator role on self-registration regardless of what was sent
    safe_role = "operator"

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


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_in: UserUpdate,
    current_user: dict = Depends(check_permissions("operator", "admin", "supervisor")),
    db: AsyncSession = Depends(get_db)
):
    """Update the authenticated user's own username and/or email."""
    user = await db.scalar(select(User).where(User.id == current_user["user_id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if update_in.username is not None and update_in.username != user.username:
        if update_in.username == DELETED_USER_USERNAME:
            raise HTTPException(status_code=400, detail="Username tidak diperbolehkan")
        existing = await db.scalar(select(User).where(User.username == update_in.username))
        if existing:
            raise HTTPException(status_code=400, detail="Username sudah digunakan")
        user.username = update_in.username

    if update_in.email is not None and update_in.email != user.email:
        existing = await db.scalar(select(User).where(User.email == update_in.email))
        if existing:
            raise HTTPException(status_code=400, detail="Email sudah terdaftar")
        user.email = update_in.email

    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Data konflik, username atau email sudah digunakan")

    return user


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: PasswordChange,
    current_user: dict = Depends(check_permissions("operator", "admin", "supervisor")),
    db: AsyncSession = Depends(get_db)
):
    """Change the authenticated user's own password. Requires the old password."""
    user = await db.scalar(select(User).where(User.id == current_user["user_id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if not verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Password lama tidak cocok")

    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="Password baru harus berbeda dari yang lama")

    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    await db.commit()

    return {"detail": "Password berhasil diubah"}


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_current_user(
    current_user: dict = Depends(check_permissions("operator", "admin", "supervisor")),
    db: AsyncSession = Depends(get_db)
):
    """
    Hard delete the authenticated user's account.
    All their classification history is reassigned to a system 'deleted_user'
    so aggregate stats stay correct, but personal data is removed.
    """
    user = await db.scalar(select(User).where(User.id == current_user["user_id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # Safety guard: don't allow deleting the system account
    if user.username == DELETED_USER_USERNAME:
        raise HTTPException(status_code=400, detail="Akun sistem tidak dapat dihapus")

    deleted_user = await _get_or_create_deleted_user(db)

    # Reassign all classifications to the system account
    await db.execute(
        update(ClassificationResult)
        .where(ClassificationResult.user_id == user.id)
        .values(user_id=deleted_user.id)
    )

    await db.delete(user)
    await db.commit()

    return {"detail": "Akun berhasil dihapus dan riwayat dianonimkan"}