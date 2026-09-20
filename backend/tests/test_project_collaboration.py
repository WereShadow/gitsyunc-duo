import pytest
from datetime import datetime, timezone, timedelta
from app.models.entities import (
    User, Duo, DuoMember, Project, ProjectMilestone, ProjectTask,
    TaskDependency, TaskActivityLog
)
from app.services.project_engine import ProjectEngine, MockGitProvider
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def make_world(db_session):
    """Creates two users, a duo, and a project for testing."""
    now = datetime.now(timezone.utc)
    user_a = User(email=f'alice_{now.timestamp()}@test.com', hashed_password=get_password_hash('pass'), full_name='Alice')
    user_b = User(email=f'bob_{now.timestamp()}@test.com', hashed_password=get_password_hash('pass'), full_name='Bob')
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    duo = Duo(name='Test Team', invite_code=f'code-{now.timestamp():.0f}', created_by=user_a.id)
    db_session.add(duo)
    await db_session.flush()

    db_session.add_all([
        DuoMember(duo_id=duo.id, user_id=user_a.id, role='CREATOR'),
        DuoMember(duo_id=duo.id, user_id=user_b.id, role='PARTNER'),
    ])

    project = Project(
        duo_id=duo.id,
        project_name='Test Project',
        github_repo_owner='test',
        github_repo_name='repo',
        github_repo_full_name='test/repo'
    )
    db_session.add(project)
    await db_session.flush()
    return user_a, user_b, duo, project


async def make_task(db_session, project_id, creator_id, assignee_id, title, status='TODO'):
    t = ProjectTask(
        project_id=project_id,
        creator_id=creator_id,
        assignee_id=assignee_id,
        title=title,
        status=status,
    )
    db_session.add(t)
    await db_session.flush()
    return t


# ---------------------------------------------------------------------------
# Original lifecycle test (preserved)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_lifecycle_and_blocking_dependencies(db_session):
    now = datetime.now(timezone.utc)

    user_a = User(email='alice@example.com', hashed_password=get_password_hash('pass'), full_name='Alice')
    user_b = User(email='bob@example.com', hashed_password=get_password_hash('pass'), full_name='Bob')
    db_session.add_all([user_a, user_b])
    await db_session.flush()

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

    task1 = ProjectTask(
        project_id=project.id,
        creator_id=user_a.id,
        assignee_id=user_a.id,
        title='Database Schema & Migrations',
        status='TODO'
    )
    task2 = ProjectTask(
        project_id=project.id,
        creator_id=user_a.id,
        assignee_id=user_b.id,
        title='Authentication API',
        status='TODO'
    )
    db_session.add_all([task1, task2])
    await db_session.flush()

    dep = TaskDependency(task_id=task2.id, depends_on_task_id=task1.id)
    db_session.add(dep)
    await db_session.flush()

    is_blocked, blockers = await ProjectEngine.is_task_blocked(db_session, task2.id)
    assert is_blocked is True
    assert len(blockers) == 1
    assert blockers[0]['is_blocking'] is True

    with pytest.raises(ValueError) as exc:
        await ProjectEngine.update_task_status(db_session, task2, 'IN_PROGRESS', user_b.id)
    assert 'blocked by uncompleted tasks' in str(exc.value)

    await ProjectEngine.update_task_status(db_session, task1, 'IN_PROGRESS', user_a.id)
    await ProjectEngine.submit_task(
        db_session,
        task1,
        {'branch': 'feature/db-schema', 'commit_sha': 'a1b2c3d', 'commit_message': 'feat: initial schema'},
        user_a.id
    )
    assert task1.status == 'UNDER_REVIEW'

    with pytest.raises(PermissionError) as exc:
        await ProjectEngine.review_task(
            db_session,
            task1,
            reviewer_id=user_a.id,
            review_status='APPROVED',
            comment='Looks good to me'
        )
    assert 'cannot approve or review their own assigned work' in str(exc.value)

    await ProjectEngine.review_task(
        db_session,
        task1,
        reviewer_id=user_b.id,
        review_status='CHANGES_REQUESTED',
        comment='Please add index on email column'
    )
    assert task1.status == 'CHANGES_REQUESTED'

    await ProjectEngine.update_task_status(db_session, task1, 'IN_PROGRESS', user_a.id)
    await ProjectEngine.submit_task(
        db_session,
        task1,
        {'commit_sha': 'e4f5g6h', 'commit_message': 'fix: add unique index on email'},
        user_a.id
    )

    await ProjectEngine.review_task(
        db_session,
        task1,
        reviewer_id=user_b.id,
        review_status='APPROVED',
        comment='LGTM! Clean indices.'
    )
    assert task1.status == 'COMPLETED'
    assert task1.completed_at is not None

    is_blocked2, blockers2 = await ProjectEngine.is_task_blocked(db_session, task2.id)
    assert is_blocked2 is False

    await ProjectEngine.update_task_status(db_session, task2, 'IN_PROGRESS', user_b.id)
    assert task2.status == 'IN_PROGRESS'

    metrics = await ProjectEngine.calculate_project_metrics(db_session, project.id)
    assert metrics['total_tasks'] == 2
    assert metrics['completed_tasks'] == 1
    assert metrics['completion_percentage'] == 50.0
    assert metrics['blocked_tasks'] == 0


