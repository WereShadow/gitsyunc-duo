import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.database import get_db
from app.models.entities import (
    User,
    Project,
    ProjectTask,
    ProjectMilestone,
    TaskDependency,
    TaskReviewLog,
    TaskComment,
    TaskActivityLog,
    DuoMember,
)
from app.api.deps import get_current_user
from app.schemas.project_tasks import (
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskResponse,
    TaskSubmit,
    TaskStatusUpdate,
    TaskReviewCreate,
    TaskReviewResponse,
    TaskCommentCreate,
    TaskCommentResponse,
    DependencyCreate,
    DependencyItem,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
    ProjectDashboardResponse,
    MemberDashboardResponse,
    MemberActivityStat,
    ActivityLogResponse,
)
from app.services.project_engine import ProjectEngine, utc_now

router = APIRouter(tags=['Project Collaboration'])

async def build_task_response(session: AsyncSession, task: ProjectTask) -> ProjectTaskResponse:
    is_blocked, blocked_by = await ProjectEngine.is_task_blocked(session, task.id)
    
    changed_files_list = []
    if task.changed_files:
        try:
            changed_files_list = json.loads(task.changed_files)
        except Exception:
            pass

    verification_details = None
    if task.verification_details:
        try:
            verification_details = json.loads(task.verification_details)
        except Exception:
            pass

    reviews_resp = []
    for r in task.reviews:
        reviews_resp.append(TaskReviewResponse(
            id=r.id,
            task_id=r.task_id,
            reviewer_id=r.reviewer_id,
            reviewer_name=r.reviewer.full_name if r.reviewer else None,
            reviewer_avatar=r.reviewer.avatar_url if r.reviewer else None,
            status=r.status,
            comment=r.comment,
            commit_sha=r.commit_sha,
            created_at=r.created_at
        ))

    return ProjectTaskResponse(
        id=task.id,
        project_id=task.project_id,
        milestone_id=task.milestone_id,
        milestone_title=task.milestone.title if task.milestone else None,
        creator_id=task.creator_id,
        creator_name=task.creator.full_name if task.creator else None,
        assignee_id=task.assignee_id,
        assignee_name=task.assignee.full_name if task.assignee else None,
        assignee_avatar=task.assignee.avatar_url if task.assignee else None,
        title=task.title,
        description=task.description,
        priority=task.priority,
        deadline=task.deadline,
        status=task.status,
        is_blocked=is_blocked,
        blocked_by=blocked_by,
        github_repo=task.github_repo,
        branch=task.branch,
        pull_request_url=task.pull_request_url,
        pull_request_number=task.pull_request_number,
        latest_commit_sha=task.latest_commit_sha,
        latest_commit_message=task.latest_commit_message,
        changed_files=changed_files_list,
        verification_status=task.verification_status,
        verification_details=verification_details,
        submission_notes=task.submission_notes,
        submitted_at=task.submitted_at,
        approved_at=task.approved_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        reviews=reviews_resp,
        comment_count=len(task.comments) if task.comments else 0
    )


# --- Milestones Endpoints ---
@router.get('/projects/{project_id}/milestones', response_model=List[MilestoneResponse])
async def list_milestones(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(ProjectMilestone)
        .options(selectinload(ProjectMilestone.tasks))
        .where(ProjectMilestone.project_id == project_id)
        .order_by(ProjectMilestone.created_at.asc())
    )
    res = await db.execute(stmt)
    milestones = res.scalars().all()
    
    resp = []
    for m in milestones:
        resp.append(MilestoneResponse(
            id=m.id,
            project_id=m.project_id,
            title=m.title,
            description=m.description,
            target_date=m.target_date,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
            task_count=len(m.tasks),
            completed_task_count=sum(1 for t in m.tasks if t.status == 'COMPLETED')
        ))
    return resp

