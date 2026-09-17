import pytest
from datetime import datetime, timezone, timedelta
from app.models.entities import User, Duo, DuoMember, Project, ProjectMilestone, ProjectTask, TaskDependency
from app.services.project_engine import ProjectEngine
from app.core.security import get_password_hash

@pytest.mark.asyncio
async def test_task_lifecycle_and_blocking_dependencies(db_session):
    now = datetime.now(timezone.utc)
    
    # 1. Create Users
    user_a = User(email='alice@example.com', hashed_password=get_password_hash('pass'), full_name='Alice')
    user_b = User(email='bob@example.com', hashed_password=get_password_hash('pass'), full_name='Bob')
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    # 2. Create Duo & Project
    duo = Duo(name='Platform Team', invite_code='CODE-1234', created_by=user_a.id)
    db_session.add(duo)
    await db_session.flush()

    m_a = DuoMember(duo_id=duo.id, user_id=user_a.id, role='CREATOR')
    m_b = DuoMember(duo_id=duo.id, user_id=user_b.id, role='PARTNER')
    db_session.add_all([m_a, m_b])

    project = Project(
        duo_id=duo.id,
        project_name='GitSync Core',
        github_repo_owner='WereShadow',
        github_repo_name='gitsync-duo',
        github_repo_full_name='WereShadow/gitsync-duo'
    )
    db_session.add(project)
    await db_session.flush()

    # 3. Create Upstream Task (Database Setup) assigned to Alice
    task1 = ProjectTask(
        project_id=project.id,
        creator_id=user_a.id,
        assignee_id=user_a.id,
        title='Database Schema & Migrations',
        status='TODO'
    )
    # Downstream Task (Auth API) assigned to Bob
    task2 = ProjectTask(
        project_id=project.id,
        creator_id=user_a.id,
        assignee_id=user_b.id,
        title='Authentication API',
        status='TODO'
    )
    db_session.add_all([task1, task2])
    await db_session.flush()

    # Set dependency: task2 depends on task1
    dep = TaskDependency(task_id=task2.id, depends_on_task_id=task1.id)
    db_session.add(dep)
    await db_session.flush()

    # 4. Verify Task 2 is BLOCKED
    is_blocked, blockers = await ProjectEngine.is_task_blocked(db_session, task2.id)
    assert is_blocked is True
    assert len(blockers) == 1
    assert blockers[0]['is_blocking'] is True

    # 5. Trying to start or submit Task 2 while blocked raises error
    with pytest.raises(ValueError) as exc:
        await ProjectEngine.update_task_status(db_session, task2, 'IN_PROGRESS', user_b.id)
    assert 'blocked by uncompleted tasks' in str(exc.value)

    # 6. Alice begins and submits Task 1
    await ProjectEngine.update_task_status(db_session, task1, 'IN_PROGRESS', user_a.id)
    await ProjectEngine.submit_task(
        db_session,
        task1,
        {'branch': 'feature/db-schema', 'commit_sha': 'a1b2c3d', 'commit_message': 'feat: initial schema'},
        user_a.id
    )
    assert task1.status == 'UNDER_REVIEW'

    # 7. Alice cannot approve her own task (Self-approval blocked)
    with pytest.raises(PermissionError) as exc:
        await ProjectEngine.review_task(
            db_session,
            task1,
            reviewer_id=user_a.id,
            review_status='APPROVED',
            comment='Looks good to me'
        )
    assert 'cannot approve or review their own assigned work' in str(exc.value)

    # 8. Bob reviews Task 1 -> Requests Changes
    await ProjectEngine.review_task(
        db_session,
        task1,
        reviewer_id=user_b.id,
        review_status='CHANGES_REQUESTED',
        comment='Please add index on email column'
    )
    assert task1.status == 'CHANGES_REQUESTED'

    # 9. Alice updates and resubmits
    await ProjectEngine.update_task_status(db_session, task1, 'IN_PROGRESS', user_a.id)
    await ProjectEngine.submit_task(
        db_session,
        task1,
        {'commit_sha': 'e4f5g6h', 'commit_message': 'fix: add unique index on email'},
        user_a.id
    )

    # 10. Bob reviews again -> Approves
    await ProjectEngine.review_task(
        db_session,
        task1,
        reviewer_id=user_b.id,
        review_status='APPROVED',
        comment='LGTM! Clean indices.'
    )
    assert task1.status == 'COMPLETED'
    assert task1.completed_at is not None

    # 11. Now Task 2 should NO LONGER BE BLOCKED
    is_blocked2, blockers2 = await ProjectEngine.is_task_blocked(db_session, task2.id)
    assert is_blocked2 is False

    # 12. Bob can now begin Task 2
    await ProjectEngine.update_task_status(db_session, task2, 'IN_PROGRESS', user_b.id)
    assert task2.status == 'IN_PROGRESS'

    # 13. Check metrics calculation
    metrics = await ProjectEngine.calculate_project_metrics(db_session, project.id)
    assert metrics['total_tasks'] == 2
    assert metrics['completed_tasks'] == 1
    assert metrics['completion_percentage'] == 50.0
    assert metrics['blocked_tasks'] == 0
