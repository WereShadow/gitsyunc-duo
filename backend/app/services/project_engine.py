import json
import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Protocol
from sqlalchemy import select, and_
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


# ---------------------------------------------------------------------------
# GitProvider abstraction (Spec §9-10)
# ---------------------------------------------------------------------------

class VerificationResult:
    """Structured result of a task evidence verification pass."""
    def __init__(
        self,
        status: str,              # PASSED, FAILED, SKIPPED
        ci_passed: Optional[bool] = None,
        build_passed: Optional[bool] = None,
        test_passed: Optional[bool] = None,
        details: Optional[Dict[str, Any]] = None,
        message: str = "",
    ):
        self.status = status
        self.ci_passed = ci_passed
        self.build_passed = build_passed
        self.test_passed = test_passed
        self.details = details or {}
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        def safe_val(v: Any) -> Any:
            if isinstance(v, datetime):
                return v.isoformat()
            if isinstance(v, dict):
                return {k: safe_val(vv) for k, vv in v.items()}
            if isinstance(v, list):
                return [safe_val(i) for i in v]
            return v

        return {
            "status": self.status,
            "ci_passed": self.ci_passed,
            "build_passed": self.build_passed,
            "test_passed": self.test_passed,
            "details": safe_val(self.details),
            "message": self.message,
        }


class MockGitProvider:
    """
    Uses SimulationStore to verify evidence — shares the same interface as GitHubProvider.
    This is the default provider in development and tests.
    DO NOT REMOVE: the simulator must use the same verification engine as real GitHub.
    """

    def __init__(self):
        from app.services.simulation_store import sim_store
        self._store = sim_store

    async def verify_evidence(
        self,
        repo: str,
        branch: Optional[str],
        commit_sha: Optional[str],
        pr_number: Optional[int],
    ) -> VerificationResult:
        if not repo:
            return VerificationResult(status="SKIPPED", message="No repository specified")

        commits = self._store.get_commits(repo_full_name=repo, branch=branch)
        if commit_sha:
            commits = [
                c for c in commits
                if c.get("sha") == commit_sha or c.get("full_sha") == commit_sha
            ]
        if not commits:
            commits = self._store.get_commits(repo_full_name=repo)

        if not commits:
            return VerificationResult(
                status="FAILED",
                message=(
                    f"No commits found in simulator for repo '{repo}'"
                    + (f", branch '{branch}'" if branch else "")
                ),
            )

        latest = commits[0]
        sha_key = latest.get("full_sha") or latest.get("sha", "")
        check_run = self._store._check_runs.get(sha_key, {})

        ci_passed = bool(check_run.get("ci", True))
        build_passed = bool(check_run.get("build", True))
        test_passed = bool(check_run.get("tests", True))
        overall = "PASSED" if all([ci_passed, build_passed, test_passed]) else "FAILED"

        return VerificationResult(
            status=overall,
            ci_passed=ci_passed,
            build_passed=build_passed,
            test_passed=test_passed,
            details={"latest_commit": latest, "check_run": check_run},
            message=f"Verified {len(commits)} commit(s) in simulator",
        )

    async def get_commit_info(self, repo: str, sha: str) -> Optional[Dict[str, Any]]:
        for c in self._store.get_commits(repo_full_name=repo):
            if c.get("sha") == sha or c.get("full_sha") == sha:
                return c
        return None

    async def get_branch_info(self, repo: str, branch: str) -> Optional[Dict[str, Any]]:
        commits = self._store.get_commits(repo_full_name=repo, branch=branch)
        if commits:
            return {"branch": branch, "latest_commit": commits[0], "commit_count": len(commits)}
        return None


