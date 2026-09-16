from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import DailyTask, DuoMember, User
from app.schemas.review import ReviewCreate, ReviewResponse
from app.api.deps import get_current_user
from app.services.review_service import ReviewService

router = APIRouter(prefix="/tasks/{task_id}/reviews", tags=["Reviews"])

@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review(
    task_id: str,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify task exists
    task_res = await db.execute(select(DailyTask).where(DailyTask.id == task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Daily task not found")

    # Find the partner in this duo who is the task owner being reviewed
    members_res = await db.execute(
        select(DuoMember).where(DuoMember.duo_id == task.duo_id)
    )
    members = members_res.scalars().all()
    
    partner = None
    for m in members:
        if m.user_id != current_user.id:
            partner = m
            break

    if not partner:
        raise HTTPException(status_code=400, detail="Cannot review: Duo has no partner")

    # Enforce review rules via ReviewService
    review = await ReviewService.create_review(
        session=db,
        task_id=task_id,
        task_owner_id=partner.user_id,
        reviewer_id=current_user.id,
        review_status_input=data.status,
        comment=data.comment,
        commit_sha=data.commit_sha
    )
    await db.commit()
    await db.refresh(review)

    # Fetch reviewer full name
    return ReviewResponse(
        id=review.id,
        daily_task_id=review.daily_task_id,
        task_owner_id=review.task_owner_id,
        task_owner_name=None,
        reviewer_id=review.reviewer_id,
        reviewer_name=current_user.full_name,
        status=review.status,
        comment=review.comment,
        commit_sha=review.commit_sha,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

@router.get("", response_model=List[ReviewResponse])
async def get_reviews(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify task exists
    task_res = await db.execute(select(DailyTask).where(DailyTask.id == task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Daily task not found")

    # Verify user is in this duo
    mem_res = await db.execute(
        select(DuoMember).where(
            and_(
                DuoMember.duo_id == task.duo_id,
                DuoMember.user_id == current_user.id
            )
        )
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    reviews = await ReviewService.get_task_reviews(db, task_id)
    return [ReviewResponse(**r) for r in reviews]
