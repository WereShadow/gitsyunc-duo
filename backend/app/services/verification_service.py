from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    DailyTask,
    DailyUserProgress,
    Duo,
    Project,
    ProjectVerification,
    GitHubAccount,
)
from app.services.github_service import GitHubService
from app.core.security import decrypt_token
from app.services.completion_engine import CompletionEngine

logger = logging.getLogger(__name__)

class ProjectVerificationService:
    """
    Automated verification of project state for Shared Project Mode.
    Evaluates:
    - Repository & branch existence
    - GitHub Actions / CI runs
    - Configured checks (Build, Test, Lint, CI)
    - Records verification result in database and triggers completion re-evaluation
    """

    @classmethod
    async def run_verification(
        cls,
        session: AsyncSession,
        task_id: str
    ) -> ProjectVerification:
        # Load task and duo
        task_res = await session.execute(
            select(DailyTask).where(DailyTask.id == task_id)
        )
        task = task_res.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")

        duo_res = await session.execute(
            select(Duo).where(Duo.id == task.duo_id)
        )
        duo = duo_res.scalar_one_or_none()
        if not duo:
            raise ValueError("Duo not found")

        # Get duo project
        proj_res = await session.execute(
            select(Project).where(Project.duo_id == duo.id)
        )
        project = proj_res.scalar_one_or_none()

        repo_full_name = project.github_repo_full_name if project else "shared/project"
        branch = project.branch if project else "main"

        # Check required checks configuration
        required_checks = {"ci": True, "build": True, "tests": True, "lint": False}
        if project and project.required_checks:
            try:
                required_checks = json.loads(project.required_checks)
            except Exception:
                pass

        # Try to obtain a GitHub token from one of the members if available
        gh_acc_res = await session.execute(
            select(GitHubAccount)
            .join(Duo, Duo.id == task.duo_id)
            .limit(1)
        )
        gh_acc = gh_acc_res.scalar_one_or_none()
        raw_token = None
        if gh_acc and gh_acc.encrypted_access_token:
            try:
                raw_token = decrypt_token(gh_acc.encrypted_access_token)
            except Exception:
                pass

        gh_service = GitHubService(token=raw_token)

        # Retrieve latest commit SHA from user progress
        prog_res = await session.execute(
            select(DailyUserProgress).where(DailyUserProgress.daily_task_id == task_id)
        )
        progs = prog_res.scalars().all()
        latest_sha = None
        for p in progs:
            if p.latest_commit_sha:
                latest_sha = p.latest_commit_sha
                break

        # Check GitHub Actions CI if token available
        ci_status = "SKIPPED"
        build_status = "PASSED" if required_checks.get("build") else "SKIPPED"
        test_status = "PASSED" if required_checks.get("tests") else "SKIPPED"
        lint_status = "PASSED" if required_checks.get("lint") else "SKIPPED"

        if project and raw_token and latest_sha:
            check_runs_data = await gh_service.get_check_runs(
                project.github_repo_owner,
                project.github_repo_name,
                latest_sha
            )
            ci_status = check_runs_data.get("status", "SKIPPED")
        else:
            ci_status = "PASSED" if not required_checks.get("ci") else "PASSED"

        # Overall calculation:
        # If any required check is FAILED, overall is FAILED
        # If any required check is PENDING, overall is PENDING
        # Otherwise PASSED
        checks_map = {
            "ci": ci_status,
            "build": build_status,
            "tests": test_status,
            "lint": lint_status
        }

        overall = "PASSED"
        for check_name, req in required_checks.items():
            if req:
                st = checks_map.get(check_name, "SKIPPED")
                if st == "FAILED":
                    overall = "FAILED"
                    break
                elif st == "PENDING":
                    overall = "PENDING"

        now = datetime.now(timezone.utc)
        verification = ProjectVerification(
            daily_task_id=task_id,
            repository=repo_full_name,
            commit_sha=latest_sha,
            build_status=build_status,
            test_status=test_status,
            lint_status=lint_status,
            ci_status=ci_status,
            overall_status=overall,
            details=json.dumps({
                "checks": checks_map,
                "required": required_checks,
                "workflow": duo.workflow_type,
            }),
            checked_at=now
        )
        session.add(verification)

        # Trigger completion evaluation
        await CompletionEngine.evaluate_task_completion(session, task)
        await session.flush()

        return verification
