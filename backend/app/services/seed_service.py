from datetime import datetime, timezone, timedelta
import json
import logging
from sqlalchemy import select

from app.models.database import AsyncSessionLocal
from app.models.entities import (
    User,
    GitHubAccount,
    Duo,
    DuoMember,
    Project,
    DailyTask,
    DailyUserProgress,
    TaskReview,
    ProjectVerification,
    Streak,
    Notification,
    ProjectMilestone,
    ProjectTask,
    TaskDependency,
    TaskActivityLog,
)
from app.core.security import get_password_hash, encrypt_token
from app.services.completion_engine import CompletionEngine
from app.services.simulation_store import sim_store

logger = logging.getLogger(__name__)

async def seed_demo_data():
    """Seed initial demo data if database is empty."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        if res.scalar_one_or_none():
            return  # Already seeded

        logger.info("Seeding realistic demo data for GitSync Duo...")
        now = datetime.now(timezone.utc)

        # 1. Users
        user_a = User(
            email="alex@gitsync.dev",
            full_name="Alex Rivera",
            hashed_password=get_password_hash("password123"),
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=20)
        )
        user_b = User(
            email="morgan@gitsync.dev",
            full_name="Morgan Chen",
            hashed_password=get_password_hash("password123"),
            avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=20)
        )
        db.add_all([user_a, user_b])
        await db.flush()

        # 2. GitHub Accounts
        gh_a = GitHubAccount(
            user_id=user_a.id,
            github_username="alexrivera-dev",
            encrypted_access_token=encrypt_token("ghp_demo_alex_token"),
            token_scope="repo,user",
            connected_at=now - timedelta(days=20)
        )
        gh_b = GitHubAccount(
            user_id=user_b.id,
            github_username="morganchen-code",
            encrypted_access_token=encrypt_token("ghp_demo_morgan_token"),
            token_scope="repo,user",
            connected_at=now - timedelta(days=20)
        )
        db.add_all([gh_a, gh_b])

        # 3. Duo
        duo = Duo(
            name="Campus AI Squad",
            invite_code="SYNC-7721",
            created_by=user_a.id,
            timezone="Asia/Kolkata",
            deadline_time="23:59",
            grace_period_minutes=30,
            project_mode="SHARED",
            workflow_type="SEPARATE_BRANCHES",
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=20)
        )
        db.add(duo)
        await db.flush()

        # 4. Duo Members
        dm_a = DuoMember(
            duo_id=duo.id,
            user_id=user_a.id,
            role="CREATOR",
            joined_at=now - timedelta(days=20)
        )
        dm_b = DuoMember(
            duo_id=duo.id,
            user_id=user_b.id,
            role="PARTNER",
            joined_at=now - timedelta(days=20)
        )
        db.add_all([dm_a, dm_b])

        # 5. Shared Project
        shared_repo_owner = "campus-ai"
        shared_repo_name = "assistant"
        shared_repo_full = "campus-ai/assistant"

        proj = Project(
            duo_id=duo.id,
            user_id=None,  # Shared project
            project_name="Campus AI Assistant",
            description="Intelligent student course planning and campus assistant monorepo",
            github_repo_owner=shared_repo_owner,
            github_repo_name=shared_repo_name,
            github_repo_full_name=shared_repo_full,
            branch="main",
            assigned_area="Fullstack Monorepo",
            verification_enabled=True,
            required_checks=json.dumps({"ci": True, "build": True, "tests": True, "lint": False}),
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=20)
        )
        db.add(proj)

        # 6. Streak
        streak = Streak(
            duo_id=duo.id,
            current_streak=14,
            longest_streak=14,
            completed_days=14,
            missed_days=1,
            last_completed_date=None,
            updated_at=now
        )
        db.add(streak)

        # 7. Seed past 14 days of history for calendar & stats
        today_str = CompletionEngine.get_today_local_date_str(duo.timezone)
        today_date = datetime.strptime(today_str, "%Y-%m-%d").date()

        for day_offset in range(14, 0, -1):
            past_date = today_date - timedelta(days=day_offset)
            past_date_str = past_date.strftime("%Y-%m-%d")
            _, _, past_deadline_utc = CompletionEngine.get_day_boundaries(duo.timezone, past_date_str, duo.deadline_time)

            past_task = DailyTask(
                duo_id=duo.id,
                date=past_date_str,
                title=f"Day {15 - day_offset}: Feature Sprint Integration",
                description="Coordinate services and ship incremental tested code.",
                user_a_task="Backend service integration",
                user_b_task="Frontend state and component wiring",
                github_requirement="1 commit",
                min_commits_required=1,
                deadline_utc=past_deadline_utc,
                status="COMPLETED",
                created_at=now - timedelta(days=day_offset),
                updated_at=now - timedelta(days=day_offset)
            )
            db.add(past_task)
            await db.flush()

            # Progress for both
            p_a = DailyUserProgress(
                daily_task_id=past_task.id,
                user_id=user_a.id,
                github_verified=True,
                commit_count=2,
                latest_commit_sha=f"c7a{day_offset:02d}b",
                latest_commit_message=f"feat(backend): ship daily updates for {past_date_str}",
                latest_commit_url=f"https://github.com/{shared_repo_full}/commit/c7a{day_offset:02d}b",
                submission_status="APPROVED",
                review_status="APPROVED",
                submitted_at=now - timedelta(days=day_offset, hours=4),
                approved_at=now - timedelta(days=day_offset, hours=2),
                verified_at=now - timedelta(days=day_offset, hours=4)
            )
            p_b = DailyUserProgress(
                daily_task_id=past_task.id,
                user_id=user_b.id,
                github_verified=True,
                commit_count=3,
                latest_commit_sha=f"f8b{day_offset:02d}e",
                latest_commit_message=f"feat(ui): connect api endpoints for {past_date_str}",
                latest_commit_url=f"https://github.com/{shared_repo_full}/commit/f8b{day_offset:02d}e",
                submission_status="APPROVED",
                review_status="APPROVED",
                submitted_at=now - timedelta(days=day_offset, hours=3),
                approved_at=now - timedelta(days=day_offset, hours=1),
                verified_at=now - timedelta(days=day_offset, hours=3)
            )
            db.add_all([p_a, p_b])

        # 8. Today's active task
        _, _, today_deadline_utc = CompletionEngine.get_day_boundaries(duo.timezone, today_str, duo.deadline_time)
        today_task = DailyTask(
            duo_id=duo.id,
            date=today_str,
            title="Authentication & Peer Review Flow",
            description="Implement secure JWT auth on the backend and paired interactive review UI.",
            user_a_task="Implement FastAPI JWT authentication, security middlewares, and tokens",
            user_b_task="Build modern dark authentication UI, review modals, and change-request drawer",
            github_requirement="1 commit",
            min_commits_required=1,
            deadline_utc=today_deadline_utc,
            status="WAITING_FOR_USER_B",  # Alex has pushed, Morgan is in progress!
            created_at=now,
            updated_at=now
        )
        db.add(today_task)
        await db.flush()

        # Alex has pushed & submitted work
        prog_today_a = DailyUserProgress(
            daily_task_id=today_task.id,
            user_id=user_a.id,
            github_verified=True,
            commit_count=3,
            latest_commit_sha="a91b4e2",
            latest_commit_message="feat(auth): implement JWT token generation & Fernet encryption",
            latest_commit_url=f"https://github.com/{shared_repo_full}/commit/a91b4e2",
            latest_commit_time=now - timedelta(minutes=45),
            changed_files=json.dumps(["backend/core/security.py", "backend/routes/auth.py", "backend/tests/test_auth.py"]),
            submission_status="SUBMITTED",
            review_status="UNDER_REVIEW",
            submitted_at=now - timedelta(minutes=40),
            verified_at=now - timedelta(minutes=45)
        )

        # Morgan has not pushed yet (waiting...)
        prog_today_b = DailyUserProgress(
            daily_task_id=today_task.id,
            user_id=user_b.id,
            github_verified=False,
            commit_count=0,
            submission_status="PENDING",
            review_status="PENDING"
        )
        db.add_all([prog_today_a, prog_today_b])

        # Project verification for today
        pv_today = ProjectVerification(
            daily_task_id=today_task.id,
            repository=shared_repo_full,
            commit_sha="a91b4e2",
            build_status="PASSED",
            test_status="PASSED",
            lint_status="PASSED",
            ci_status="PASSED",
            overall_status="PASSED",
            details=json.dumps({
                "checks": {"ci": "PASSED", "build": "PASSED", "tests": "PASSED", "lint": "PASSED"},
                "required": {"ci": True, "build": True, "tests": True, "lint": False}
            }),
            checked_at=now - timedelta(minutes=30)
        )
        db.add(pv_today)

        # Notifications
        n1 = Notification(
            user_id=user_b.id,
            duo_id=duo.id,
            type="PARTNER_COMPLETED",
            title="Alex pushed today's work",
            message="Your partner Alex completed their requirement and submitted their backend task for review.",
            is_read=False,
            created_at=now - timedelta(minutes=40)
        )
        n2 = Notification(
            user_id=user_a.id,
            duo_id=duo.id,
            type="REMINDER",
            title="Requirement Satisfied",
            message="Your GitHub requirement is verified. Waiting for Morgan to complete their work.",
            is_read=True,
            created_at=now - timedelta(minutes=45)
        )
        db.add_all([n1, n2])

        # Seed simulation store with Alex's commit
        sim_store.add_commit(
            repo_full_name=shared_repo_full,
            branch="backend",
            author_username="alexrivera-dev",
            author_name="Alex Rivera",
            message="feat(auth): implement JWT token generation & Fernet encryption",
            sha="a91b4e2",
            files=["backend/core/security.py", "backend/routes/auth.py", "backend/tests/test_auth.py"],
            timestamp=now - timedelta(minutes=45)
        )

        # --- Seed Project Milestones and Tasks ---
        m1 = ProjectMilestone(
            project_id=shared_proj.id,
            title="Milestone 1: MVP Core Architecture",
            description="Base database models, asynchronous API endpoints, and authentication workflow.",
            target_date=(now + timedelta(days=7)).strftime("%Y-%m-%d"),
            status="OPEN"
        )
        m2 = ProjectMilestone(
            project_id=shared_proj.id,
            title="Milestone 2: Collaborative Review & GitHub Integration",
            description="Branch verification, pull request audit log, and peer review execution.",
            target_date=(now + timedelta(days=14)).strftime("%Y-%m-%d"),
            status="OPEN"
        )
        db.add_all([m1, m2])
        await db.flush()

        # Task 1: Database Setup (Completed by Alex)
        pt1 = ProjectTask(
            project_id=shared_proj.id,
            milestone_id=m1.id,
            creator_id=user_a.id,
            assignee_id=user_a.id,
            title="Database Schema & Async Engine",
            description="Configure SQLAlchemy async engine, aiosqlite, and base entity models.",
            priority="HIGH",
            deadline=now - timedelta(days=1),
            status="COMPLETED",
            github_repo=shared_repo_full,
            branch="main",
            latest_commit_sha="c576f63",
            latest_commit_message="feat: database setup & models",
            verification_status="PASSED",
            completed_at=now - timedelta(days=1)
        )
        # Task 2: Auth API & Security (Submitted by Alex, awaiting Morgan's review)
        pt2 = ProjectTask(
            project_id=shared_proj.id,
            milestone_id=m1.id,
            creator_id=user_a.id,
            assignee_id=user_a.id,
            title="FastAPI Authentication & JWT Tokens",
            description="Implement JWT tokens, password hashing, and OAuth dependency injection.",
            priority="URGENT",
            deadline=now + timedelta(days=1),
            status="UNDER_REVIEW",
            github_repo=shared_repo_full,
            branch="backend",
            latest_commit_sha="a91b4e2",
            latest_commit_message="feat(auth): implement JWT token generation & Fernet encryption",
            verification_status="PASSED",
            submitted_at=now - timedelta(minutes=40)
        )
        # Task 3: Frontend Login & Review UI (Assigned to Morgan, in progress)
        pt3 = ProjectTask(
            project_id=shared_proj.id,
            milestone_id=m1.id,
            creator_id=user_a.id,
            assignee_id=user_b.id,
            title="Frontend Authentication & Review Modals",
            description="Build login page, token storage in auth context, and peer review submit modal.",
            priority="HIGH",
            deadline=now + timedelta(days=2),
            status="IN_PROGRESS",
            github_repo=shared_repo_full,
            branch="frontend",
            verification_status="PENDING"
        )
        # Task 4: Collaborative Dashboard (Assigned to Morgan, BLOCKED by Auth API)
        pt4 = ProjectTask(
            project_id=shared_proj.id,
            milestone_id=m2.id,
            creator_id=user_a.id,
            assignee_id=user_b.id,
            title="Project Execution Dashboard",
            description="Render overall completion metrics, task pipeline, blocked dependency indicators, and team activity.",
            priority="HIGH",
            deadline=now + timedelta(days=5),
            status="TODO",
            github_repo=shared_repo_full,
            branch="frontend/dashboard",
            verification_status="PENDING"
        )
        # Task 5: Automated GitHub Actions & CI Pipeline (Backlog)
        pt5 = ProjectTask(
            project_id=shared_proj.id,
            milestone_id=m2.id,
            creator_id=user_b.id,
            assignee_id=None,
            title="Continuous Integration & Test Workflow",
            description="Setup GitHub Actions workflow to run pytest and frontend type-checking on PRs.",
            priority="MEDIUM",
            deadline=now + timedelta(days=7),
            status="BACKLOG",
            github_repo=shared_repo_full,
            branch="infra/ci",
            verification_status="PENDING"
        )
        db.add_all([pt1, pt2, pt3, pt4, pt5])
        await db.flush()

        # Dependencies:
        # Task 2 depends on Task 1 (Satisfied, since Task 1 is COMPLETED)
        # Task 3 depends on Task 2 (Task 2 is UNDER_REVIEW, so Task 3 has upstream dependency)
        # Task 4 depends on Task 2 and Task 3
        d1 = TaskDependency(task_id=pt2.id, depends_on_task_id=pt1.id)
        d2 = TaskDependency(task_id=pt3.id, depends_on_task_id=pt2.id)
        d3 = TaskDependency(task_id=pt4.id, depends_on_task_id=pt2.id)
        d4 = TaskDependency(task_id=pt4.id, depends_on_task_id=pt3.id)
        db.add_all([d1, d2, d3, d4])

        # Activity Logs
        act1 = TaskActivityLog(
            project_id=shared_proj.id,
            task_id=pt1.id,
            user_id=user_a.id,
            action="TASK_COMPLETED",
            details="Approved and completed: Database Schema & Async Engine",
            created_at=now - timedelta(days=1)
        )
        act2 = TaskActivityLog(
            project_id=shared_proj.id,
            task_id=pt2.id,
            user_id=user_a.id,
            action="TASK_SUBMITTED",
            details="Submitted for peer review with commit a91b4e2",
            created_at=now - timedelta(minutes=40)
        )
        db.add_all([act1, act2])

        await db.commit()
        logger.info("Demo data seeded successfully with Duo, Project Milestones, Tasks, and Dependencies!")
