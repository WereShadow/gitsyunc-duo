from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import (
    User,
    GitHubAccount,
    DuoMember,
    Duo,
    DailyTask,
    DailyUserProgress,
    Project,
)
from app.schemas.github import (
    GitHubStatusResponse,
    GitHubRepoItem,
    CommitItem,
    GitHubActivityResponse,
    SimulatePushRequest,
)
from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token
from app.api.deps import get_current_user
from app.services.github_service import GitHubService
from app.services.completion_engine import CompletionEngine
from app.services.simulation_store import sim_store

router = APIRouter(prefix="/github", tags=["GitHub"])

class ConnectTokenRequest(BaseModel):
    github_username: str
    access_token: str

@router.get("/connect")
async def get_github_connect_url():
    """Return GitHub OAuth authorization URL."""
    if not settings.GITHUB_CLIENT_ID:
        # If client ID not configured, indicate dev mode
        return {
            "oauth_configured": False,
            "message": "GitHub OAuth App credentials not configured in backend environment. You can use direct token connect."
        }
    
    redirect_uri = "http://localhost:5173/github/callback"
    scope = "repo,user,read:org"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope={scope}"
        f"&redirect_uri={redirect_uri}"
    )
    return {"oauth_configured": True, "url": url}

@router.post("/connect-token", response_model=GitHubStatusResponse)
async def connect_token(
    data: ConnectTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Connect GitHub account with a personal access token or test token.
    Securely encrypts token using Fernet before persisting.
    """
    # Test token if it looks real, or accept for dev
    username = data.github_username.strip()
    clean_token = data.access_token.strip()

    gh_service = GitHubService(token=clean_token)
    profile = await gh_service.get_current_user()
    if profile and profile.get("login"):
        username = profile.get("login")

    # Encrypt token
    encrypted = encrypt_token(clean_token)
    now = datetime.now(timezone.utc)

    # Upsert GitHubAccount
    res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == current_user.id))
    acc = res.scalar_one_or_none()
    if acc:
        acc.github_username = username
        acc.encrypted_access_token = encrypted
        acc.token_scope = "repo,user"
        acc.updated_at = now
    else:
        acc = GitHubAccount(
            user_id=current_user.id,
            github_username=username,
            encrypted_access_token=encrypted,
            token_scope="repo,user",
            connected_at=now,
            updated_at=now
        )
        db.add(acc)

    await db.commit()
    await db.refresh(acc)

    return GitHubStatusResponse(
        connected=True,
        github_username=acc.github_username,
        avatar_url=profile.get("avatar_url") if profile else None,
        scopes=acc.token_scope,
        connected_at=acc.connected_at
    )

@router.get("/status", response_model=GitHubStatusResponse)
async def get_github_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == current_user.id))
    acc = res.scalar_one_or_none()
    if not acc:
        return GitHubStatusResponse(connected=False)

    return GitHubStatusResponse(
        connected=True,
        github_username=acc.github_username,
        avatar_url=current_user.avatar_url,
        scopes=acc.token_scope,
        connected_at=acc.connected_at
    )

@router.get("/repositories", response_model=List[GitHubRepoItem])
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == current_user.id))
    acc = res.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=400, detail="GitHub account not connected")

    try:
        token = decrypt_token(acc.encrypted_access_token)
        gh_service = GitHubService(token=token)
        repos = await gh_service.get_user_repositories()
        
        output = []
        for r in repos:
            output.append(
                GitHubRepoItem(
                    id=r.get("id"),
                    name=r.get("name"),
                    full_name=r.get("full_name"),
                    owner=r.get("owner", {}).get("login", acc.github_username),
                    default_branch=r.get("default_branch", "main"),
                    private=r.get("private", False),
                    description=r.get("description"),
                    html_url=r.get("html_url", f"https://github.com/{r.get('full_name')}")
                )
            )
        if output:
            return output
    except Exception:
        pass

    # Default fallback demo repositories if external API call fails
    return [
        GitHubRepoItem(
            id=101,
            name="campus-ai",
            full_name=f"{acc.github_username}/campus-ai",
            owner=acc.github_username,
            default_branch="main",
            private=False,
            description="AI Campus Assistant monorepo",
            html_url=f"https://github.com/{acc.github_username}/campus-ai"
        ),
        GitHubRepoItem(
            id=102,
            name="fastapi-backend",
            full_name=f"{acc.github_username}/fastapi-backend",
            owner=acc.github_username,
            default_branch="main",
            private=True,
            description="Core backend services",
            html_url=f"https://github.com/{acc.github_username}/fastapi-backend"
        ),
        GitHubRepoItem(
            id=103,
            name="react-frontend",
            full_name=f"{acc.github_username}/react-frontend",
            owner=acc.github_username,
            default_branch="main",
            private=False,
            description="Modern web UI client",
            html_url=f"https://github.com/{acc.github_username}/react-frontend"
        )
    ]

@router.get("/activity", response_model=GitHubActivityResponse)
async def get_github_activity(
    target_user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_to_check_id = target_user_id or current_user.id

    # Get user's github account
    gh_res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == user_to_check_id))
    gh_acc = gh_res.scalar_one_or_none()
    username = gh_acc.github_username if gh_acc else "unknown"

    # Get duo and today's task
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == user_to_check_id)
    )
    record = mem_res.first()
    if not record:
        return GitHubActivityResponse(
            user_id=user_to_check_id,
            github_username=username,
            today_commits=[],
            total_today_commits=0,
            pushes_count=0,
            verification_status=False
        )
    membership, duo = record

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

    # Get project
    proj_res = await db.execute(
        select(Project).where(
            and_(
                Project.duo_id == duo.id,
                (Project.user_id == user_to_check_id) | (Project.user_id == None)
            )
        )
    )
    proj = proj_res.scalar_one_or_none()
    repo_name = proj.github_repo_full_name if proj else None
    branch = proj.branch if proj else "main"

    commits_list: List[CommitItem] = []
    verified = False
    last_act = None

    if task:
        prog_res = await db.execute(
            select(DailyUserProgress).where(
                and_(
                    DailyUserProgress.daily_task_id == task.id,
                    DailyUserProgress.user_id == user_to_check_id
                )
            )
        )
        prog = prog_res.scalar_one_or_none()
        if prog:
            verified = prog.github_verified
            last_act = prog.latest_commit_time or prog.verified_at
            if prog.latest_commit_sha:
                commits_list.append(
                    CommitItem(
                        sha=prog.latest_commit_sha,
                        message=prog.latest_commit_message or "Verified daily work",
                        author_name=username,
                        author_username=username,
                        date=prog.latest_commit_time or datetime.now(timezone.utc),
                        url=prog.latest_commit_url or f"https://github.com/{repo_name}/commit/{prog.latest_commit_sha}",
                        files_changed=[]
                    )
                )

    # Also include simulated commits if any
    if repo_name and username:
        start_utc, end_utc, _ = CompletionEngine.get_day_boundaries(duo.timezone, today_str, duo.deadline_time)
        sim_c = sim_store.get_commits(
            repo_full_name=repo_name,
            branch=branch,
            author_username=username,
            since_utc=start_utc,
            until_utc=end_utc + timedelta(minutes=duo.grace_period_minutes)
        )
        for sc in sim_c:
            if not any(c.sha == sc["sha"] for c in commits_list):
                commits_list.append(
                    CommitItem(
                        sha=sc["sha"],
                        message=sc["message"],
                        author_name=sc["author_name"],
                        author_username=sc["author_username"],
                        date=sc["timestamp"],
                        url=sc["url"],
                        files_changed=sc["files"]
                    )
                )

    return GitHubActivityResponse(
        user_id=user_to_check_id,
        github_username=username,
        repository=repo_name,
        branch=branch,
        today_commits=commits_list,
        total_today_commits=len(commits_list),
        pushes_count=len(commits_list),
        verification_status=verified,
        last_activity_at=last_act
    )

@router.post("/verify")
async def trigger_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger on-demand commit verification for current user and duo."""
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == current_user.id)
    )
    record = mem_res.first()
    if not record:
        raise HTTPException(status_code=400, detail="Not in an active Duo")
    membership, duo = record

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
        raise HTTPException(status_code=404, detail="No active task found for today")

    # Verify both members
    all_members = (await db.execute(
        select(DuoMember).where(DuoMember.duo_id == duo.id)
    )).scalars().all()

    start_utc, end_utc, _ = CompletionEngine.get_day_boundaries(duo.timezone, today_str, duo.deadline_time)
    until_utc = end_utc + timedelta(minutes=duo.grace_period_minutes)

    verified_results = []
    for m in all_members:
        # Get progress
        prog_res = await db.execute(
            select(DailyUserProgress).where(
                and_(
                    DailyUserProgress.daily_task_id == task.id,
                    DailyUserProgress.user_id == m.user_id
                )
            )
        )
        prog = prog_res.scalar_one_or_none()
        if not prog:
            continue

        # Get GitHub account
        gh_res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == m.user_id))
        gh_acc = gh_res.scalar_one_or_none()
        if not gh_acc:
            continue

        # Get project
        proj_res = await db.execute(
            select(Project).where(
                and_(
                    Project.duo_id == duo.id,
                    (Project.user_id == m.user_id) | (Project.user_id == None)
                )
            )
        )
        proj = proj_res.scalar_one_or_none()
        if not proj:
            continue

        raw_token = None
        if gh_acc.encrypted_access_token:
            try:
                raw_token = decrypt_token(gh_acc.encrypted_access_token)
            except Exception:
                pass

        gh_service = GitHubService(token=raw_token)
        verif = await gh_service.verify_commits(
            repo_owner=proj.github_repo_owner,
            repo_name=proj.github_repo_name,
            branch=proj.branch,
            github_username=gh_acc.github_username,
            since_utc=start_utc,
            until_utc=until_utc,
            min_commits=task.min_commits_required
        )

        if verif.get("verified"):
            prog.github_verified = True
            prog.commit_count = verif.get("commit_count", 1)
            prog.verified_at = datetime.now(timezone.utc)
            latest = verif.get("latest_commit")
            if latest:
                prog.latest_commit_sha = latest.get("sha")
                prog.latest_commit_message = latest.get("message")
                prog.latest_commit_url = latest.get("url")
            verified_results.append({
                "user_id": m.user_id,
                "verified": True,
                "commit_count": prog.commit_count
            })
        else:
            verified_results.append({
                "user_id": m.user_id,
                "verified": prog.github_verified,
                "error": verif.get("error")
            })

    # Authoritative evaluation
    eval_res = await CompletionEngine.evaluate_task_completion(db, task)
    await db.commit()

    return {
        "task_id": task.id,
        "daily_status": eval_res.get("status"),
        "completed": eval_res.get("completed"),
        "results": verified_results
    }

