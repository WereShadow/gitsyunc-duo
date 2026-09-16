from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

class SimulationStore:
    """
    In-memory simulation store for development, automated testing, and local demos.
    Allows pushing commits, simulating checks, and verifying GitHub activity
    without requiring external internet tunnels or public GitHub repo setup.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimulationStore, cls).__new__(cls)
            cls._instance._commits = []
            cls._instance._check_runs = {}
        return cls._instance

    def add_commit(
        self,
        repo_full_name: str,
        branch: str,
        author_username: str,
        author_name: str,
        message: str,
        sha: Optional[str] = None,
        files: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        import uuid
        now = timestamp or datetime.now(timezone.utc)
        clean_sha = sha or uuid.uuid4().hex[:7]
        commit = {
            "sha": clean_sha[:7],
            "full_sha": clean_sha,
            "repo_full_name": repo_full_name.lower(),
            "branch": branch,
            "author_username": author_username.lower(),
            "author_name": author_name,
            "message": message,
            "date": now.isoformat(),
            "timestamp": now,
            "url": f"https://github.com/{repo_full_name}/commit/{clean_sha}",
            "files": files or ["src/index.ts", "package.json"]
        }
        self._commits.insert(0, commit)
        return commit

    def get_commits(
        self,
        repo_full_name: str,
        branch: Optional[str] = None,
        author_username: Optional[str] = None,
        since_utc: Optional[datetime] = None,
        until_utc: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for c in self._commits:
            if repo_full_name and c["repo_full_name"] != repo_full_name.lower():
                continue
            if branch and c["branch"] != branch:
                continue
            if author_username and c["author_username"] != author_username.lower():
                continue
            if since_utc and c["timestamp"] < since_utc:
                continue
            if until_utc and c["timestamp"] > until_utc:
                continue
            results.append(c)
        return results

    def clear(self):
        self._commits.clear()
        self._check_runs.clear()

sim_store = SimulationStore()