@router.post('/projects/{project_id}/milestones', response_model=MilestoneResponse)
async def create_milestone(
    project_id: str,
    data: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    milestone = ProjectMilestone(
        project_id=project_id,
        title=data.title,
        description=data.description,
        target_date=data.target_date,
        status='OPEN'
    )
    db.add(milestone)
    await db.flush()
    await ProjectEngine.log_activity(
        session=db,
        project_id=project_id,
        action='MILESTONE_CREATED',
        user_id=current_user.id,
        details=f'Created milestone: {milestone.title}'
    )
    return MilestoneResponse(
        id=milestone.id,
        project_id=milestone.project_id,
        title=milestone.title,
        description=milestone.description,
        target_date=milestone.target_date,
        status=milestone.status,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
        task_count=0,
        completed_task_count=0
    )


# --- Project Tasks CRUD ---
@router.get('/projects/{project_id}/tasks', response_model=List[ProjectTaskResponse])
async def list_project_tasks(
    project_id: str,
    milestone_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias='status'),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(ProjectTask)
        .options(
            selectinload(ProjectTask.creator),
            selectinload(ProjectTask.assignee),
            selectinload(ProjectTask.milestone),
            selectinload(ProjectTask.dependencies).selectinload(TaskDependency.depends_on_task),
            selectinload(ProjectTask.reviews).selectinload(TaskReviewLog.reviewer),
            selectinload(ProjectTask.comments),
        )
        .where(ProjectTask.project_id == project_id)
        .order_by(desc(ProjectTask.created_at))
    )
    if milestone_id:
        stmt = stmt.where(ProjectTask.milestone_id == milestone_id)
    if assignee_id:
        stmt = stmt.where(ProjectTask.assignee_id == assignee_id)
    if status_filter:
        stmt = stmt.where(ProjectTask.status == status_filter)

    res = await db.execute(stmt)
    tasks = res.scalars().all()
    
    resp = []
    for t in tasks:
        resp.append(await build_task_response(db, t))
    return resp

