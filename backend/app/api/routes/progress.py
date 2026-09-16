import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import (
    DailyTask,
    DailyUserProgress,
    Duo,
    DuoMember,
    User,
    Streak,
    ProjectVerification,
    GitHubAccount,
)
from app.schemas.progress import TodayProgressResponse, CalendarDayItem, CalendarHistoryResponse
from app.schemas.task import UserTaskProgressDetail, ProjectVerificationDetail
from app.api.deps import get_current_user
from app.services.completion_engine import CompletionEngine

router = APIRouter(prefix="/progress", tags=["Progress"])

@router.get("/today", response_model=TodayProgressResponse)
async def get_today_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == current_user.id)
    )
    record = mem_res.first()
    if not record:
        raise HTTPException(status_code=404, detail="Not a member of any Duo")
    membership, duo = record

    today_str = CompletionEngine.get_today_local_date_str(duo.timezone)
    task_res = await db.execute(
        select(DailyTask).where(
            and_(
                DailyTask.duo_id == duo.id,
                DailyTask.date == today_str
            )
        )
    )
    task = task_res.scalar_one_or_none()

    if not task:
        return TodayProgressResponse(
            duo_id=duo.id,
            date=today_str,
            status="NO_TASK",
            grace_period_minutes=duo.grace_period_minutes,
            project_mode=duo.project_mode
        )

    # Trigger completion engine
    eval_res = await CompletionEngine.evaluate_task_completion(db, task)
    await db.commit()
    await db.refresh(task)

    # Fetch members & user progress
    members_res = await db.execute(
        select(DuoMember, User)
        .join(User, DuoMember.user_id == User.id)
        .where(DuoMember.duo_id == duo.id)
        .order_by(DuoMember.joined_at)
    )
    members_data = members_res.all()

    prog_res = await db.execute(
        select(DailyUserProgress).where(DailyUserProgress.daily_task_id == task.id)
    )
    progress_map = {p.user_id: p for p in prog_res.scalars().all()}

    curr_prog_detail = None
    partner_prog_detail = None

    for idx, (m, u) in enumerate(members_data):
        p = progress_map.get(u.id)
        assigned = task.user_a_task if idx == 0 else task.user_b_task

        files = []
        if p and p.changed_files:
            try:
                files = json.loads(p.changed_files)
            except Exception:
                files = []

        gh_res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == u.id))
        gh_acc = gh_res.scalar_one_or_none()

        detail = UserTaskProgressDetail(
            user_id=u.id,
            user_name=u.full_name,
            user_email=u.email,
            avatar_url=u.avatar_url,
            github_username=gh_acc.github_username if gh_acc else None,
            assigned_task=assigned,
            github_verified=p.github_verified if p else False,
            commit_count=p.commit_count if p else 0,
            latest_commit_sha=p.latest_commit_sha if p else None,
            latest_commit_message=p.latest_commit_message if p else None,
            latest_commit_url=p.latest_commit_url if p else None,
            latest_commit_time=p.latest_commit_time if p else None,
            changed_files=files,
            pull_request_url=p.pull_request_url if p else None,
            submission_status=p.submission_status if p else "PENDING",
            review_status=p.review_status if p else "PENDING",
            submitted_at=p.submitted_at if p else None,
            approved_at=p.approved_at if p else None,
            verified_at=p.verified_at if p else None,
        )

        if u.id == current_user.id:
            curr_prog_detail = detail
        else:
            partner_prog_detail = detail

    # Fetch latest project verification if available
    pv_res = await db.execute(
        select(ProjectVerification)
        .where(ProjectVerification.daily_task_id == task.id)
        .order_by(ProjectVerification.checked_at.desc())
    )
    pv = pv_res.scalar_one_or_none()
    pv_detail = None
    if pv:
        details_obj = {}
        if pv.details:
            try:
                details_obj = json.loads(pv.details)
            except Exception:
                pass
        pv_detail = ProjectVerificationDetail(
            id=pv.id,
            repository=pv.repository,
            commit_sha=pv.commit_sha,
            build_status=pv.build_status,
            test_status=pv.test_status,
            lint_status=pv.lint_status,
            ci_status=pv.ci_status,
            overall_status=pv.overall_status,
            details=details_obj,
            checked_at=pv.checked_at
        )

    # Permission flags
    can_submit = bool(
        curr_prog_detail and
        curr_prog_detail.github_verified and
        curr_prog_detail.submission_status in ("PENDING", "CHANGES_REQUESTED")
    )
    can_review = bool(
        partner_prog_detail and
        partner_prog_detail.github_verified and
        partner_prog_detail.submission_status in ("SUBMITTED", "UNDER_REVIEW")
    )

    now_utc = datetime.now(timezone.utc)
    effective_deadline = task.deadline_utc + timedelta(minutes=duo.grace_period_minutes)

    return TodayProgressResponse(
        task_id=task.id,
        duo_id=duo.id,
        date=task.date,
        status=task.status,
        deadline_utc=task.deadline_utc,
        grace_period_minutes=duo.grace_period_minutes,
        is_expired=now_utc > effective_deadline,
        title=task.title,
        description=task.description,
        current_user_progress=curr_prog_detail,
        partner_user_progress=partner_prog_detail,
        project_verification=pv_detail,
        can_submit=can_submit,
        can_review=can_review,
        project_mode=duo.project_mode
    )

