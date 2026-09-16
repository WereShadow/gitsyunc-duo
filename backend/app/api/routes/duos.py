import secrets
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import Duo, DuoMember, User, Streak, GitHubAccount, Project
from app.schemas.duo import DuoCreate, DuoJoin, DuoSettingsUpdate, DuoResponse, DuoMemberResponse
from app.schemas.streak import StreakResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/duos", tags=["Duos"])

def generate_invite_code() -> str:
    """Generate friendly 8-character invite code like SYNC-9482."""
    rand_chars = secrets.token_hex(2).upper()
    rand_digits = secrets.randbelow(9000) + 1000
    return f"SYNC-{rand_digits}"

async def _build_duo_response(session: AsyncSession, duo: Duo) -> DuoResponse:
    # Get members
    members_res = await session.execute(
        select(DuoMember, User)
        .join(User, DuoMember.user_id == User.id)
        .where(DuoMember.duo_id == duo.id)
        .order_by(DuoMember.joined_at)
    )
    members_data = members_res.all()

    # Get GitHub usernames for members
    member_responses: List[DuoMemberResponse] = []
    for dm, user in members_data:
        gh_res = await session.execute(
            select(GitHubAccount).where(GitHubAccount.user_id == user.id)
        )
        gh_acc = gh_res.scalar_one_or_none()
        member_responses.append(
            DuoMemberResponse(
                id=dm.id,
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                github_username=gh_acc.github_username if gh_acc else None,
                role=dm.role,
                joined_at=dm.joined_at
            )
        )

    # Get streak
    streak_res = await session.execute(
        select(Streak).where(Streak.duo_id == duo.id)
    )
    streak = streak_res.scalar_one_or_none()
    streak_resp = None
    if streak:
        streak_resp = StreakResponse.model_validate(streak)

    return DuoResponse(
        id=duo.id,
        name=duo.name,
        invite_code=duo.invite_code,
        created_by=duo.created_by,
        timezone=duo.timezone,
        deadline_time=duo.deadline_time,
        grace_period_minutes=duo.grace_period_minutes,
        project_mode=duo.project_mode,
        workflow_type=duo.workflow_type,
        created_at=duo.created_at,
        members=member_responses,
        streak=streak_resp
    )

@router.post("", response_model=DuoResponse, status_code=status.HTTP_201_CREATED)
async def create_duo(
    data: DuoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if user is already in a duo
    existing = await db.execute(
        select(DuoMember).where(DuoMember.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of an active Duo. You must leave or complete it first."
        )

    # Generate unique invite code
    invite_code = generate_invite_code()
    while (await db.execute(select(Duo).where(Duo.invite_code == invite_code))).scalar_one_or_none():
        invite_code = generate_invite_code()

    now = datetime.now(timezone.utc)
    duo = Duo(
        name=data.name,
        invite_code=invite_code,
        created_by=current_user.id,
        timezone=data.timezone,
        deadline_time=data.deadline_time,
        grace_period_minutes=data.grace_period_minutes,
        project_mode=data.project_mode,
        workflow_type=data.workflow_type,
        created_at=now,
        updated_at=now
    )
    db.add(duo)
    await db.flush()

    # Add creator as first member
    membership = DuoMember(
        duo_id=duo.id,
        user_id=current_user.id,
        role="CREATOR",
        joined_at=now
    )
    db.add(membership)

    # Initialize streak record
    streak = Streak(
        duo_id=duo.id,
        current_streak=0,
        longest_streak=0,
        completed_days=0,
        missed_days=0,
        updated_at=now
    )
    db.add(streak)

    await db.commit()
    await db.refresh(duo)

    return await _build_duo_response(db, duo)

@router.post("/join", response_model=DuoResponse)
async def join_duo(
    data: DuoJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if user already in a duo
    user_existing = await db.execute(
        select(DuoMember).where(DuoMember.user_id == current_user.id)
    )
    if user_existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already in an active Duo."
        )

    # Find duo by invite code
    duo_res = await db.execute(
        select(Duo).where(Duo.invite_code == data.invite_code.strip().upper())
    )
    duo = duo_res.scalar_one_or_none()
    if not duo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code. No Duo found."
        )

    # ENFORCE MAXIMUM TWO MEMBERS RULE
    members_res = await db.execute(
        select(DuoMember).where(DuoMember.duo_id == duo.id)
    )
    members = members_res.scalars().all()
    if len(members) >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Duo is already full. Duos can contain exactly two members."
        )

    # Add user as PARTNER
    membership = DuoMember(
        duo_id=duo.id,
        user_id=current_user.id,
        role="PARTNER",
        joined_at=datetime.now(timezone.utc)
    )
    db.add(membership)
    await db.commit()
    await db.refresh(duo)

    return await _build_duo_response(db, duo)

@router.get("/current", response_model=DuoResponse)
async def get_current_duo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get user's membership
    mem_res = await db.execute(
        select(DuoMember).where(DuoMember.user_id == current_user.id)
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not part of any Duo."
        )

    duo_res = await db.execute(
        select(Duo).where(Duo.id == membership.duo_id)
    )
    duo = duo_res.scalar_one_or_none()
    if not duo:
        raise HTTPException(status_code=404, detail="Duo not found")

    return await _build_duo_response(db, duo)

@router.get("/{id}", response_model=DuoResponse)
async def get_duo_by_id(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # SECURITY RULE: User may ONLY access their own duo data
    mem_res = await db.execute(
        select(DuoMember).where(
            and_(
                DuoMember.duo_id == id,
                DuoMember.user_id == current_user.id
            )
        )
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this Duo."
        )

    duo_res = await db.execute(select(Duo).where(Duo.id == id))
    duo = duo_res.scalar_one_or_none()
    if not duo:
        raise HTTPException(status_code=404, detail="Duo not found")

    return await _build_duo_response(db, duo)

@router.put("/{id}/settings", response_model=DuoResponse)
async def update_duo_settings(
    id: str,
    data: DuoSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user belongs to this duo
    mem_res = await db.execute(
        select(DuoMember).where(
            and_(
                DuoMember.duo_id == id,
                DuoMember.user_id == current_user.id
            )
        )
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this Duo."
        )

    duo_res = await db.execute(select(Duo).where(Duo.id == id))
    duo = duo_res.scalar_one_or_none()
    if not duo:
        raise HTTPException(status_code=404, detail="Duo not found")

    if data.timezone is not None:
        duo.timezone = data.timezone
    if data.deadline_time is not None:
        duo.deadline_time = data.deadline_time
    if data.grace_period_minutes is not None:
        duo.grace_period_minutes = data.grace_period_minutes
    if data.project_mode is not None:
        duo.project_mode = data.project_mode
    if data.workflow_type is not None:
        duo.workflow_type = data.workflow_type

    duo.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(duo)

    return await _build_duo_response(db, duo)
