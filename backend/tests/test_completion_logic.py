import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.entities import (
    User,
    Duo,
    DuoMember,
    Project,
    DailyTask,
    DailyUserProgress,
    TaskReview,
    ProjectVerification,
    Streak,
)
from app.core.security import get_password_hash
from app.services.completion_engine import CompletionEngine
from app.services.review_service import ReviewService
from app.services.github_service import GitHubService
from app.services.simulation_store import sim_store

@pytest.mark.asyncio
async def test_completion_separate_projects(db_session: AsyncSession):
    """
    Test Edge Cases 1-4:
    - User A commits, User B doesn't -> WAITING_FOR_USER_B
    - User B commits, User A doesn't -> WAITING_FOR_USER_A
    - User A makes multiple commits, User B doesn't -> WAITING_FOR_USER_B
    - Both commit -> COMPLETED and streak increments to 1
    """
    now = datetime.now(timezone.utc)
    user_a = User(email="user_a@test.com", full_name="User A", hashed_password=get_password_hash("pass"))
    user_b = User(email="user_b@test.com", full_name="User B", hashed_password=get_password_hash("pass"))
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    duo = Duo(
        name="Test Separate Duo",
        invite_code="TEST-1001",
        created_by=user_a.id,
        timezone="Asia/Kolkata",
        project_mode="SEPARATE"
    )
    db_session.add(duo)
    await db_session.flush()

    mem_a = DuoMember(duo_id=duo.id, user_id=user_a.id, role="CREATOR")
    mem_b = DuoMember(duo_id=duo.id, user_id=user_b.id, role="PARTNER")
    streak = Streak(duo_id=duo.id, current_streak=0, longest_streak=0, completed_days=0, missed_days=0)
    db_session.add_all([mem_a, mem_b, streak])

    # Create daily task
    task = DailyTask(
        duo_id=duo.id,
        date="2026-09-16",
        title="Test Task 1",
        deadline_utc=now + timedelta(hours=5),
        status="ACTIVE"
    )
    db_session.add(task)
    await db_session.flush()

    prog_a = DailyUserProgress(daily_task_id=task.id, user_id=user_a.id, github_verified=False, commit_count=0)
    prog_b = DailyUserProgress(daily_task_id=task.id, user_id=user_b.id, github_verified=False, commit_count=0)
    db_session.add_all([prog_a, prog_b])
    await db_session.flush()

    # Initial evaluation: neither committed -> ACTIVE
    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "ACTIVE"
    assert res["completed"] is False

    # Case 1: User A commits, User B has not
    prog_a.github_verified = True
    prog_a.commit_count = 1
    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "WAITING_FOR_USER_B"
    assert res["completed"] is False

    # Case 4: User A makes multiple commits, User B still has not
    prog_a.commit_count = 5
    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "WAITING_FOR_USER_B"
    assert res["completed"] is False

    # Case 3: Both commit -> Day COMPLETED
    prog_b.github_verified = True
    prog_b.commit_count = 1
    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "COMPLETED"
    assert res["completed"] is True
    assert streak.current_streak == 1
    assert streak.completed_days == 1

