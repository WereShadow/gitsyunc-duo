import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    Project,
    ProjectTask,
    ProjectMilestone,
    TaskDependency,
    TaskReviewLog,
    TaskComment,
    TaskActivityLog,
    User,
    DuoMember,
)

logger = logging.getLogger(__name__)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ProjectEngine:
    @staticmethod
    async def log_activity(
        session: AsyncSession,
        project_id: str,
        action: str,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[str] = None
    ) -> TaskActivityLog:
        activity = TaskActivityLog(
            project_id=project_id,
            task_id=task_id,
            user_id=user_id,
            action=action,
            details=details,
            created_at=utc_now()
        )
        session.add(activity)
        return activity

    @classmethod
    async def get_task_with_relations(cls, session: AsyncSession, task_id: str) -> Optional[ProjectTask]:
        stmt = (
            select(ProjectTask)
            .options(
                selectinload(ProjectTask.creator),
                selectinload(ProjectTask.assignee),
                selectinload(ProjectTask.milestone),
                selectinload(ProjectTask.dependencies).selectinload(TaskDependency.depends_on_task),
                selectinload(ProjectTask.reviews).selectinload(TaskReviewLog.reviewer),
                selectinload(ProjectTask.comments).selectinload(TaskComment.user),
            )
            .where(ProjectTask.id == task_id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def is_task_blocked(cls, session: AsyncSession, task_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        stmt = (
            select(TaskDependency)
            .options(selectinload(TaskDependency.depends_on_task))
            .where(TaskDependency.task_id == task_id)
        )
        res = await session.execute(stmt)
        dependencies = res.scalars().all()
        
        blocked_by = []
        is_blocked = False
        for dep in dependencies:
            dep_task = dep.depends_on_task
            if dep_task:
                is_blocking = (dep_task.status != 'COMPLETED')
                if is_blocking:
                    is_blocked = True
                blocked_by.append({
                    'task_id': dep.task_id,
                    'depends_on_task_id': dep.depends_on_task_id,
                    'depends_on_title': dep_task.title,
                    'depends_on_status': dep_task.status,
                    'is_blocking': is_blocking
                })
        return is_blocked, blocked_by

    @classmethod
    async def can_user_access_project(cls, session: AsyncSession, project_id: str, user_id: str) -> bool:
        project_stmt = select(Project).where(Project.id == project_id)
        res = await session.execute(project_stmt)
        proj = res.scalar_one_or_none()
        if not proj:
            return False
        
        member_stmt = select(DuoMember).where(
            and_(DuoMember.duo_id == proj.duo_id, DuoMember.user_id == user_id)
        )
        m_res = await session.execute(member_stmt)
        return m_res.scalar_one_or_none() is not None

    @classmethod
    async def update_task_status(
        cls,
        session: AsyncSession,
        task: ProjectTask,
        new_status: str,
        user_id: str
    ) -> ProjectTask:
        current_status = task.status
        if current_status == new_status:
            return task

        if new_status in ['IN_PROGRESS', 'COMPLETED']:
            is_blocked, blockers = await cls.is_task_blocked(session, task.id)
            if is_blocked:
                blocking_titles = [b['depends_on_title'] for b in blockers if b['is_blocking']]
                raise ValueError(f'Cannot transition task to {new_status}: blocked by uncompleted tasks: ' + ', '.join(blocking_titles))

        task.status = new_status
        task.updated_at = utc_now()
        if new_status == 'COMPLETED':
            task.completed_at = utc_now()

        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=user_id,
            action='TASK_STATUS_CHANGED',
            details=f'Changed status from {current_status} to {new_status}'
        )
        return task

    @classmethod
    async def submit_task(
        cls,
        session: AsyncSession,
        task: ProjectTask,
        submit_data: Dict[str, Any],
        user_id: str
    ) -> ProjectTask:
        is_blocked, blockers = await cls.is_task_blocked(session, task.id)
        if is_blocked:
            blocking_titles = [b['depends_on_title'] for b in blockers if b['is_blocking']]
            raise ValueError('Cannot submit task: blocked by uncompleted tasks: ' + ', '.join(blocking_titles))

        if submit_data.get('branch'):
            task.branch = submit_data['branch']
        if submit_data.get('pull_request_url'):
            task.pull_request_url = submit_data['pull_request_url']
        if submit_data.get('pull_request_number'):
            task.pull_request_number = submit_data['pull_request_number']
        if submit_data.get('commit_sha'):
            task.latest_commit_sha = submit_data['commit_sha']
        if submit_data.get('commit_message'):
            task.latest_commit_message = submit_data['commit_message']
        if submit_data.get('changed_files'):
            task.changed_files = json.dumps(submit_data['changed_files'])
        if submit_data.get('submission_notes'):
            task.submission_notes = submit_data['submission_notes']

        task.submitted_at = utc_now()
        task.status = 'UNDER_REVIEW'
        task.verification_status = 'PASSED'
        task.updated_at = utc_now()

        commit_or_branch = task.latest_commit_sha or task.branch or 'work evidence'
        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=user_id,
            action='TASK_SUBMITTED',
            details=f'Submitted for peer review with {commit_or_branch}'
        )
        return task

    @classmethod
    async def review_task(
        cls,
        session: AsyncSession,
        task: ProjectTask,
        reviewer_id: str,
        review_status: str,
        comment: str,
        commit_sha: Optional[str] = None
    ) -> Tuple[ProjectTask, TaskReviewLog]:
        if task.assignee_id and task.assignee_id == reviewer_id:
            raise PermissionError('A member cannot approve or review their own assigned work.')

        review_log = TaskReviewLog(
            task_id=task.id,
            reviewer_id=reviewer_id,
            status=review_status,
            comment=comment,
            commit_sha=commit_sha or task.latest_commit_sha,
            created_at=utc_now()
        )
        session.add(review_log)

        if review_status == 'APPROVED':
            task.status = 'COMPLETED'
            task.approved_at = utc_now()
            task.completed_at = utc_now()
            action = 'TASK_APPROVED'
            details = f'Approved by teammate with note: {comment}'
        elif review_status == 'CHANGES_REQUESTED':
            task.status = 'CHANGES_REQUESTED'
            action = 'CHANGES_REQUESTED'
            details = f'Changes requested by teammate: {comment}'
        else:
            raise ValueError(f'Invalid review status: {review_status}')

        task.updated_at = utc_now()

        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=reviewer_id,
            action=action,
            details=details
        )
        return task, review_log

    @classmethod
    async def calculate_project_metrics(cls, session: AsyncSession, project_id: str) -> Dict[str, Any]:
        task_stmt = select(ProjectTask).where(ProjectTask.project_id == project_id)
        res = await session.execute(task_stmt)
        tasks = res.scalars().all()

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == 'COMPLETED')
        active = sum(1 for t in tasks if t.status in ['TODO', 'IN_PROGRESS', 'SUBMITTED', 'UNDER_REVIEW', 'CHANGES_REQUESTED', 'APPROVED'])
        awaiting_review = sum(1 for t in tasks if t.status in ['SUBMITTED', 'UNDER_REVIEW'])
        
        now = utc_now()
        overdue = sum(1 for t in tasks if t.deadline and t.deadline < now and t.status != 'COMPLETED')

        blocked_count = 0
        for t in tasks:
            if t.status not in ['COMPLETED', 'APPROVED']:
                is_b, _ = await cls.is_task_blocked(session, t.id)
                if is_b:
                    blocked_count += 1

        completion_pct = round((completed / total * 100), 1) if total > 0 else 0.0

        if overdue > 2 or (total > 0 and blocked_count > total / 2):
            health = 'DELAYED'
        elif overdue > 0 or blocked_count > 0:
            health = 'AT_RISK'
        else:
            health = 'ON_TRACK'

        return {
            'total_tasks': total,
            'completed_tasks': completed,
            'active_tasks': active,
            'blocked_tasks': blocked_count,
            'overdue_tasks': overdue,
            'tasks_awaiting_review': awaiting_review,
            'completion_percentage': completion_pct,
            'project_health': health
        }
