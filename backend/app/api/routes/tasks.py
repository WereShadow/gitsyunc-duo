import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
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
    GitHubAccount,
    TaskReview,
    ProjectVerification,
)
from app.schemas.task import DailyTaskCreate, DailyTaskResponse, UserTaskProgressDetail, ProjectVerificationDetail
from app.schemas.review import ReviewResponse
from app.api.deps import get_current_user
from app.services.completion_engine import CompletionEngine
from app.services.review_service import ReviewService
from app.services.verification_service import ProjectVerificationService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

async def _build_task_response(session: AsyncSession, task: DailyTask) -> DailyTaskResponse:
    # 1. Fetch duo members
    members_res = await session.execute(
        select(DuoMember, User)
        .join(User, DuoMember.user_id == User.id)
        .where(DuoMember.duo_id == task.duo_id)
        .order_by(DuoMember.joined_at)
    )
    members_data = members_res.all()
    user_map = {m.user_id: user for m, user in members_data}

    # 2. Fetch user progress
    prog_res = await session.execute(
        select(DailyUserProgress).where(DailyUserProgress.daily_task_id == task.id)
    )
    progress_list = prog_res.scalars().all()
    progress_map = {p.user_id: p for p in progress_list}

    user_progress_details: List[UserTaskProgressDetail] = []
    for idx, (m, user) in enumerate(members_data):
        gh_res = await session.execute(
            select(GitHubAccount).where(GitHubAccount.user_id == user.id)
        )
        gh_acc = gh_res.scalar_one_or_none()

        assigned = task.user_a_task if idx == 0 else task.user_b_task
        p = progress_map.get(user.id)

        files = []
        if p and p.changed_files:
            try:
                files = json.loads(p.changed_files)
            except Exception:
                files = []

        user_progress_details.append(
            UserTaskProgressDetail(
                user_id=user.id,
                user_name=user.full_name,
                user_email=user.email,
                avatar_url=user.avatar_url,
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
        )

    # 3. Fetch reviews
    reviews_res = await session.execute(
        select(TaskReview, User)
        .join(User, TaskReview.reviewer_id == User.id)
        .where(TaskReview.daily_task_id == task.id)
        .order_by(TaskReview.created_at.desc())
    )
    reviews_list = [
        ReviewResponse(
            id=r.id,
            daily_task_id=r.daily_task_id,
            task_owner_id=r.task_owner_id,
            task_owner_name=user_map.get(r.task_owner_id, User(full_name="Partner")).full_name,
            reviewer_id=r.reviewer_id,
            reviewer_name=reviewer.full_name,
            status=r.status,
            comment=r.comment,
            commit_sha=r.commit_sha,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r, reviewer in reviews_res.all()
    ]

    # 4. Fetch project verifications
    verif_res = await session.execute(
        select(ProjectVerification)
        .where(ProjectVerification.daily_task_id == task.id)
        .order_by(ProjectVerification.checked_at.desc())
    )
    verifications = []
    for v in verif_res.scalars().all():
        details_obj = {}
        if v.details:
            try:
                details_obj = json.loads(v.details)
            except Exception:
                pass
        verifications.append(
            ProjectVerificationDetail(
                id=v.id,
                repository=v.repository,
                commit_sha=v.commit_sha,
                build_status=v.build_status,
                test_status=v.test_status,
                lint_status=v.lint_status,
                ci_status=v.ci_status,
                overall_status=v.overall_status,
                details=details_obj,
                checked_at=v.checked_at
            )
        )

    return DailyTaskResponse(
        id=task.id,
        duo_id=task.duo_id,
        date=task.date,
        title=task.title,
        description=task.description,
        user_a_task=task.user_a_task,
        user_b_task=task.user_b_task,
        github_requirement=task.github_requirement,
        min_commits_required=task.min_commits_required,
        deadline_utc=task.deadline_utc,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        user_progress=user_progress_details,
        reviews=reviews_list,
        verifications=verifications
    )

@router.post("", response_model=DailyTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_task(
    data: DailyTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Find user's duo
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == current_user.id)
    )
    record = mem_res.first()
    if not record:
        raise HTTPException(status_code=400, detail="You are not in an active Duo.")
    membership, duo = record

    # Calculate date in duo timezone
    target_date = data.date or CompletionEngine.get_today_local_date_str(duo.timezone)

    # Check if task already exists for this date
    existing_res = await db.execute(
        select(DailyTask).where(
            and_(
                DailyTask.duo_id == duo.id,
                DailyTask.date == target_date
            )
        )
    )
    existing_task = existing_res.scalar_one_or_none()
    if existing_task:
        # If task exists, update its details
        existing_task.title = data.title
        existing_task.description = data.description
        existing_task.user_a_task = data.user_a_task
        existing_task.user_b_task = data.user_b_task
        existing_task.github_requirement = data.github_requirement
        existing_task.min_commits_required = data.min_commits_required
        existing_task.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_task)
        return await _build_task_response(db, existing_task)

    # Calculate deadline in UTC
    _, _, deadline_utc = CompletionEngine.get_day_boundaries(
        duo.timezone,
        target_date,
        duo.deadline_time
    )

    now = datetime.now(timezone.utc)
    task = DailyTask(
        duo_id=duo.id,
        date=target_date,
        title=data.title,
        description=data.description,
        user_a_task=data.user_a_task,
        user_b_task=data.user_b_task,
        github_requirement=data.github_requirement,
        min_commits_required=data.min_commits_required,
        deadline_utc=deadline_utc,
        status="ACTIVE",
        created_at=now,
        updated_at=now
    )
    db.add(task)
    await db.flush()

    # Initialize progress for both members
    all_members = (await db.execute(
        select(DuoMember).where(DuoMember.duo_id == duo.id)
    )).scalars().all()

    for m in all_members:
        prog = DailyUserProgress(
            daily_task_id=task.id,
            user_id=m.user_id,
            github_verified=False,
            commit_count=0,
            submission_status="PENDING",
            review_status="PENDING"
        )
        db.add(prog)

    await db.commit()
    await db.refresh(task)

    return await _build_task_response(db, task)

@router.get("/today", response_model=Optional[DailyTaskResponse])
async def get_today_task(
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
        return None
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
        # Check if yesterday's task needs evaluation
        return None

    # Evaluate task completion authoritatively
    await CompletionEngine.evaluate_task_completion(db, task)
    await db.commit()
    await db.refresh(task)

    return await _build_task_response(db, task)

@router.get("/history", response_model=List[DailyTaskResponse])
async def get_task_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    mem_res = await db.execute(
        select(DuoMember).where(DuoMember.user_id == current_user.id)
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        return []

    tasks_res = await db.execute(
        select(DailyTask)
        .where(DailyTask.duo_id == membership.duo_id)
        .order_by(DailyTask.date.desc())
    )
    tasks = tasks_res.scalars().all()

    output = []
    for t in tasks:
        output.append(await _build_task_response(db, t))
    return output

@router.get("/{id}", response_model=DailyTaskResponse)
async def get_task_by_id(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task_res = await db.execute(select(DailyTask).where(DailyTask.id == id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Authorize user belongs to duo
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

    await CompletionEngine.evaluate_task_completion(db, task)
    await db.commit()
    await db.refresh(task)

    return await _build_task_response(db, task)

@router.post("/{id}/submit")
async def submit_task_for_review(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """User submits their uploaded work for peer review."""
    result = await ReviewService.submit_task(db, id, current_user.id)
    await db.commit()
    return result

@router.post("/{id}/verify-project")
async def trigger_project_verification(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger automated project checks for Shared Project Mode."""
    task_res = await db.execute(select(DailyTask).where(DailyTask.id == id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    verif = await ProjectVerificationService.run_verification(db, id)
    await db.commit()
    return {
        "success": True,
        "overall_status": verif.overall_status,
        "build_status": verif.build_status,
        "test_status": verif.test_status,
        "ci_status": verif.ci_status,
        "lint_status": verif.lint_status,
    }
