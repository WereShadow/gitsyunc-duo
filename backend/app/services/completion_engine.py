from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List
import pytz
import json
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    DailyTask,
    DailyUserProgress,
    Duo,
    DuoMember,
    Streak,
    Project,
    ProjectVerification,
    TaskReview,
    Notification,
)

logger = logging.getLogger(__name__)

class CompletionEngine:
    """
    Core authoritative business engine for GitSync Duo.
    Strictly enforces completion logic, review rules, project checks,
    streak calculations, and timezone boundaries.
    """

    @staticmethod
    def get_day_boundaries(duo_timezone_str: str, target_date_str: str, deadline_time_str: str = "23:59") -> Tuple[datetime, datetime, datetime]:
        """
        Calculate local day start, day end, and deadline in UTC for a specific date (YYYY-MM-DD).
        Returns: (start_of_day_utc, end_of_day_utc, deadline_utc)
        """
        try:
            tz = pytz.timezone(duo_timezone_str)
        except Exception:
            tz = pytz.timezone("Asia/Kolkata")

        year, month, day = map(int, target_date_str.split("-"))
        
        # Local start of day: 00:00:00
        local_start = tz.localize(datetime(year, month, day, 0, 0, 0))
        # Local end of day: 23:59:59
        local_end = tz.localize(datetime(year, month, day, 23, 59, 59))
        
        # Deadline time
        d_hour, d_minute = map(int, deadline_time_str.split(":"))
        local_deadline = tz.localize(datetime(year, month, day, d_hour, d_minute, 0))

        return (
            local_start.astimezone(pytz.UTC),
            local_end.astimezone(pytz.UTC),
            local_deadline.astimezone(pytz.UTC)
        )

    @staticmethod
    def get_today_local_date_str(duo_timezone_str: str) -> str:
        """Get today's local date YYYY-MM-DD in the duo's configured timezone."""
        try:
            tz = pytz.timezone(duo_timezone_str)
        except Exception:
            tz = pytz.timezone("Asia/Kolkata")
        return datetime.now(tz).strftime("%Y-%m-%d")

    @classmethod
    async def evaluate_task_completion(
        cls,
        session: AsyncSession,
        daily_task: DailyTask,
        trigger_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authoritative evaluation of daily task completion.
        Updates task status, user progress statuses, notifications, and streak.
        """
        # Fetch Duo with members
        duo_res = await session.execute(
            select(Duo).where(Duo.id == daily_task.duo_id)
        )
        duo = duo_res.scalar_one_or_none()
        if not duo:
            return {"status": daily_task.status, "completed": False}

        # Fetch members
        members_res = await session.execute(
            select(DuoMember).where(DuoMember.duo_id == duo.id).order_by(DuoMember.joined_at)
        )
        members = members_res.scalars().all()
        if len(members) < 2:
            logger.info(f"Duo {duo.id} has fewer than 2 members. Waiting for partner.")
            return {"status": "WAITING_FOR_PARTNER", "completed": False}

        user_a = members[0]
        user_b = members[1]

        # Fetch progress for both users
        progress_res = await session.execute(
            select(DailyUserProgress).where(DailyUserProgress.daily_task_id == daily_task.id)
        )
        progress_list = progress_res.scalars().all()
        progress_map = {p.user_id: p for p in progress_list}

        prog_a = progress_map.get(user_a.user_id)
        prog_b = progress_map.get(user_b.user_id)

        user_a_verified = bool(prog_a and prog_a.github_verified)
        user_b_verified = bool(prog_b and prog_b.github_verified)

        now_utc = datetime.now(timezone.utc)
        grace_delta = timedelta(minutes=duo.grace_period_minutes)
        effective_deadline = daily_task.deadline_utc + grace_delta
        is_past_deadline = now_utc > effective_deadline

        # Handle SEPARATE PROJECTS MODE
        if duo.project_mode == "SEPARATE":
            if user_a_verified and user_b_verified:
                new_status = "COMPLETED"
            elif is_past_deadline:
                new_status = "MISSED"
            elif user_a_verified and not user_b_verified:
                new_status = "WAITING_FOR_USER_B"
            elif user_b_verified and not user_a_verified:
                new_status = "WAITING_FOR_USER_A"
            else:
                new_status = "ACTIVE"

            previous_status = daily_task.status
            daily_task.status = new_status
            daily_task.updated_at = now_utc

            if new_status == "COMPLETED" and previous_status != "COMPLETED":
                await cls._handle_completion_success(session, duo, daily_task, user_a, user_b)
            elif new_status == "MISSED" and previous_status != "MISSED":
                await cls._handle_completion_missed(session, duo, daily_task)

            return {
                "status": daily_task.status,
                "completed": daily_task.status == "COMPLETED",
                "user_a_verified": user_a_verified,
                "user_b_verified": user_b_verified,
            }

        # Handle SHARED PROJECT MODE
        elif duo.project_mode == "SHARED":
            # Stage 1: Both must have uploaded work (GitHub verified)
            # Stage 2: Peer reviews
            user_a_approved = bool(prog_a and prog_a.review_status == "APPROVED")
            user_b_approved = bool(prog_b and prog_b.review_status == "APPROVED")

            # Check project verification
            pv_res = await session.execute(
                select(ProjectVerification).where(ProjectVerification.daily_task_id == daily_task.id).order_by(ProjectVerification.checked_at.desc())
            )
            latest_pv = pv_res.scalar_one_or_none()
            project_checks_passed = False

            if latest_pv:
                # If automated checks exist, overall_status must be PASSED
                project_checks_passed = (latest_pv.overall_status == "PASSED")
            else:
                # If no verification record exists yet, check if verification is required
                proj_res = await session.execute(
                    select(Project).where(Project.duo_id == duo.id)
                )
                proj = proj_res.scalar_one_or_none()
                if proj and not proj.verification_enabled:
                    # Verification disabled, only peer review required
                    project_checks_passed = True
                else:
                    # By default in shared mode, project verification record is required
                    project_checks_passed = False

            # Check for changes requested
            user_a_changes_requested = bool(prog_a and prog_a.review_status == "CHANGES_REQUESTED")
            user_b_changes_requested = bool(prog_b and prog_b.review_status == "CHANGES_REQUESTED")

            if user_a_verified and user_b_verified and user_a_approved and user_b_approved and project_checks_passed:
                new_status = "COMPLETED"
            elif is_past_deadline:
                new_status = "MISSED"
            elif user_a_changes_requested or user_b_changes_requested:
                new_status = "CHANGES_REQUESTED"
            elif user_a_verified and user_b_verified and (not user_a_approved or not user_b_approved or not project_checks_passed):
                new_status = "WAITING_FOR_REVIEW"
            elif user_a_verified and not user_b_verified:
                new_status = "WAITING_FOR_USER_B"
            elif user_b_verified and not user_a_verified:
                new_status = "WAITING_FOR_USER_A"
            else:
                new_status = "ACTIVE"

            previous_status = daily_task.status
            daily_task.status = new_status
            daily_task.updated_at = now_utc

            if new_status == "COMPLETED" and previous_status != "COMPLETED":
                await cls._handle_completion_success(session, duo, daily_task, user_a, user_b)
            elif new_status == "MISSED" and previous_status != "MISSED":
                await cls._handle_completion_missed(session, duo, daily_task)

            return {
                "status": daily_task.status,
                "completed": daily_task.status == "COMPLETED",
                "user_a_verified": user_a_verified,
                "user_b_verified": user_b_verified,
                "user_a_approved": user_a_approved,
                "user_b_approved": user_b_approved,
                "project_checks_passed": project_checks_passed,
            }

        return {"status": daily_task.status, "completed": False}

    @classmethod
    async def _handle_completion_success(
        cls,
        session: AsyncSession,
        duo: Duo,
        daily_task: DailyTask,
        user_a: DuoMember,
        user_b: DuoMember
    ):
        """Update streaks and issue celebration notifications on day complete."""
        # Get or create streak record
        streak_res = await session.execute(
            select(Streak).where(Streak.duo_id == duo.id)
        )
        streak = streak_res.scalar_one_or_none()
        if not streak:
            streak = Streak(
                duo_id=duo.id,
                current_streak=0,
                longest_streak=0,
                completed_days=0,
                missed_days=0
            )
            session.add(streak)

        # Avoid double-counting if completed on same calendar date
        if streak.last_completed_date != daily_task.date:
            streak.current_streak += 1
            streak.completed_days += 1
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
            streak.last_completed_date = daily_task.date
            streak.updated_at = datetime.now(timezone.utc)

        # Send celebration notifications to both users
        for member in [user_a, user_b]:
            notif = Notification(
                user_id=member.user_id,
                duo_id=duo.id,
                type="DAY_COMPLETED",
                title="🎉 Day Completed!",
                message=f"Both members have completed today's requirements! Streak increased to {streak.current_streak} days."
            )
            session.add(notif)

    @classmethod
    async def _handle_completion_missed(
        cls,
        session: AsyncSession,
        duo: Duo,
        daily_task: DailyTask
    ):
        """Reset streak when deadline expires without completion."""
        streak_res = await session.execute(
            select(Streak).where(Streak.duo_id == duo.id)
        )
        streak = streak_res.scalar_one_or_none()
        if streak:
            streak.current_streak = 0
            streak.missed_days += 1
            streak.updated_at = datetime.now(timezone.utc)

        # Fetch members to notify
        members_res = await session.execute(
            select(DuoMember).where(DuoMember.duo_id == duo.id)
        )
        for member in members_res.scalars().all():
            notif = Notification(
                user_id=member.user_id,
                duo_id=duo.id,
                type="STREAK_WARNING",
                title="⚠️ Day Missed",
                message=f"Today's deadline passed without both requirements completed. The streak has reset."
            )
            session.add(notif)