@router.post('/projects/{project_id}/tasks', response_model=ProjectTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_project_task(
    project_id: str,
    data: ProjectTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = ProjectTask(
        project_id=project_id,
        creator_id=current_user.id,
        assignee_id=data.assignee_id,
        milestone_id=data.milestone_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        deadline=data.deadline,
        github_repo=data.github_repo,
        branch=data.branch,
        status='TODO' if data.assignee_id else 'BACKLOG',
    )
    db.add(task)
    await db.flush()

    if data.dependencies:
        for dep_id in data.dependencies:
            if dep_id != task.id:
                db.add(TaskDependency(task_id=task.id, depends_on_task_id=dep_id))
        await db.flush()

    await ProjectEngine.log_activity(
        session=db,
        project_id=project_id,
        task_id=task.id,
        user_id=current_user.id,
        action='TASK_CREATED',
        details=f'Created task: {task.title}'
    )

    fresh_task = await ProjectEngine.get_task_with_relations(db, task.id)
    return await build_task_response(db, fresh_task)

@router.get('/tasks/{task_id}', response_model=ProjectTaskResponse)
async def get_task_details(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    return await build_task_response(db, task)

@router.put('/tasks/{task_id}', response_model=ProjectTaskResponse)
async def update_task(
    task_id: str,
    data: ProjectTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.milestone_id is not None:
        task.milestone_id = data.milestone_id
    if data.assignee_id is not None:
        task.assignee_id = data.assignee_id
    if data.priority is not None:
        task.priority = data.priority
    if data.deadline is not None:
        task.deadline = data.deadline
    if data.github_repo is not None:
        task.github_repo = data.github_repo
    if data.branch is not None:
        task.branch = data.branch
    if data.pull_request_url is not None:
        task.pull_request_url = data.pull_request_url
    if data.status is not None:
        try:
            task = await ProjectEngine.update_task_status(db, task, data.status, current_user.id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    task.updated_at = utc_now()
    await db.flush()
    return await build_task_response(db, task)

@router.post('/tasks/{task_id}/status', response_model=ProjectTaskResponse)
async def update_status_transition(
    task_id: str,
    data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    try:
        task = await ProjectEngine.update_task_status(db, task, data.status, current_user.id)
        await db.flush()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await build_task_response(db, task)


# --- Dependencies ---
@router.post('/tasks/{task_id}/dependencies', response_model=ProjectTaskResponse)
async def add_task_dependency(
    task_id: str,
    data: DependencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if task_id == data.depends_on_task_id:
        raise HTTPException(status_code=400, detail='Task cannot depend on itself')

    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    dep_task = await ProjectEngine.get_task_with_relations(db, data.depends_on_task_id)
    if not dep_task:
        raise HTTPException(status_code=404, detail='Dependency task not found')

    existing = await db.execute(
        select(TaskDependency).where(
            and_(
                TaskDependency.task_id == task_id,
                TaskDependency.depends_on_task_id == data.depends_on_task_id
            )
        )
    )
    if not existing.scalar_one_or_none():
        dep = TaskDependency(task_id=task_id, depends_on_task_id=data.depends_on_task_id)
        db.add(dep)
        await db.flush()

    fresh = await ProjectEngine.get_task_with_relations(db, task_id)
    return await build_task_response(db, fresh)

@router.delete('/tasks/{task_id}/dependencies/{depends_on_task_id}', response_model=ProjectTaskResponse)
async def remove_task_dependency(
    task_id: str,
    depends_on_task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(TaskDependency).where(
        and_(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id
        )
    )
    res = await db.execute(stmt)
    dep = res.scalar_one_or_none()
    if dep:
        await db.delete(dep)
        await db.flush()

    fresh = await ProjectEngine.get_task_with_relations(db, task_id)
    return await build_task_response(db, fresh)


# --- Submit Task with GitHub Evidence ---
@router.post('/tasks/{task_id}/submit', response_model=ProjectTaskResponse)
async def submit_task_evidence(
    task_id: str,
    data: TaskSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    try:
        task = await ProjectEngine.submit_task(
            session=db,
            task=task,
            submit_data=data.dict(exclude_unset=True),
            user_id=current_user.id
        )
        await db.flush()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await build_task_response(db, task)


# --- Peer Review Endpoint ---
@router.post('/tasks/{task_id}/reviews', response_model=ProjectTaskResponse)
async def create_task_review(
    task_id: str,
    data: TaskReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    try:
        task, review = await ProjectEngine.review_task(
            session=db,
            task=task,
            reviewer_id=current_user.id,
            review_status=data.status,
            comment=data.comment,
            commit_sha=data.commit_sha
        )
        await db.flush()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fresh = await ProjectEngine.get_task_with_relations(db, task_id)
    return await build_task_response(db, fresh)


# --- Task Comments ---
@router.post('/tasks/{task_id}/comments', response_model=TaskCommentResponse)
async def add_task_comment(
    task_id: str,
    data: TaskCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = await ProjectEngine.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    comment = TaskComment(
        task_id=task.id,
        user_id=current_user.id,
        content=data.content
    )
    db.add(comment)
    await db.flush()

    return TaskCommentResponse(
        id=comment.id,
        task_id=comment.task_id,
        user_id=comment.user_id,
        user_name=current_user.full_name,
        user_avatar=current_user.avatar_url,
        content=comment.content,
        created_at=comment.created_at
    )


# --- Dashboards ---
@router.get('/projects/{project_id}/dashboard', response_model=ProjectDashboardResponse)
async def get_project_dashboard(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proj_stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(proj_stmt)
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail='Project not found')

    metrics = await ProjectEngine.calculate_project_metrics(db, project_id)

    # Milestones
    m_stmt = (
        select(ProjectMilestone)
        .options(selectinload(ProjectMilestone.tasks))
        .where(ProjectMilestone.project_id == project_id)
    )
    m_res = await db.execute(m_stmt)
    milestones_data = []
    for m in m_res.scalars().all():
        milestones_data.append(MilestoneResponse(
            id=m.id,
            project_id=m.project_id,
            title=m.title,
            description=m.description,
            target_date=m.target_date,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
            task_count=len(m.tasks),
            completed_task_count=sum(1 for t in m.tasks if t.status == 'COMPLETED')
        ))

    # Duo Members Activity Stats
    members_stmt = (
        select(DuoMember)
        .options(selectinload(DuoMember.user))
        .where(DuoMember.duo_id == proj.duo_id)
    )
    members_res = await db.execute(members_stmt)
    members = members_res.scalars().all()

    # All tasks for member aggregation
    tasks_stmt = (
        select(ProjectTask)
        .options(
            selectinload(ProjectTask.creator),
            selectinload(ProjectTask.assignee),
            selectinload(ProjectTask.milestone),
            selectinload(ProjectTask.dependencies).selectinload(TaskDependency.depends_on_task),
            selectinload(ProjectTask.reviews).selectinload(TaskReviewLog.reviewer),
            selectinload(ProjectTask.comments),
        )
        .where(ProjectTask.project_id == project_id)
    )
    all_tasks = (await db.execute(tasks_stmt)).scalars().all()

    member_stats = []
    for m in members:
        u = m.user
        m_tasks = [t for t in all_tasks if t.assignee_id == u.id]
        member_stats.append(MemberActivityStat(
            user_id=u.id,
            full_name=u.full_name,
            avatar_url=u.avatar_url,
            assigned_count=len(m_tasks),
            completed_count=sum(1 for t in m_tasks if t.status == 'COMPLETED'),
            in_progress_count=sum(1 for t in m_tasks if t.status == 'IN_PROGRESS'),
            submitted_count=sum(1 for t in m_tasks if t.status == 'SUBMITTED'),
            awaiting_review_count=sum(1 for t in m_tasks if t.status == 'UNDER_REVIEW')
        ))

    # Recent activities
    act_stmt = (
        select(TaskActivityLog)
        .options(selectinload(TaskActivityLog.user), selectinload(TaskActivityLog.task))
        .where(TaskActivityLog.project_id == project_id)
        .order_by(desc(TaskActivityLog.created_at))
        .limit(20)
    )
    act_res = await db.execute(act_stmt)
    recent_activity = [
        ActivityLogResponse(
            id=a.id,
            project_id=a.project_id,
            task_id=a.task_id,
            task_title=a.task.title if a.task else None,
            user_id=a.user_id,
            user_name=a.user.full_name if a.user else 'System',
            action=a.action,
            details=a.details,
            created_at=a.created_at
        )
        for a in act_res.scalars().all()
    ]

    recent_tasks_resp = []
    for t in all_tasks[:15]:
        recent_tasks_resp.append(await build_task_response(db, t))

    return ProjectDashboardResponse(
        project_id=proj.id,
        project_name=proj.project_name,
        github_repo_full_name=proj.github_repo_full_name,
        completion_percentage=metrics['completion_percentage'],
        total_tasks=metrics['total_tasks'],
        active_tasks=metrics['active_tasks'],
        completed_tasks=metrics['completed_tasks'],
        blocked_tasks=metrics['blocked_tasks'],
        overdue_tasks=metrics['overdue_tasks'],
        tasks_awaiting_review=metrics['tasks_awaiting_review'],
        project_health=metrics['project_health'],
        milestones=milestones_data,
        member_activities=member_stats,
        recent_activity=recent_activity,
        recent_tasks=recent_tasks_resp
    )


@router.get('/members/me/dashboard', response_model=MemberDashboardResponse)
async def get_member_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(ProjectTask)
        .options(
            selectinload(ProjectTask.creator),
            selectinload(ProjectTask.assignee),
            selectinload(ProjectTask.milestone),
            selectinload(ProjectTask.dependencies).selectinload(TaskDependency.depends_on_task),
            selectinload(ProjectTask.reviews).selectinload(TaskReviewLog.reviewer),
            selectinload(ProjectTask.comments),
        )
        .order_by(desc(ProjectTask.updated_at))
    )
    res = await db.execute(stmt)
    all_tasks = res.scalars().all()

    assigned_tasks = []
    submitted_tasks = []
    tasks_requiring_changes = []
    completed_tasks = []
    tasks_awaiting_my_review = []
    overdue_count = 0
    now = utc_now()

    for t in all_tasks:
        resp_t = await build_task_response(db, t)
        if t.assignee_id == current_user.id:
            if t.status in ['BACKLOG', 'TODO', 'IN_PROGRESS']:
                assigned_tasks.append(resp_t)
            elif t.status in ['SUBMITTED', 'UNDER_REVIEW']:
                submitted_tasks.append(resp_t)
            elif t.status == 'CHANGES_REQUESTED':
                tasks_requiring_changes.append(resp_t)
            elif t.status == 'COMPLETED':
                completed_tasks.append(resp_t)
            
            if t.deadline and t.deadline < now and t.status != 'COMPLETED':
                overdue_count += 1
        else:
            if t.status in ['SUBMITTED', 'UNDER_REVIEW']:
                tasks_awaiting_my_review.append(resp_t)

    return MemberDashboardResponse(
        user_id=current_user.id,
        assigned_tasks=assigned_tasks,
        submitted_tasks=submitted_tasks,
        tasks_awaiting_my_review=tasks_awaiting_my_review,
        tasks_requiring_changes=tasks_requiring_changes,
        completed_tasks=completed_tasks,
        overdue_count=overdue_count
    )
