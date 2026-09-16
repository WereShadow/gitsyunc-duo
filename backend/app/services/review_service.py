from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    DailyTask,
    DailyUserProgress,
    Duo,
    DuoMember,
    TaskReview,
    Notification,
    User,
)
from app.services.completion_engine import CompletionEngine

class ReviewService:
    """
    Handles task submission, peer review permissions, review audit trail,
    and triggering completion engine evaluations.
    """

    @staticmethod
    async def submit_task(
        session: AsyncSession,
        task_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """User submits their task for partner review once GitHub work is uploaded."""
        # Find progress
        prog_res = await session.execute(
            select(DailyUserProgress).where(
                and_(
                    DailyUserProgress.daily_task_id == task_id,
                    DailyUserProgress.user_id == user_id
                )
            )
        )
        progress = prog_res.scalar_one_or_none()
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User progress record not found for this task"
            )

        if not progress.github_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit for review until GitHub activity is verified"
            )

        now = datetime.now(timezone.utc)
        progress.submission_status = "SUBMITTED"
        progress.review_status = "UNDER_REVIEW"
        progress.submitted_at = now

        # Get task and duo to notify partner
        task_res = await session.execute(
            select(DailyTask).where(DailyTask.id == task_id)
        )
        task = task_res.scalar_one_or_none()
        
        if task:
            # Find partner
            partner_res = await session.execute(
                select(DuoMember).where(
                    and_(
                        DuoMember.duo_id == task.duo_id,
                        DuoMember.user_id != user_id
                    )
                )
            )
            partner = partner_res.scalar_one_or_none()
            if partner:
                notif = Notification(
                    user_id=partner.user_id,
                    duo_id=task.duo_id,
                    type="REVIEW_REQUESTED",
                    title="🔍 Peer Review Requested",
                    message=f"Your partner submitted their task '{task.title}' for your review."
                )
                session.add(notif)

            # Re-evaluate completion status
            await CompletionEngine.evaluate_task_completion(session, task, trigger_user_id=user_id)

        await session.flush()
        return {
            "success": True,
            "submission_status": progress.submission_status,
            "review_status": progress.review_status,
            "submitted_at": progress.submitted_at
        }

    @staticmethod
    async def create_review(
        session: AsyncSession,
        task_id: str,
        task_owner_id: str,
        reviewer_id: str,
        review_status_input: str,  # "APPROVED" or "CHANGES_REQUESTED"
        comment: str,
        commit_sha: Optional[str] = None
    ) -> TaskReview:
        """
        Submit a peer review with strict server-side authorization:
        1. Reviewer CANNOT approve/review their own task (reviewer_id != task_owner_id).
        2. Reviewer must be in the same duo as task owner.
        """
        # RULE 1: Cannot review own task
        if reviewer_id == task_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Violation: You cannot review or approve your own task."
            )

        # Get task
        task_res = await session.execute(
            select(DailyTask).where(DailyTask.id == task_id)
        )
        task = task_res.scalar_one_or_none()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily task not found"
            )

        # RULE 2: Must be members of the same duo
        duo_res = await session.execute(
            select(DuoMember).where(
                and_(
                    DuoMember.duo_id == task.duo_id,
                    DuoMember.user_id.in_([reviewer_id, task_owner_id])
                )
            )
        )
        members = duo_res.scalars().all()
        if len(members) != 2:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Both users must belong to the same duo to perform peer reviews."
            )

        # Find task owner's progress
        prog_res = await session.execute(
            select(DailyUserProgress).where(
                and_(
                    DailyUserProgress.daily_task_id == task_id,
                    DailyUserProgress.user_id == task_owner_id
                )
            )
        )
        progress = prog_res.scalar_one_or_none()
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task owner progress record not found"
            )

        now = datetime.now(timezone.utc)
        clean_status = review_status_input.upper()

        if clean_status == "APPROVED":
            progress.review_status = "APPROVED"
            progress.approved_at = now
            # Notification to task owner
            notif = Notification(
                user_id=task_owner_id,
                duo_id=task.duo_id,
                type="TASK_APPROVED",
                title="✅ Task Approved",
                message=f"Your partner approved your work on '{task.title}'!"
            )
            session.add(notif)

        elif clean_status == "CHANGES_REQUESTED":
            progress.review_status = "CHANGES_REQUESTED"
            progress.submission_status = "CHANGES_REQUESTED"
            # Notification to task owner
            notif = Notification(
                user_id=task_owner_id,
                duo_id=task.duo_id,
                type="CHANGES_REQUESTED",
                title="✏️ Changes Requested",
                message=f"Your partner requested changes: {comment}"
            )
            session.add(notif)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Review status must be either APPROVED or CHANGES_REQUESTED"
            )

        # Create audit review record
        review = TaskReview(
            daily_task_id=task_id,
            task_owner_id=task_owner_id,
            reviewer_id=reviewer_id,
            status=clean_status,
            comment=comment,
            commit_sha=commit_sha or progress.latest_commit_sha,
            created_at=now,
            updated_at=now
        )
        session.add(review)

        # Trigger completion engine
        await CompletionEngine.evaluate_task_completion(session, task, trigger_user_id=reviewer_id)

        await session.flush()
        return review

    @staticmethod
    async def get_task_reviews(
        session: AsyncSession,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """Retrieve complete review history for a daily task."""
        res = await session.execute(
            select(TaskReview, User)
            .join(User, TaskReview.reviewer_id == User.id)
            .where(TaskReview.daily_task_id == task_id)
            .order_by(TaskReview.created_at.desc())
        )
        records = res.all()
        
        output = []
        for review, reviewer in records:
            output.append({
                "id": review.id,
                "daily_task_id": review.daily_task_id,
                "task_owner_id": review.task_owner_id,
                "reviewer_id": review.reviewer_id,
                "reviewer_name": reviewer.full_name,
                "status": review.status,
                "comment": review.comment,
                "commit_sha": review.commit_sha,
                "created_at": review.created_at,
                "updated_at": review.updated_at
            })
        return output
