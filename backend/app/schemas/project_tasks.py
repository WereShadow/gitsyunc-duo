from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# --- Milestone Schemas ---
class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_date: Optional[str] = None

class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_date: Optional[str] = None
    status: Optional[str] = None

class MilestoneResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    target_date: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
    completed_task_count: int = 0

    class Config:
        from_attributes = True


# --- Dependency Schemas ---
class DependencyItem(BaseModel):
    task_id: str
    depends_on_task_id: str
    depends_on_title: Optional[str] = None
    depends_on_status: Optional[str] = None
    is_blocking: bool = False

    class Config:
        from_attributes = True

class DependencyCreate(BaseModel):
    depends_on_task_id: str


# --- Review Schemas ---
class TaskReviewCreate(BaseModel):
    status: str = Field(..., pattern='^(APPROVED|CHANGES_REQUESTED)$')
    comment: str = Field(..., min_length=1)
    commit_sha: Optional[str] = None

class TaskReviewResponse(BaseModel):
    id: str
    task_id: str
    reviewer_id: str
    reviewer_name: Optional[str] = None
    reviewer_avatar: Optional[str] = None
    status: str
    comment: str
    commit_sha: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Comment Schemas ---
class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)

class TaskCommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Task Submission & Status Schemas ---
class TaskSubmit(BaseModel):
    branch: Optional[str] = None
    pull_request_url: Optional[str] = None
    pull_request_number: Optional[int] = None
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    changed_files: Optional[List[str]] = None
    submission_notes: Optional[str] = None

class TaskStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern='^(BACKLOG|TODO|IN_PROGRESS|SUBMITTED|UNDER_REVIEW|CHANGES_REQUESTED|APPROVED|COMPLETED)$'
    )


# --- Task Schemas ---
class ProjectTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    milestone_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: str = Field(default='MEDIUM', pattern='^(LOW|MEDIUM|HIGH|URGENT)$')
    deadline: Optional[datetime] = None
    github_repo: Optional[str] = None
    branch: Optional[str] = None
    dependencies: Optional[List[str]] = None

class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    milestone_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None
    github_repo: Optional[str] = None
    branch: Optional[str] = None
    pull_request_url: Optional[str] = None
    status: Optional[str] = None

class ProjectTaskResponse(BaseModel):
    id: str
    project_id: str
    milestone_id: Optional[str] = None
    milestone_title: Optional[str] = None
    creator_id: str
    creator_name: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_avatar: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: str
    deadline: Optional[datetime] = None
    status: str
    is_blocked: bool = False
    blocked_by: List[Dict[str, Any]] = []
    github_repo: Optional[str] = None
    branch: Optional[str] = None
    pull_request_url: Optional[str] = None
    pull_request_number: Optional[int] = None
    latest_commit_sha: Optional[str] = None
    latest_commit_message: Optional[str] = None
    changed_files: Optional[List[str]] = None
    verification_status: str
    verification_details: Optional[Dict[str, Any]] = None
    submission_notes: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    reviews: List[TaskReviewResponse] = []
    comment_count: int = 0

    class Config:
        from_attributes = True


# --- Activity Log ---
class ActivityLogResponse(BaseModel):
    id: str
    project_id: str
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Dashboards ---
class MemberActivityStat(BaseModel):
    user_id: str
    full_name: str
    avatar_url: Optional[str] = None
    assigned_count: int = 0
    completed_count: int = 0
    in_progress_count: int = 0
    submitted_count: int = 0
    awaiting_review_count: int = 0

class ProjectDashboardResponse(BaseModel):
    project_id: str
    project_name: str
    github_repo_full_name: str
    completion_percentage: float
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    tasks_awaiting_review: int
    project_health: str
    milestones: List[MilestoneResponse] = []
    member_activities: List[MemberActivityStat] = []
    recent_activity: List[ActivityLogResponse] = []
    recent_tasks: List[ProjectTaskResponse] = []

class MemberDashboardResponse(BaseModel):
    user_id: str
    assigned_tasks: List[ProjectTaskResponse] = []
    submitted_tasks: List[ProjectTaskResponse] = []
    tasks_awaiting_my_review: List[ProjectTaskResponse] = []
    tasks_requiring_changes: List[ProjectTaskResponse] = []
    completed_tasks: List[ProjectTaskResponse] = []
    overdue_count: int = 0
