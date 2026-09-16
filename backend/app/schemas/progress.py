from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.schemas.task import UserTaskProgressDetail, ProjectVerificationDetail

class TodayProgressResponse(BaseModel):
    task_id: Optional[str] = None
    duo_id: str
    date: str
    status: str
    deadline_utc: Optional[datetime] = None
    grace_period_minutes: int
    is_expired: bool = False
    title: Optional[str] = None
    description: Optional[str] = None
    current_user_progress: Optional[UserTaskProgressDetail] = None
    partner_user_progress: Optional[UserTaskProgressDetail] = None
    project_verification: Optional[ProjectVerificationDetail] = None
    can_submit: bool = False
    can_review: bool = False
    project_mode: str = "SEPARATE"

class CalendarDayItem(BaseModel):
    date: str  # YYYY-MM-DD
    status: str  # COMPLETED (Green), PARTIAL (Yellow), MISSED (Red), FUTURE (Grey), NO_TASK
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    both_completed: bool = False
    user_a_verified: bool = False
    user_b_verified: bool = False
    user_a_name: Optional[str] = None
    user_b_name: Optional[str] = None
    completed_at: Optional[datetime] = None

class CalendarHistoryResponse(BaseModel):
    duo_id: str
    days: List[CalendarDayItem]
    current_streak: int
    longest_streak: int
    total_completed: int
    total_missed: int
