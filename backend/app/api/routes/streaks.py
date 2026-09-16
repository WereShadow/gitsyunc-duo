from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import DuoMember, Streak, User
from app.schemas.streak import StreakResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/streaks", tags=["Streaks"])

@router.get("", response_model=StreakResponse)
async def get_my_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    mem_res = await db.execute(
        select(DuoMember).where(DuoMember.user_id == current_user.id)
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Not in a Duo")

    streak_res = await db.execute(
        select(Streak).where(Streak.duo_id == membership.duo_id)
    )
    streak = streak_res.scalar_one_or_none()
    if not streak:
        return StreakResponse(
            current_streak=0,
            longest_streak=0,
            completed_days=0,
            missed_days=0
        )

    return StreakResponse.model_validate(streak)