@router.get("/history", response_model=CalendarHistoryResponse)
async def get_calendar_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate contribution-style calendar data for the last 60 days.
    Colors:
    - Green: Both completed
    - Yellow: Only one completed
    - Red: Missed
    - Grey: Future / No Task
    """
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == current_user.id)
    )
    record = mem_res.first()
    if not record:
        raise HTTPException(status_code=404, detail="Not in a Duo")
    membership, duo = record

    streak_res = await db.execute(select(Streak).where(Streak.duo_id == duo.id))
    streak = streak_res.scalar_one_or_none()

    # Get members
    members = (await db.execute(
        select(DuoMember, User)
        .join(User, DuoMember.user_id == User.id)
        .where(DuoMember.duo_id == duo.id)
        .order_by(DuoMember.joined_at)
    )).all()

    user_a = members[0][1] if len(members) > 0 else None
    user_b = members[1][1] if len(members) > 1 else None

    # Fetch all tasks for duo
    tasks_res = await db.execute(
        select(DailyTask).where(DailyTask.duo_id == duo.id)
    )
    tasks = {t.date: t for t in tasks_res.scalars().all()}

    # Fetch all user progress for duo's tasks
    all_task_ids = [t.id for t in tasks.values()]
    progress_by_task = {}
    if all_task_ids:
        progs = (await db.execute(
            select(DailyUserProgress).where(DailyUserProgress.daily_task_id.in_(all_task_ids))
        )).scalars().all()
        for p in progs:
            progress_by_task.setdefault(p.daily_task_id, {})[p.user_id] = p

    # Build 60 days sequence up to today
    today_str = CompletionEngine.get_today_local_date_str(duo.timezone)
    today_date = datetime.strptime(today_str, "%Y-%m-%d").date()

    calendar_items: List[CalendarDayItem] = []
    total_completed = 0
    total_missed = 0

    for i in range(59, -1, -1):
        d = today_date - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")

        task = tasks.get(d_str)
        if not task:
            calendar_items.append(
                CalendarDayItem(
                    date=d_str,
                    status="NO_TASK",
                    both_completed=False,
                    user_a_verified=False,
                    user_b_verified=False
                )
            )
            continue

        progs = progress_by_task.get(task.id, {})
        u_a_prog = progs.get(user_a.id) if user_a else None
        u_b_prog = progs.get(user_b.id) if user_b else None

        a_verif = bool(u_a_prog and u_a_prog.github_verified)
        b_verif = bool(u_b_prog and u_b_prog.github_verified)
        is_completed = (task.status == "COMPLETED")
        is_missed = (task.status == "MISSED")

        if is_completed:
            day_status = "COMPLETED"  # Green
            total_completed += 1
        elif is_missed:
            day_status = "MISSED"     # Red
            total_missed += 1
        elif a_verif or b_verif:
            day_status = "PARTIAL"    # Yellow (Only one completed)
        else:
            day_status = "ACTIVE"

        calendar_items.append(
            CalendarDayItem(
                date=d_str,
                status=day_status,
                task_id=task.id,
                task_title=task.title,
                both_completed=is_completed,
                user_a_verified=a_verif,
                user_b_verified=b_verif,
                user_a_name=user_a.full_name if user_a else None,
                user_b_name=user_b.full_name if user_b else None,
                completed_at=task.updated_at if is_completed else None
            )
        )

    return CalendarHistoryResponse(
        duo_id=duo.id,
        days=calendar_items,
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        total_completed=total_completed,
        total_missed=total_missed
    )
