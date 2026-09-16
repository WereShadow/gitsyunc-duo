import asyncio
from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AsyncSessionLocal
from app.models.entities import DailyTask, Duo, DuoMember, DailyUserProgress, Project, GitHubAccount, Notification
from app.services.completion_engine import CompletionEngine
from app.services.github_service import GitHubService
from app.core.security import decrypt_token

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """
    Background worker that runs every minute to:
    1. Check deadlines and mark uncompleted expired tasks as MISSED (resets streak).
    2. Run fallback commit verification for duos whose members haven't triggered webhooks.
    3. Send deadline warning notifications when under 2 hours remain.
    """
    def __init__(self):
        self._running = False
        self._task: asyncio.Task = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("GitSync Duo background scheduler started.")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("GitSync Duo background scheduler stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.check_deadlines_and_verify()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background scheduler loop: {e}", exc_info=True)
            
            # Wait 60 seconds before next iteration
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break

    async def check_deadlines_and_verify(self):
        # Use naive UTC so comparisons work with SQLite's naive datetime storage
        now_utc = datetime.utcnow()
        async with AsyncSessionLocal() as session:
            try:
                # Find all active or waiting tasks
                tasks_res = await session.execute(
                    select(DailyTask).where(
                        DailyTask.status.in_([
                            "ACTIVE",
                            "WAITING_FOR_USER_A",
                            "WAITING_FOR_USER_B",
                            "WAITING_FOR_REVIEW",
                            "CHANGES_REQUESTED"
                        ])
                    )
                )
                active_tasks = tasks_res.scalars().all()

                for task in active_tasks:
                    duo_res = await session.execute(
                        select(Duo).where(Duo.id == task.duo_id)
                    )
                    duo = duo_res.scalar_one_or_none()
                    if not duo:
                        continue

                    # 1. Evaluate deadline rollover
                    effective_deadline = task.deadline_utc + timedelta(minutes=duo.grace_period_minutes)
                    if now_utc > effective_deadline:
                        logger.info(f"Task {task.id} for Duo {duo.name} expired. Marking as MISSED.")
                        await CompletionEngine.evaluate_task_completion(session, task)
                        continue

                    # 2. Check for deadline warning (between 1h and 2h remaining)
                    time_remaining = effective_deadline - now_utc
                    if timedelta(hours=1) <= time_remaining <= timedelta(hours=2):
                        # Send deadline warning if not already sent
                        members_res = await session.execute(
                            select(DuoMember).where(DuoMember.duo_id == duo.id)
                        )
                        members = members_res.scalars().all()
                        for m in members:
                            existing_warn = await session.execute(
                                select(Notification).where(
                                    and_(
                                        Notification.user_id == m.user_id,
                                        Notification.duo_id == duo.id,
                                        Notification.type == "DEADLINE_WARNING",
                                        Notification.created_at >= task.created_at
                                    )
                                )
                            )
                            if not existing_warn.scalar_one_or_none():
                                warn_notif = Notification(
                                    user_id=m.user_id,
                                    duo_id=duo.id,
                                    type="DEADLINE_WARNING",
                                    title="⏳ 2 Hours Remaining",
                                    message=f"Only 2 hours left to complete today's requirement for '{task.title}' and protect your streak!"
                                )
                                session.add(warn_notif)

                    # 3. Fallback GitHub commit verification
                    prog_res = await session.execute(
                        select(DailyUserProgress).where(DailyUserProgress.daily_task_id == task.id)
                    )
                    user_progresses = prog_res.scalars().all()
                    
                    for up in user_progresses:
                        if not up.github_verified:
                            # Try to verify user
                            await self._verify_user_commits(session, task, duo, up)

                    # Re-evaluate completion status
                    await CompletionEngine.evaluate_task_completion(session, task)

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error checking tasks in scheduler: {e}")

    async def _verify_user_commits(
        self,
        session: AsyncSession,
        task: DailyTask,
        duo: Duo,
        progress: DailyUserProgress
    ):
        # Fetch GitHub account
        gh_res = await session.execute(
            select(GitHubAccount).where(GitHubAccount.user_id == progress.user_id)
        )
        gh_acc = gh_res.scalar_one_or_none()
        if not gh_acc:
            return

        # Fetch user's project or shared project
        proj_res = await session.execute(
            select(Project).where(
                and_(
                    Project.duo_id == duo.id,
                    (Project.user_id == progress.user_id) | (Project.user_id == None)
                )
            )
        )
        proj = proj_res.scalar_one_or_none()
        if not proj:
            return

        token = None
        if gh_acc.encrypted_access_token:
            try:
                token = decrypt_token(gh_acc.encrypted_access_token)
            except Exception:
                pass

        gh_service = GitHubService(token=token)

        # Day start & end
        start_utc, end_utc, _ = CompletionEngine.get_day_boundaries(duo.timezone, task.date, duo.deadline_time)

        result = await gh_service.verify_commits(
            repo_owner=proj.github_repo_owner,
            repo_name=proj.github_repo_name,
            branch=proj.branch,
            github_username=gh_acc.github_username,
            since_utc=start_utc,
            until_utc=end_utc + timedelta(minutes=duo.grace_period_minutes),
            min_commits=task.min_commits_required
        )

        if result.get("verified"):
            progress.github_verified = True
            progress.commit_count = result.get("commit_count", 1)
            progress.verified_at = datetime.now(timezone.utc)
            latest = result.get("latest_commit")
            if latest:
                progress.latest_commit_sha = latest.get("sha")
                progress.latest_commit_message = latest.get("message")
                progress.latest_commit_url = latest.get("url")

scheduler = BackgroundScheduler()
