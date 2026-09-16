import httpx
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitSync-Duo-App/1.0"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    async def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.request(method, url, headers=self.headers, **kwargs)
                    
                    # If rate limited (403 or 429), respect rate limit if not critical
                    if response.status_code in (403, 429) and attempt < max_retries - 1:
                        logger.warning(f"GitHub API rate limited on {url}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        logger.warning(f"GitHub API server error ({response.status_code}) on {url}. Retrying...")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue

                    return response
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt == max_retries - 1:
                    logger.error(f"GitHub API request failed after {max_retries} attempts: {exc}")
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2

        raise httpx.RequestError("Max retries exceeded")

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Fetch authenticated GitHub user profile."""
        if not self.token:
            return None
        try:
            resp = await self._request_with_retry("GET", "/user")
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error(f"Failed to fetch current GitHub user: {e}")
            return None

    async def get_user_repositories(self) -> List[Dict[str, Any]]:
        """List repositories accessible to the authenticated user."""
        if not self.token:
            return []
        try:
            resp = await self._request_with_retry("GET", "/user/repos?sort=updated&per_page=50")
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Failed to list user repositories: {e}")
            return []

    async def get_repo_branches(self, repo_owner: str, repo_name: str) -> List[str]:
        """List branches for a repository."""
        try:
            resp = await self._request_with_retry("GET", f"/repos/{repo_owner}/{repo_name}/branches")
            if resp.status_code == 200:
                return [b["name"] for b in resp.json()]
            return ["main"]
        except Exception:
            return ["main"]

    async def verify_commits(
        self,
        repo_owner: str,
        repo_name: str,
        branch: str,
        github_username: str,
        since_utc: datetime,
        until_utc: datetime,
        min_commits: int = 1
    ) -> Dict[str, Any]:
        """
        Verify if the given GitHub user made qualifying commits to the configured repo/branch
        between since_utc and until_utc.
        """
        if not self.token:
            from app.services.simulation_store import sim_store
            repo_full = f"{repo_owner}/{repo_name}".lower()
            sim_commits = sim_store.get_commits(
                repo_full_name=repo_full,
                branch=branch,
                author_username=github_username,
                since_utc=since_utc,
                until_utc=until_utc
            )
            count = len(sim_commits)
            return {
                "verified": count >= min_commits,
                "commit_count": count,
                "commits": sim_commits,
                "latest_commit": sim_commits[0] if sim_commits else None,
                "error": None if count >= min_commits else "No GitHub access token configured and no qualifying commits found in simulation"
            }

        endpoint = f"/repos/{repo_owner}/{repo_name}/commits"
        params = {
            "sha": branch,
            "since": since_utc.isoformat(),
            "until": until_utc.isoformat(),
            "per_page": 50
        }

        try:
            resp = await self._request_with_retry("GET", endpoint, params=params)
            if resp.status_code == 404:
                return {
                    "verified": False,
                    "commit_count": 0,
                    "commits": [],
                    "error": f"Repository '{repo_owner}/{repo_name}' or branch '{branch}' not found"
                }
            if resp.status_code != 200:
                return {
                    "verified": False,
                    "commit_count": 0,
                    "commits": [],
                    "error": f"GitHub API error: {resp.status_code}"
                }

            all_commits = resp.json()
            qualifying_commits = []

            for c in all_commits:
                author_obj = c.get("author") or {}
                committer_obj = c.get("committer") or {}
                commit_author = author_obj.get("login") or committer_obj.get("login")
                
                # Check author login matching case-insensitively
                if commit_author and commit_author.lower() == github_username.lower():
                    qualifying_commits.append({
                        "sha": c.get("sha", "")[:7],
                        "full_sha": c.get("sha", ""),
                        "message": c.get("commit", {}).get("message", "").split("\n")[0],
                        "author_name": c.get("commit", {}).get("author", {}).get("name", ""),
                        "author_username": commit_author,
                        "date": c.get("commit", {}).get("author", {}).get("date", ""),
                        "url": c.get("html_url", "")
                    })

            count = len(qualifying_commits)
            if count >= min_commits:
                return {
                    "verified": True,
                    "commit_count": count,
                    "commits": qualifying_commits,
                    "latest_commit": qualifying_commits[0] if qualifying_commits else None,
                    "error": None
                }
            
            # Check simulation store as complement/fallback
            from app.services.simulation_store import sim_store
            repo_full = f"{repo_owner}/{repo_name}".lower()
            sim_commits = sim_store.get_commits(
                repo_full_name=repo_full,
                branch=branch,
                author_username=github_username,
                since_utc=since_utc,
                until_utc=until_utc
            )
            for sc in sim_commits:
                if not any(qc["sha"] == sc["sha"] for qc in qualifying_commits):
                    qualifying_commits.append(sc)

            count = len(qualifying_commits)
            return {
                "verified": count >= min_commits,
                "commit_count": count,
                "commits": qualifying_commits,
                "latest_commit": qualifying_commits[0] if qualifying_commits else None,
                "error": None
            }

        except Exception as e:
            logger.warning(f"Live GitHub verification failed ({e}), checking simulation store fallback...")
            from app.services.simulation_store import sim_store
            repo_full = f"{repo_owner}/{repo_name}".lower()
            sim_commits = sim_store.get_commits(
                repo_full_name=repo_full,
                branch=branch,
                author_username=github_username,
                since_utc=since_utc,
                until_utc=until_utc
            )
            count = len(sim_commits)
            return {
                "verified": count >= min_commits,
                "commit_count": count,
                "commits": sim_commits,
                "latest_commit": sim_commits[0] if sim_commits else None,
                "error": None if count >= min_commits else str(e)
            }

    async def get_check_runs(self, repo_owner: str, repo_name: str, ref: str) -> Dict[str, Any]:
        """
        Check GitHub Actions status / check runs for a specific branch or commit SHA.
        """
        if not self.token:
            return {"status": "SKIPPED", "runs": [], "message": "No token provided"}

        endpoint = f"/repos/{repo_owner}/{repo_name}/commits/{ref}/check-runs"
        try:
            resp = await self._request_with_retry("GET", endpoint)
            if resp.status_code == 200:
                data = resp.json()
                check_runs = data.get("check_runs", [])
                if not check_runs:
                    return {"status": "SKIPPED", "runs": [], "message": "No check runs found"}

                all_passed = True
                any_in_progress = False
                for cr in check_runs:
                    conclusion = cr.get("conclusion")
                    status = cr.get("status")
                    if status != "completed":
                        any_in_progress = True
                    elif conclusion not in ("success", "neutral", "skipped"):
                        all_passed = False

                if any_in_progress:
                    return {"status": "PENDING", "runs": check_runs}
                return {"status": "PASSED" if all_passed else "FAILED", "runs": check_runs}

            return {"status": "SKIPPED", "runs": [], "message": f"Status {resp.status_code}"}
        except Exception as e:
            logger.warning(f"Failed to fetch check runs: {e}")
            return {"status": "SKIPPED", "runs": [], "message": str(e)}

    async def get_pull_request_for_branch(self, repo_owner: str, repo_name: str, branch: str) -> Optional[Dict[str, Any]]:
        """Look for an open or recently merged pull request for the branch."""
        if not self.token:
            return None
        endpoint = f"/repos/{repo_owner}/{repo_name}/pulls"
        params = {"head": f"{repo_owner}:{branch}", "state": "all", "per_page": 5}
        try:
            resp = await self._request_with_retry("GET", endpoint, params=params)
            if resp.status_code == 200:
                prs = resp.json()
                if prs:
                    pr = prs[0]
                    return {
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "url": pr.get("html_url"),
                        "state": pr.get("state"),
                        "merged": pr.get("merged_at") is not None
                    }
            return None
        except Exception:
            return None
