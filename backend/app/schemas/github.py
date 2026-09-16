from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class GitHubStatusResponse(BaseModel):
    connected: bool
    github_username: Optional[str] = None
    avatar_url: Optional[str] = None
    scopes: Optional[str] = None
    connected_at: Optional[datetime] = None

class GitHubRepoItem(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    default_branch: str
    private: bool
    description: Optional[str] = None
    html_url: str

class CommitItem(BaseModel):
    sha: str
    message: str
    author_name: str
    author_username: Optional[str] = None
    date: datetime
    url: str
    files_changed: List[str] = []

class GitHubActivityResponse(BaseModel):
    user_id: str
    github_username: str
    repository: Optional[str] = None
    branch: Optional[str] = None
    today_commits: List[CommitItem] = []
    total_today_commits: int = 0
    pushes_count: int = 0
    verification_status: bool = False
    last_activity_at: Optional[datetime] = None

class SimulatePushRequest(BaseModel):
    repository_full_name: str = Field(..., description="e.g. team/campus-ai or user/repo")
    branch: str = Field(default="main")
    commit_sha: Optional[str] = None
    commit_message: str = Field(default="Feature update", min_length=1)
    author_username: Optional[str] = None
    files_changed: List[str] = Field(default_factory=lambda: ["main.py", "app.ts"])
    target_user_id: Optional[str] = None