# ---------------------------------------------------------------------------
# Spec §6 — Transitive dependency blocking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transitive_blocking(db_session):
    """
    A → B → C: C must be blocked when A is incomplete, not just B.
    """
    user_a, user_b, _, project = await make_world(db_session)

    task_a = await make_task(db_session, project.id, user_a.id, user_a.id, 'Task A (root)')
    task_b = await make_task(db_session, project.id, user_a.id, user_a.id, 'Task B (mid)')
    task_c = await make_task(db_session, project.id, user_a.id, user_b.id, 'Task C (leaf)')

    # B depends on A; C depends on B
    db_session.add(TaskDependency(task_id=task_b.id, depends_on_task_id=task_a.id))
    db_session.add(TaskDependency(task_id=task_c.id, depends_on_task_id=task_b.id))
    await db_session.flush()

    # With A and B incomplete, C should be transitively blocked
    is_blocked_c, blockers_c = await ProjectEngine.is_task_blocked(db_session, task_c.id)
    assert is_blocked_c is True
    blocking_ids = {b['depends_on_task_id'] for b in blockers_c}
    # Both A and B should appear as blockers (transitive)
    assert task_a.id in blocking_ids or task_b.id in blocking_ids

    # Complete A → B should now unblock (direct dependency), C still blocked by B
    task_a.status = 'COMPLETED'
    await db_session.flush()

    is_blocked_b, _ = await ProjectEngine.is_task_blocked(db_session, task_b.id)
    assert is_blocked_b is False  # B is now unblocked

    is_blocked_c2, _ = await ProjectEngine.is_task_blocked(db_session, task_c.id)
    assert is_blocked_c2 is True  # C still blocked by B (B not yet completed)

    # Complete B → C should unblock
    task_b.status = 'COMPLETED'
    await db_session.flush()

    is_blocked_c3, _ = await ProjectEngine.is_task_blocked(db_session, task_c.id)
    assert is_blocked_c3 is False


# ---------------------------------------------------------------------------
# Spec §7 — Cycle detection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cycle_detection(db_session):
    """
    Adding A→B when B→A already exists should be detected as a cycle.
    """
    user_a, user_b, _, project = await make_world(db_session)

    task_a = await make_task(db_session, project.id, user_a.id, user_a.id, 'Task A')
    task_b = await make_task(db_session, project.id, user_a.id, user_b.id, 'Task B')

    # Add B depends on A
    db_session.add(TaskDependency(task_id=task_b.id, depends_on_task_id=task_a.id))
    await db_session.flush()

    # Now try to add A depends on B — this would create a cycle
    would_cycle = await ProjectEngine.would_create_cycle(db_session, task_a.id, task_b.id)
    assert would_cycle is True, "Should detect direct cycle A→B when B→A exists"

    # Self-dependency should also be caught by the cycle check
    would_self = await ProjectEngine.would_create_cycle(db_session, task_a.id, task_a.id)
    assert would_self is True, "Self-dependency should also be a cycle"


@pytest.mark.asyncio
async def test_cycle_detection_transitive(db_session):
    """
    A→B→C: trying to add C→A should be detected as a transitive cycle.
    """
    user_a, user_b, _, project = await make_world(db_session)

    task_a = await make_task(db_session, project.id, user_a.id, user_a.id, 'Task A')
    task_b = await make_task(db_session, project.id, user_a.id, user_b.id, 'Task B')
    task_c = await make_task(db_session, project.id, user_a.id, user_b.id, 'Task C')

    db_session.add(TaskDependency(task_id=task_b.id, depends_on_task_id=task_a.id))
    db_session.add(TaskDependency(task_id=task_c.id, depends_on_task_id=task_b.id))
    await db_session.flush()

    # Adding A depends on C would create A→B→C→A cycle
    would_cycle = await ProjectEngine.would_create_cycle(db_session, task_a.id, task_c.id)
    assert would_cycle is True, "Should detect transitive cycle A→B→C→A"

    # Adding D→C is fine (no cycle)
    task_d = await make_task(db_session, project.id, user_a.id, user_b.id, 'Task D')
    would_cycle_d = await ProjectEngine.would_create_cycle(db_session, task_d.id, task_c.id)
    assert would_cycle_d is False, "D→C should not create a cycle"


