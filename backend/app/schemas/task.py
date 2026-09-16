from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.review import ReviewResponse

class UserTaskProgressDetail(BaseModel):
    user_id: str
    user_name: str
    user_email: str
    avatar_url: Optional[str] = None
    github_username: Optional[str] = None
    assigned_task: Optional[str] = None
    github_verified: bool
    commit_count: int
    latest_commit_sha: Optional[str] = None
    latest_commit_message: Optional[str] = None
    latest_commit_url: Optional[str] = None
    latest_commit_time: Optional[datetime] = None
    changed_files: List[str] = []
    pull_request_url: Optional[str] = None
    submission_status: str
    review_status: str
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

class ProjectVerificationDetail(BaseModel):
    id: str
    repository: str
    commit_sha: Optional[str] = None
    build_status: str
    test_status: str
    lint_status: str
    ci_status: str
    overall_status: str
    details: Dict[str, Any] = {}
    checked_at: datetime

class DailyTaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    user_a_task: Optional[str] = None
    user_b_task: Optional[str] = None
    github_requirement: str = "1 commit"
    min_commits_required: int = Field(default=1, ge=1)
    date: Optional[str] = None  # Optional YYYY-MM-DD

class DailyTaskResponse(BaseModel):
    id: str
    duo_id: str
    date: str
    title: str
    description: Optional[str] = None
    user_a_task: Optional[str] = None
    user_b_task: Optional[str] = None
    github_requirement: str
    min_commits_required: int
    deadline_utc: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    user_progress: List[UserTaskProgressDetail] = []
    reviews: List[ReviewResponse] = []
    verifications: List[ProjectVerificationDetail] = []

    class Config:
        from_attributes = True