@pytest.mark.asyncio
async def test_shared_project_mode_and_peer_reviews(db_session: AsyncSession):
    """
    Test Shared Project Mode:
    - User A and User B both upload work
    - Reviewer CANNOT approve own task (security violation)
    - Reviewer requests changes with comment -> CHANGES_REQUESTED
    - New commit submitted -> UNDER_REVIEW
    - Both approved + project checks pass -> COMPLETED
    """
    now = datetime.now(timezone.utc)
    user_a = User(email="shared_a@test.com", full_name="Shared A", hashed_password=get_password_hash("pass"))
    user_b = User(email="shared_b@test.com", full_name="Shared B", hashed_password=get_password_hash("pass"))
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    duo = Duo(
        name="Shared Project Duo",
        invite_code="TEST-2002",
        created_by=user_a.id,
        timezone="Asia/Kolkata",
        project_mode="SHARED",
        workflow_type="SEPARATE_BRANCHES"
    )
    db_session.add(duo)
    await db_session.flush()

    mem_a = DuoMember(duo_id=duo.id, user_id=user_a.id, role="CREATOR")
    mem_b = DuoMember(duo_id=duo.id, user_id=user_b.id, role="PARTNER")
    streak = Streak(duo_id=duo.id, current_streak=0, longest_streak=0, completed_days=0, missed_days=0)
    db_session.add_all([mem_a, mem_b, streak])

    project = Project(
        duo_id=duo.id,
        project_name="Shared App",
        github_repo_owner="team",
        github_repo_name="shared-app",
        github_repo_full_name="team/shared-app",
        branch="main",
        verification_enabled=True,
        required_checks='{"ci": true, "build": true, "tests": true, "lint": false}'
    )
    db_session.add(project)

    task = DailyTask(
        duo_id=duo.id,
        date="2026-09-16",
        title="Shared Daily Goal",
        deadline_utc=now + timedelta(hours=5),
        status="ACTIVE"
    )
    db_session.add(task)
    await db_session.flush()

    prog_a = DailyUserProgress(
        daily_task_id=task.id,
        user_id=user_a.id,
        github_verified=True,
        commit_count=1,
        latest_commit_sha="a1b2c3d",
        submission_status="SUBMITTED",
        review_status="UNDER_REVIEW"
    )
    prog_b = DailyUserProgress(
        daily_task_id=task.id,
        user_id=user_b.id,
        github_verified=True,
        commit_count=1,
        latest_commit_sha="e4f5a6b",
        submission_status="SUBMITTED",
        review_status="UNDER_REVIEW"
    )
    db_session.add_all([prog_a, prog_b])
    await db_session.flush()

    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "WAITING_FOR_REVIEW"
    assert res["completed"] is False

    # SECURITY: User A attempts to approve own task -> 403 Forbidden!
    with pytest.raises(HTTPException) as exc_info:
        await ReviewService.create_review(
            session=db_session,
            task_id=task.id,
            task_owner_id=user_a.id,
            reviewer_id=user_a.id,
            review_status_input="APPROVED",
            comment="I approve myself"
        )
    assert exc_info.value.status_code == 403

    # Partner reviews User A's task and requests changes
    review_1 = await ReviewService.create_review(
        session=db_session,
        task_id=task.id,
        task_owner_id=user_a.id,
        reviewer_id=user_b.id,
        review_status_input="CHANGES_REQUESTED",
        comment="Missing unit tests for edge cases"
    )
    assert review_1.status == "CHANGES_REQUESTED"
    assert prog_a.review_status == "CHANGES_REQUESTED"

    # User A pushes new commit & resubmits
    prog_a.latest_commit_sha = "new999"
    prog_a.submission_status = "SUBMITTED"
    prog_a.review_status = "UNDER_REVIEW"

    # User B reviews again and APPROVES User A
    review_2 = await ReviewService.create_review(
        session=db_session,
        task_id=task.id,
        task_owner_id=user_a.id,
        reviewer_id=user_b.id,
        review_status_input="APPROVED",
        comment="Tests added and verified, looking great!"
    )
    assert review_2.status == "APPROVED"
    assert prog_a.review_status == "APPROVED"

    # User A approves User B
    review_3 = await ReviewService.create_review(
        session=db_session,
        task_id=task.id,
        task_owner_id=user_b.id,
        reviewer_id=user_a.id,
        review_status_input="APPROVED",
        comment="UI works cleanly, approved!"
    )
    assert review_3.status == "APPROVED"
    assert prog_b.review_status == "APPROVED"

    # Both reviews approved, but project verification not yet recorded
    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["completed"] is False

    # Add passed project verification record
    pv = ProjectVerification(
        daily_task_id=task.id,
        repository="team/shared-app",
        commit_sha="new999",
        build_status="PASSED",
        test_status="PASSED",
        lint_status="PASSED",
        ci_status="PASSED",
        overall_status="PASSED"
    )
    db_session.add(pv)
    await db_session.flush()

    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "COMPLETED"
    assert res["completed"] is True
    assert streak.current_streak == 1