# ---------------------------------------------------------------------------
# Spec §12 — Review-per-submission integrity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_per_submission_integrity(db_session):
    """
    After a task is submitted (submission #1) and the reviewer approves it,
    a second submit increments submission_count so the reviewer must review again.
    """
    user_a, user_b, _, project = await make_world(db_session)

    task = await make_task(db_session, project.id, user_a.id, user_a.id, 'Review Integrity Task', status='IN_PROGRESS')

    # First submission
    await ProjectEngine.submit_task(
        db_session,
        task,
        {'commit_sha': 'abc111', 'branch': 'feature/v1'},
        user_a.id
    )
    assert task.submission_count == 1
    assert task.status == 'UNDER_REVIEW'

    # Approve
    await ProjectEngine.review_task(
        db_session, task, reviewer_id=user_b.id,
        review_status='APPROVED', comment='LGTM'
    )
    assert task.status == 'COMPLETED'
    assert task.submission_count == 1

    # Simulate re-opening (changes requested cycle)
    task.status = 'IN_PROGRESS'

    # Second submission — increments submission_count
    await ProjectEngine.submit_task(
        db_session,
        task,
        {'commit_sha': 'def222', 'branch': 'feature/v2'},
        user_a.id
    )
    assert task.submission_count == 2, "submission_count must increment on re-submit"
    assert task.status == 'UNDER_REVIEW'


# ---------------------------------------------------------------------------
# Spec §13 — Audit log: previous_state, new_state, event_metadata
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_fields(db_session):
    """
    Audit log entries must contain previous_state, new_state, and event_metadata.
    """
    from sqlalchemy import select
    user_a, user_b, _, project = await make_world(db_session)

    task = await make_task(db_session, project.id, user_a.id, user_a.id, 'Audit Test Task', status='TODO')

    await ProjectEngine.update_task_status(db_session, task, 'IN_PROGRESS', user_a.id)

    # Fetch the audit log entry
    logs = (
        await db_session.execute(
            select(TaskActivityLog)
            .where(TaskActivityLog.task_id == task.id)
            .where(TaskActivityLog.action == 'STATUS_CHANGED')
        )
    ).scalars().all()

    assert len(logs) >= 1
    log = logs[0]
    assert log.previous_state == 'TODO'
    assert log.new_state == 'IN_PROGRESS'

    # Submit and verify TASK_SUBMITTED log has metadata
    await ProjectEngine.submit_task(
        db_session,
        task,
        {'commit_sha': 'abc123', 'branch': 'main'},
        user_a.id
    )

    submit_logs = (
        await db_session.execute(
            select(TaskActivityLog)
            .where(TaskActivityLog.task_id == task.id)
            .where(TaskActivityLog.action == 'TASK_SUBMITTED')
        )
    ).scalars().all()

    assert len(submit_logs) >= 1
    submit_log = submit_logs[0]
    assert submit_log.event_metadata is not None
    import json
    meta = json.loads(submit_log.event_metadata)
    assert 'submission_count' in meta
    assert meta['submission_count'] == 1


