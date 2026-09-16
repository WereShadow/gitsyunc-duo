import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import (
    WebhookEvent,
    Project,
    GitHubAccount,
    DailyTask,
    DailyUserProgress,
    Duo,
)
from app.core.config import settings
from app.core.security import verify_github_signature
from app.services.completion_engine import CompletionEngine

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/github")
async def handle_github_webhook(
    request: Request,
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
):
    body_bytes = await request.body()

    # 1. Signature Verification
    if settings.GITHUB_WEBHOOK_SECRET:
        if not verify_github_signature(body_bytes, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook signature"
            )

    # 2. Idempotency check via Delivery ID
    delivery_id = x_github_delivery or hashlib.sha256(body_bytes).hexdigest()[:32]
    existing_event = await db.execute(
        select(WebhookEvent).where(WebhookEvent.delivery_id == delivery_id)
    )
    if existing_event.scalar_one_or_none():
        # Already processed this exact webhook delivery
        return {"status": "IGNORED", "detail": "Duplicate delivery ID ignored idempotently"}

    payload_hash = hashlib.sha256(body_bytes).hexdigest()
    webhook_record = WebhookEvent(
        delivery_id=delivery_id,
        event_type=x_github_event or "push",
        payload_hash=payload_hash,
        status="PROCESSED",
        created_at=datetime.now(timezone.utc)
    )
    db.add(webhook_record)

    # If ping event, return pong
    if x_github_event == "ping":
        await db.commit()
        return {"status": "PONG", "message": "Webhook configured successfully"}

    if x_github_event != "push":
        await db.commit()
        return {"status": "SKIPPED", "detail": f"Event '{x_github_event}' ignored"}

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        await db.commit()
        return {"status": "SKIPPED", "detail": "Invalid JSON"}

    # Extract repository and branch info
    repo_obj = payload.get("repository") or {}
    repo_full_name = repo_obj.get("full_name", "").lower()

    ref = payload.get("ref", "")  # refs/heads/main
    branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

    pusher_obj = payload.get("pusher") or {}
    sender_obj = payload.get("sender") or {}
    pusher_username = (pusher_obj.get("name") or sender_obj.get("login") or "").lower()

    commits = payload.get("commits", [])
    if not commits or not repo_full_name:
        await db.commit()
        return {"status": "SKIPPED", "detail": "No commits or repo found"}

    # Find matching project
    proj_res = await db.execute(
        select(Project).where(Project.github_repo_full_name == repo_full_name)
    )
    matching_projects = proj_res.scalars().all()
    if not matching_projects:
        await db.commit()
        return {"status": "SKIPPED", "detail": f"No project configured for repository '{repo_full_name}'"}

    # Process commits for each project matching
    for proj in matching_projects:
        # Branch check if branch is configured
        if proj.branch and branch and proj.branch != branch:
            continue

        duo_res = await db.execute(select(Duo).where(Duo.id == proj.duo_id))
        duo = duo_res.scalar_one_or_none()
        if not duo:
            continue

        # Find user matching pusher or commit authors
        # First check GitHubAccount
        gh_acc_res = await db.execute(
            select(GitHubAccount).where(GitHubAccount.github_username.ilike(pusher_username))
        )
        gh_acc = gh_acc_res.scalar_one_or_none()
        target_user_id = gh_acc.user_id if gh_acc else proj.user_id

        if not target_user_id:
            continue

        # Get today's task for this duo
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
            continue

        # Find or create user progress
        prog_res = await db.execute(
            select(DailyUserProgress).where(
                and_(
                    DailyUserProgress.daily_task_id == task.id,
                    DailyUserProgress.user_id == target_user_id
                )
            )
        )
        prog = prog_res.scalar_one_or_none()
        if not prog:
            prog = DailyUserProgress(
                daily_task_id=task.id,
                user_id=target_user_id,
                github_verified=True,
                commit_count=len(commits),
                submission_status="SUBMITTED",
                review_status="UNDER_REVIEW"
            )
            db.add(prog)
        else:
            prog.github_verified = True
            prog.commit_count += len(commits)

        # Update latest commit details
        latest_c = commits[-1]
        prog.latest_commit_sha = latest_c.get("id", "")[:7]
        prog.latest_commit_message = latest_c.get("message", "").split("\n")[0]
        prog.latest_commit_url = latest_c.get("url")
        prog.latest_commit_time = datetime.now(timezone.utc)
        prog.verified_at = datetime.now(timezone.utc)

        # Extract modified files
        all_files = set()
        for c in commits:
            all_files.update(c.get("added", []))
            all_files.update(c.get("modified", []))
        prog.changed_files = json.dumps(list(all_files)[:20])

        # If changes were previously requested, flip to SUBMITTED for review again!
        if prog.review_status == "CHANGES_REQUESTED":
            prog.submission_status = "SUBMITTED"
            prog.review_status = "UNDER_REVIEW"

        # Authoritatively evaluate completion
        await CompletionEngine.evaluate_task_completion(db, task)

    await db.commit()
    return {"status": "SUCCESS", "message": "Push event processed and verified"}