@pytest.mark.asyncio
async def test_deadline_expiration_and_streak_reset(db_session: AsyncSession):
    """
    Test Edge Case: Day expires past deadline + grace period without completion.
    Status becomes MISSED and streak resets to 0.
    """
    now = datetime.now(timezone.utc)
    user_a = User(email="exp_a@test.com", full_name="Exp A", hashed_password="pwd")
    user_b = User(email="exp_b@test.com", full_name="Exp B", hashed_password="pwd")
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    duo = Duo(
        name="Exp Duo",
        invite_code="TEST-3003",
        created_by=user_a.id,
        timezone="Asia/Kolkata",
        grace_period_minutes=15,
        project_mode="SEPARATE"
    )
    db_session.add(duo)
    await db_session.flush()

    mem_a = DuoMember(duo_id=duo.id, user_id=user_a.id, role="CREATOR")
    mem_b = DuoMember(duo_id=duo.id, user_id=user_b.id, role="PARTNER")
    streak = Streak(duo_id=duo.id, current_streak=5, longest_streak=10, completed_days=5, missed_days=0)
    db_session.add_all([mem_a, mem_b, streak])

    # Task whose deadline was 1 hour ago
    task = DailyTask(
        duo_id=duo.id,
        date="2026-09-15",
        title="Yesterday Task",
        deadline_utc=now - timedelta(hours=1),
        status="ACTIVE"
    )
    db_session.add(task)
    await db_session.flush()

    prog_a = DailyUserProgress(daily_task_id=task.id, user_id=user_a.id, github_verified=True, commit_count=2)
    prog_b = DailyUserProgress(daily_task_id=task.id, user_id=user_b.id, github_verified=False, commit_count=0)
    db_session.add_all([prog_a, prog_b])
    await db_session.flush()

    res = await CompletionEngine.evaluate_task_completion(db_session, task)
    assert res["status"] == "MISSED"
    assert res["completed"] is False
    assert streak.current_streak == 0
    assert streak.missed_days == 1

@pytest.mark.asyncio
async def test_wrong_repository_or_branch_ignored():
    """
    Test Edge Cases 5 & 6:
    Commit to wrong repository or wrong branch does not verify.
    """
    sim_store.clear()
    now = datetime.now(timezone.utc)
    
    # Commit made to another repo
    sim_store.add_commit(
        repo_full_name="other-owner/unrelated-repo",
        branch="main",
        author_username="testuser",
        author_name="Test User",
        message="Unrelated work",
        timestamp=now
    )

    gh_service = GitHubService(token=None)
    result = await gh_service.verify_commits(
        repo_owner="team",
        repo_name="configured-repo",
        branch="main",
        github_username="testuser",
        since_utc=now - timedelta(hours=1),
        until_utc=now + timedelta(hours=1),
        min_commits=1
    )
    assert result["verified"] is False
    assert result["commit_count"] == 0

    # Commit made to wrong branch
    sim_store.add_commit(
        repo_full_name="team/configured-repo",
        branch="experiment",  # Configured is 'main'
        author_username="testuser",
        author_name="Test User",
        message="Experimental branch work",
        timestamp=now
    )
    result_branch = await gh_service.verify_commits(
        repo_owner="team",
        repo_name="configured-repo",
        branch="main",
        github_username="testuser",
        since_utc=now - timedelta(hours=1),
        until_utc=now + timedelta(hours=1),
        min_commits=1
    )
    assert result_branch["verified"] is False
    assert result_branch["commit_count"] == 0

@pytest.mark.asyncio
async def test_outside_user_cannot_review(db_session: AsyncSession):
    """Test Edge Case: User from outside the duo attempts to review task -> Rejected with 403."""
    u1 = User(email="in1@test.com", full_name="In 1", hashed_password="pwd")
    u2 = User(email="in2@test.com", full_name="In 2", hashed_password="pwd")
    u_outsider = User(email="out@test.com", full_name="Outsider", hashed_password="pwd")
    db_session.add_all([u1, u2, u_outsider])
    await db_session.flush()

    duo = Duo(name="Duo A", invite_code="CODE-A1", created_by=u1.id)
    db_session.add(duo)
    await db_session.flush()

    m1 = DuoMember(duo_id=duo.id, user_id=u1.id, role="CREATOR")
    m2 = DuoMember(duo_id=duo.id, user_id=u2.id, role="PARTNER")
    db_session.add_all([m1, m2])

    task = DailyTask(duo_id=duo.id, date="2026-09-16", title="Task", deadline_utc=datetime.now(timezone.utc))
    db_session.add(task)
    await db_session.flush()

    prog1 = DailyUserProgress(daily_task_id=task.id, user_id=u1.id, github_verified=True)
    db_session.add(prog1)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await ReviewService.create_review(
            session=db_session,
            task_id=task.id,
            task_owner_id=u1.id,
            reviewer_id=u_outsider.id,  # Outsider!
            review_status_input="APPROVED",
            comment="I am not in your duo"
        )
    assert exc.value.status_code == 403