@router.post("/simulate-push")
async def simulate_push(
    data: SimulatePushRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Developer & Demo endpoint to simulate a real GitHub push event.
    Enables instant testing of commit verification, two-person rules, and peer review.
    """
    target_uid = data.target_user_id or current_user.id
    target_user = (await db.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Get GitHub account or auto-create if missing for simulation
    gh_res = await db.execute(select(GitHubAccount).where(GitHubAccount.user_id == target_uid))
    gh_acc = gh_res.scalar_one_or_none()
    author_username = data.author_username or (gh_acc.github_username if gh_acc else target_user.full_name.lower().replace(" ", "-"))

    if not gh_acc:
        gh_acc = GitHubAccount(
            user_id=target_uid,
            github_username=author_username,
            encrypted_access_token=encrypt_token("sim_token_dev"),
            token_scope="repo,user"
        )
        db.add(gh_acc)
        await db.flush()

    # Add commit to simulation store
    commit = sim_store.add_commit(
        repo_full_name=data.repository_full_name,
        branch=data.branch,
        author_username=author_username,
        author_name=target_user.full_name,
        message=data.commit_message,
        sha=data.commit_sha,
        files=data.files_changed,
        timestamp=datetime.now(timezone.utc)
    )

    # Find active task
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == target_uid)
    )
    record = mem_res.first()
    task = None
    if record:
        membership, duo = record
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

    if task:
        # Find or create progress record
        prog_res = await db.execute(
            select(DailyUserProgress).where(
                and_(
                    DailyUserProgress.daily_task_id == task.id,
                    DailyUserProgress.user_id == target_uid
                )
            )
        )
        prog = prog_res.scalar_one_or_none()
        if not prog:
            prog = DailyUserProgress(
                daily_task_id=task.id,
                user_id=target_uid,
                github_verified=True,
                commit_count=1,
                latest_commit_sha=commit["sha"],
                latest_commit_message=commit["message"],
                latest_commit_url=commit["url"],
                latest_commit_time=datetime.now(timezone.utc),
                submission_status="SUBMITTED",
                review_status="UNDER_REVIEW"
            )
            db.add(prog)
        else:
            prog.github_verified = True
            prog.commit_count += 1
            prog.latest_commit_sha = commit["sha"],
            prog.latest_commit_message = commit["message"]
            prog.latest_commit_url = commit["url"]
            prog.latest_commit_time = datetime.now(timezone.utc)
            if prog.review_status == "CHANGES_REQUESTED":
                prog.submission_status = "SUBMITTED"
                prog.review_status = "UNDER_REVIEW"

        import json
        prog.changed_files = json.dumps(data.files_changed)

        # Authoritative completion evaluation
        await CompletionEngine.evaluate_task_completion(db, task)
        await db.commit()
        await db.refresh(task)

    return {
        "success": True,
        "commit": commit,
        "task_status": task.status if task else None,
        "message": f"Successfully simulated push to {data.repository_full_name} ({data.branch})"
    }