class GitHubProvider:
    """
    Calls the real GitHub API for evidence verification.
    Only usable when the user has a linked GitHub access token.
    """

    def __init__(self, access_token: str):
        self._token = access_token

    async def verify_evidence(
        self,
        repo: str,
        branch: Optional[str],
        commit_sha: Optional[str],
        pr_number: Optional[int],
    ) -> VerificationResult:
        # Full implementation would call GitHub REST API:
        # GET /repos/{repo}/commits and GET /repos/{repo}/check-runs/{sha}
        return VerificationResult(
            status="SKIPPED",
            message="Real GitHub verification requires an authenticated GitHub token.",
        )

    async def get_commit_info(self, repo: str, sha: str) -> Optional[Dict[str, Any]]:
        return None

    async def get_branch_info(self, repo: str, branch: str) -> Optional[Dict[str, Any]]:
        return None


def get_default_git_provider() -> MockGitProvider:
    """Returns MockGitProvider for development. Swap to GitHubProvider when token is present."""
    return MockGitProvider()


# ---------------------------------------------------------------------------
# ProjectEngine
# ---------------------------------------------------------------------------

class ProjectEngine:

    # -----------------------------------------------------------------------
    # Immutable audit log (Spec §13)
    # -----------------------------------------------------------------------

    @staticmethod
    async def log_activity(
        session: AsyncSession,
        project_id: str,
        action: str,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[str] = None,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskActivityLog:
        activity = TaskActivityLog(
            project_id=project_id,
            task_id=task_id,
            user_id=user_id,
            action=action,
            details=details,
            previous_state=previous_state,
            new_state=new_state,
            event_metadata=json.dumps(metadata) if metadata else None,
            created_at=utc_now(),
        )
        session.add(activity)
        return activity

    # -----------------------------------------------------------------------
    # Task loading with all relations
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Transitive dependency blocking (Spec §6)
    # BFS: A→B→C is blocked if A is incomplete, even though B is the direct parent.
    # -----------------------------------------------------------------------

    @classmethod
    async def is_task_blocked(
        cls, session: AsyncSession, task_id: str
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Returns (is_blocked, blockers_list).
        Blockers include all transitive ancestors that are not COMPLETED.
        """
        visited: set = set()
        queue: deque = deque([(task_id, 0)])  # (task_id, depth)
        blocked_by: List[Dict[str, Any]] = []
        is_blocked = False

        while queue:
            current_id, depth = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)

            stmt = (
                select(TaskDependency)
                .options(selectinload(TaskDependency.depends_on_task))
                .where(TaskDependency.task_id == current_id)
            )
            res = await session.execute(stmt)
            dependencies = res.scalars().all()

            for dep in dependencies:
                dep_task = dep.depends_on_task
                if not dep_task or dep_task.id in visited:
                    continue

                is_blocking = dep_task.status != "COMPLETED"
                if is_blocking:
                    is_blocked = True
                    blocked_by.append({
                        "task_id": task_id,
                        "depends_on_task_id": dep_task.id,
                        "depends_on_title": dep_task.title,
                        "depends_on_status": dep_task.status,
                        "is_blocking": True,
                        "depth": depth + 1,
                    })

                # Continue BFS through all ancestors (transitive search)
                queue.append((dep_task.id, depth + 1))

        return is_blocked, blocked_by

    # -----------------------------------------------------------------------
    # Cycle detection (Spec §7)
    # -----------------------------------------------------------------------

    @classmethod
    async def would_create_cycle(
        cls, session: AsyncSession, task_id: str, new_dep_id: str
    ) -> bool:
        """
        Returns True if adding task_id → new_dep_id would create a cycle.
        BFS from new_dep_id following existing dependency edges; cycle exists
        if task_id becomes reachable.
        """
        visited: set = set()
        queue: deque = deque([new_dep_id])

        while queue:
            current = queue.popleft()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            stmt = select(TaskDependency.depends_on_task_id).where(
                TaskDependency.task_id == current
            )
            res = await session.execute(stmt)
            for next_id in res.scalars().all():
                if next_id not in visited:
                    queue.append(next_id)

        return False

    # -----------------------------------------------------------------------
    # Project membership
    # -----------------------------------------------------------------------

    @classmethod
    async def can_user_access_project(cls, session: AsyncSession, project_id: str, user_id: str) -> bool:
        proj = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not proj:
            return False
        m = (await session.execute(
            select(DuoMember).where(and_(DuoMember.duo_id == proj.duo_id, DuoMember.user_id == user_id))
        )).scalar_one_or_none()
        return m is not None

    # -----------------------------------------------------------------------
    # Status transition
    # -----------------------------------------------------------------------

    @classmethod
    async def update_task_status(
        cls,
        session: AsyncSession,
        task: ProjectTask,
        new_status: str,
        user_id: str,
    ) -> ProjectTask:
        current_status = task.status
        if current_status == new_status:
            return task

        if new_status in ["IN_PROGRESS", "COMPLETED"]:
            is_blocked, blockers = await cls.is_task_blocked(session, task.id)
            if is_blocked:
                blocking_titles = [b["depends_on_title"] for b in blockers if b["is_blocking"]]
                raise ValueError(
                    f"Cannot transition task to {new_status}: blocked by uncompleted tasks: "
                    + ", ".join(blocking_titles)
                )

        task.status = new_status
        task.updated_at = utc_now()
        if new_status == "COMPLETED":
            task.completed_at = utc_now()

        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=user_id,
            action="STATUS_CHANGED",
            details=f"Changed status from {current_status} to {new_status}",
            previous_state=current_status,
            new_state=new_status,
        )

        if new_status == "COMPLETED" and task.milestone_id:
            await session.flush()  # ensure new status is visible to DB queries
            await cls.check_milestone_completion(session, task.milestone_id, task.project_id, user_id)

        return task


    # -----------------------------------------------------------------------
    # Milestone auto-complete (Spec §15)
    # -----------------------------------------------------------------------

    @classmethod
    async def check_milestone_completion(
        cls, session: AsyncSession, milestone_id: str, project_id: str, user_id: str
    ) -> None:
        milestone = (
            await session.execute(select(ProjectMilestone).where(ProjectMilestone.id == milestone_id))
        ).scalar_one_or_none()
        if not milestone or milestone.status == "COMPLETED":
            return

        tasks = (
            await session.execute(select(ProjectTask).where(ProjectTask.milestone_id == milestone_id))
        ).scalars().all()

        if not tasks:
            return  # no tasks in milestone — don't auto-complete empty milestones

        if all(t.status == "COMPLETED" for t in tasks):
            milestone.status = "COMPLETED"
            milestone.updated_at = utc_now()
            await cls.log_activity(
                session=session,
                project_id=project_id,
                action="MILESTONE_COMPLETED",
                user_id=user_id,
                details=f"Milestone '{milestone.title}' auto-completed: all tasks finished",
                metadata={"milestone_id": milestone_id, "milestone_title": milestone.title},
            )

    # -----------------------------------------------------------------------
    # Submit task evidence + GitProvider verification (Spec §9, §12)
    # -----------------------------------------------------------------------

    @classmethod
    async def submit_task(
        cls,
        session: AsyncSession,
        task: ProjectTask,
        submit_data: Dict[str, Any],
        user_id: str,
        git_provider: Optional[MockGitProvider] = None,
    ) -> ProjectTask:
        is_blocked, blockers = await cls.is_task_blocked(session, task.id)
        if is_blocked:
            blocking_titles = [b["depends_on_title"] for b in blockers if b["is_blocking"]]
            raise ValueError("Cannot submit task: blocked by uncompleted tasks: " + ", ".join(blocking_titles))

        previous_status = task.status

        # Apply evidence fields
        if submit_data.get("branch"):
            task.branch = submit_data["branch"]
        if submit_data.get("pull_request_url"):
            task.pull_request_url = submit_data["pull_request_url"]
        if submit_data.get("pull_request_number"):
            task.pull_request_number = submit_data["pull_request_number"]
        if submit_data.get("commit_sha"):
            task.latest_commit_sha = submit_data["commit_sha"]
        if submit_data.get("commit_message"):
            task.latest_commit_message = submit_data["commit_message"]
        if submit_data.get("changed_files"):
            task.changed_files = json.dumps(submit_data["changed_files"])
        if submit_data.get("submission_notes"):
            task.submission_notes = submit_data["submission_notes"]
        if submit_data.get("github_repo"):
            task.github_repo = submit_data["github_repo"]

        # Increment submission count — invalidates all prior approvals (Spec §12)
        task.submission_count = (task.submission_count or 0) + 1
        task.submitted_at = utc_now()
        task.updated_at = utc_now()

        # GitProvider verification
        provider = git_provider or get_default_git_provider()
        repo = task.github_repo or ""

        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=user_id,
            action="VERIFICATION_STARTED",
            details=f"Starting evidence verification for repo '{repo}'",
            previous_state=previous_status,
            new_state="UNDER_REVIEW",
            metadata={"repo": repo, "branch": task.branch, "commit_sha": task.latest_commit_sha},
        )

        verification_result = await provider.verify_evidence(
            repo=repo,
            branch=task.branch,
            commit_sha=task.latest_commit_sha,
            pr_number=task.pull_request_number,
        )

        task.verification_status = verification_result.status
        task.verification_details = json.dumps(verification_result.to_dict())
        task.status = "UNDER_REVIEW"

        verify_action = (
            "VERIFICATION_PASSED" if verification_result.status == "PASSED"
            else "VERIFICATION_FAILED" if verification_result.status == "FAILED"
            else "VERIFICATION_STARTED"
        )
        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=user_id,
            action=verify_action,
            details=verification_result.message,
            previous_state=previous_status,
            new_state="UNDER_REVIEW",
            metadata=verification_result.to_dict(),
        )

        commit_or_branch = task.latest_commit_sha or task.branch or "work evidence"
        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=user_id,
            action="TASK_SUBMITTED",
            details=f"Submitted for peer review with {commit_or_branch} (submission #{task.submission_count})",
            previous_state=previous_status,
            new_state="UNDER_REVIEW",
            metadata={
                "submission_count": task.submission_count,
                "commit_sha": task.latest_commit_sha,
                "branch": task.branch,
            },
        )
        return task

    # -----------------------------------------------------------------------
    # Peer review with submission integrity (Spec §12)
    # -----------------------------------------------------------------------

    @classmethod
    async def review_task(
        cls,
        session: AsyncSession,
        task: ProjectTask,
        reviewer_id: str,
        review_status: str,
        comment: str,
        commit_sha: Optional[str] = None,
    ) -> Tuple[ProjectTask, TaskReviewLog]:
        if task.assignee_id and task.assignee_id == reviewer_id:
            raise PermissionError("A member cannot approve or review their own assigned work.")

        if task.status not in ["UNDER_REVIEW", "SUBMITTED"]:
            raise ValueError(f"Task is not awaiting review (current status: {task.status})")

        current_submission_index = task.submission_count or 0

        review_log = TaskReviewLog(
            task_id=task.id,
            reviewer_id=reviewer_id,
            status=review_status,
            comment=comment,
            commit_sha=commit_sha or task.latest_commit_sha,
            submission_index=current_submission_index,
            created_at=utc_now(),
        )
        session.add(review_log)

        previous_status = task.status

        if review_status == "APPROVED":
            # Atomically transition APPROVED → COMPLETED (approve = complete, Spec design decision)
            task.status = "COMPLETED"
            task.approved_at = utc_now()
            task.completed_at = utc_now()
            action = "TASK_APPROVED"
            details = f"Approved by teammate with note: {comment}"
        elif review_status == "CHANGES_REQUESTED":
            task.status = "CHANGES_REQUESTED"
            action = "CHANGES_REQUESTED"
            details = f"Changes requested by teammate: {comment}"
        else:
            raise ValueError(f"Invalid review status: {review_status}")

        task.updated_at = utc_now()

        await cls.log_activity(
            session=session,
            project_id=task.project_id,
            task_id=task.id,
            user_id=reviewer_id,
            action=action,
            details=details,
            previous_state=previous_status,
            new_state=task.status,
            metadata={
                "reviewer_id": reviewer_id,
                "commit_sha": review_log.commit_sha,
                "submission_index": current_submission_index,
            },
        )

        if review_status == "APPROVED":
            await cls.log_activity(
                session=session,
                project_id=task.project_id,
                task_id=task.id,
                user_id=reviewer_id,
                action="TASK_COMPLETED",
                details="Task completed after peer approval",
                previous_state="APPROVED",
                new_state="COMPLETED",
            )
            if task.milestone_id:
                await cls.check_milestone_completion(
                    session, task.milestone_id, task.project_id, reviewer_id
                )

        return task, review_log

    # -----------------------------------------------------------------------
    # Project metrics + enhanced health signals (Spec §14)
    # -----------------------------------------------------------------------

    @classmethod
    async def calculate_project_metrics(cls, session: AsyncSession, project_id: str) -> Dict[str, Any]:
        tasks = (
            await session.execute(select(ProjectTask).where(ProjectTask.project_id == project_id))
        ).scalars().all()

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "COMPLETED")
        active = sum(
            1 for t in tasks
            if t.status in ["TODO", "IN_PROGRESS", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUESTED", "APPROVED"]
        )
        awaiting_review = sum(1 for t in tasks if t.status in ["SUBMITTED", "UNDER_REVIEW"])

        now = utc_now()
        overdue = sum(
            1 for t in tasks
            if t.deadline and t.deadline < now and t.status != "COMPLETED"
        )

        # Transitive blocked count
        blocked_count = 0
        for t in tasks:
            if t.status not in ["COMPLETED", "APPROVED"]:
                is_b, _ = await cls.is_task_blocked(session, t.id)
                if is_b:
                    blocked_count += 1

        # Failed CI (Spec §14 health signal)
        failed_ci_count = sum(
            1 for t in tasks
            if t.verification_status == "FAILED" and t.status != "COMPLETED"
        )

        # Review backlog: tasks in UNDER_REVIEW longer than 48h
        review_backlog_threshold = now - timedelta(hours=48)
        review_backlog = sum(
            1 for t in tasks
            if t.status == "UNDER_REVIEW"
            and t.submitted_at
            and t.submitted_at < review_backlog_threshold
        )

        # Milestone risk: non-completed milestones past their target date
        milestones = (
            await session.execute(
                select(ProjectMilestone).where(ProjectMilestone.project_id == project_id)
            )
        ).scalars().all()
        today_str = now.strftime("%Y-%m-%d")
        at_risk_milestones = sum(
            1 for m in milestones
            if m.status != "COMPLETED" and m.target_date and m.target_date < today_str
        )

        completion_pct = round((completed / total * 100), 1) if total > 0 else 0.0

        # Health thresholds (Spec §14)
        if overdue > 2 or (total > 0 and blocked_count > total / 2) or review_backlog > 2:
            health = "DELAYED"
        elif overdue > 0 or blocked_count > 0 or failed_ci_count > 0 or at_risk_milestones > 0:
            health = "AT_RISK"
        else:
            health = "ON_TRACK"

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "active_tasks": active,
            "blocked_tasks": blocked_count,
            "overdue_tasks": overdue,
            "tasks_awaiting_review": awaiting_review,
            "failed_ci_count": failed_ci_count,
            "review_backlog_count": review_backlog,
            "at_risk_milestones": at_risk_milestones,
            "completion_percentage": completion_pct,
            "project_health": health,
        }


