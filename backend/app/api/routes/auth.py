from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import User, GitHubAccount, DuoMember
from app.schemas.auth import UserRegister, UserLogin, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    res = await db.execute(select(User).where(User.email == data.email.lower()))
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    user = User(
        email=data.email.lower(),
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(user)
    await db.flush()

    token = create_access_token(data={"sub": user.id, "email": user.email})
    
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        github_connected=False,
        github_username=None,
        current_duo_id=None
    )
    return Token(access_token=token, token_type="bearer", user=user_resp)

@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == data.email.lower()))
    user = res.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check GitHub connection & duo
    gh_res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == user.id))
    gh_acc = gh_res.scalar_one_or_none()

    duo_res = await db.execute(select(DuoMember).where(DuoMember.user_id == user.id))
    membership = duo_res.scalar_one_or_none()

    token = create_access_token(data={"sub": user.id, "email": user.email})

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        github_connected=bool(gh_acc),
        github_username=gh_acc.github_username if gh_acc else None,
        current_duo_id=membership.duo_id if membership else None
    )
    return Token(access_token=token, token_type="bearer", user=user_resp)

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    gh_res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == current_user.id))
    gh_acc = gh_res.scalar_one_or_none()

    duo_res = await db.execute(select(DuoMember).where(DuoMember.user_id == current_user.id))
    membership = duo_res.scalar_one_or_none()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        github_connected=bool(gh_acc),
        github_username=gh_acc.github_username if gh_acc else None,
        current_duo_id=membership.duo_id if membership else None
    )