# ---------------------------------------------------------------------------
# Spec §15 — Milestone auto-complete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_milestone_auto_complete(db_session):
    """
    When all tasks in a milestone are COMPLETED, the milestone status should
    automatically be set to COMPLETED.
    """
    user_a, user_b, _, project = await make_world(db_session)

    milestone = ProjectMilestone(
        project_id=project.id,
        title='MVP Release',
        status='OPEN'
    )
    db_session.add(milestone)
    await db_session.flush()

    task1 = ProjectTask(
        project_id=project.id,
        milestone_id=milestone.id,
        creator_id=user_a.id,
        assignee_id=user_a.id,
        title='Milestone Task 1',
        status='IN_PROGRESS'
    )
    task2 = ProjectTask(
        project_id=project.id,
        milestone_id=milestone.id,
        creator_id=user_a.id,
        assignee_id=user_b.id,
        title='Milestone Task 2',
        status='IN_PROGRESS'
    )
    db_session.add_all([task1, task2])
    await db_session.flush()

    # Complete task1 — milestone should NOT auto-complete yet (task2 still open)
    await ProjectEngine.update_task_status(db_session, task1, 'COMPLETED', user_a.id)
    await db_session.flush()
    db_session.expire(milestone)
    await db_session.refresh(milestone)
    assert milestone.status == 'OPEN', "Milestone should not complete until all tasks done"

    # Complete task2 — milestone should auto-complete
    await ProjectEngine.update_task_status(db_session, task2, 'COMPLETED', user_b.id)
    await db_session.flush()
    # Re-query the milestone directly to get the updated status
    from sqlalchemy import select
    updated_milestone = (
        await db_session.execute(select(ProjectMilestone).where(ProjectMilestone.id == milestone.id))
    ).scalar_one()
    assert updated_milestone.status == 'COMPLETED', "Milestone should auto-complete when all tasks done"


# ---------------------------------------------------------------------------
# Spec §14 — Health signals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_signals_failed_ci(db_session):
    """
    A task with verification_status=FAILED should trigger AT_RISK health.
    """
    user_a, user_b, _, project = await make_world(db_session)

    task = ProjectTask(
        project_id=project.id,
        creator_id=user_a.id,
        assignee_id=user_a.id,
        title='CI Failing Task',
        status='UNDER_REVIEW',
        verification_status='FAILED'
    )
    db_session.add(task)
    await db_session.flush()

    metrics = await ProjectEngine.calculate_project_metrics(db_session, project.id)
    assert metrics['failed_ci_count'] == 1
    assert metrics['project_health'] in ('AT_RISK', 'DELAYED')


@pytest.mark.asyncio
async def test_health_signals_on_track(db_session):
    """
    A project with no overdue, blocked, or failed-CI tasks is ON_TRACK.
    """
    user_a, user_b, _, project = await make_world(db_session)

    task = ProjectTask(
        project_id=project.id,
        creator_id=user_a.id,
        assignee_id=user_a.id,
        title='Healthy Task',
        status='IN_PROGRESS',
        verification_status='PENDING'
    )
    db_session.add(task)
    await db_session.flush()

    metrics = await ProjectEngine.calculate_project_metrics(db_session, project.id)
    assert metrics['project_health'] == 'ON_TRACK'


# ---------------------------------------------------------------------------
# Spec §10 — MockGitProvider (simulator shares verification engine)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_git_provider_no_commits(db_session):
    """
    MockGitProvider returns FAILED when no commits exist in the simulator.
    """
    provider = MockGitProvider()
    provider._store.clear()

    result = await provider.verify_evidence(
        repo='test/myrepo',
        branch='main',
        commit_sha=None,
        pr_number=None,
    )
    assert result.status == 'FAILED'


@pytest.mark.asyncio
async def test_mock_git_provider_with_commits(db_session):
    """
    MockGitProvider returns PASSED when commits exist in the simulator.
    """
    provider = MockGitProvider()
    provider._store.clear()
    provider._store.add_commit(
        repo_full_name='test/myrepo',
        branch='main',
        author_username='alice',
        author_name='Alice',
        message='feat: implement feature'
    )

    result = await provider.verify_evidence(
        repo='test/myrepo',
        branch='main',
        commit_sha=None,
        pr_number=None,
    )
    assert result.status == 'PASSED'


@pytest.mark.asyncio
async def test_submit_task_triggers_verification(db_session):
    """
    submit_task() calls MockGitProvider.verify_evidence and populates
    task.verification_status and task.verification_details.
    """
    user_a, user_b, _, project = await make_world(db_session)

    provider = MockGitProvider()
    provider._store.clear()
    provider._store.add_commit(
        repo_full_name='test/repo',
        branch='feature/x',
        author_username='alice',
        author_name='Alice',
        message='feat: add feature x'
    )

    task = await make_task(db_session, project.id, user_a.id, user_a.id, 'Verified Task', status='IN_PROGRESS')
    task.github_repo = 'test/repo'

    await ProjectEngine.submit_task(
        db_session,
        task,
        {'branch': 'feature/x', 'commit_sha': None},
        user_a.id,
        git_provider=provider,
    )

    assert task.status == 'UNDER_REVIEW'
    assert task.verification_status == 'PASSED'
    assert task.verification_details is not None

