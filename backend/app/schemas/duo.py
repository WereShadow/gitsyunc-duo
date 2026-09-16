from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.streak import StreakResponse

class DuoCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    project_mode: str = Field(default="SEPARATE", pattern="^(SEPARATE|SHARED)$")
    workflow_type: str = Field(default="SEPARATE_BRANCHES", pattern="^(SAME_BRANCH|SEPARATE_BRANCHES|PULL_REQUESTS)$")
    timezone: str = Field(default="Asia/Kolkata")
    deadline_time: str = Field(default="23:59")
    grace_period_minutes: int = Field(default=30, ge=0, le=360)

class DuoJoin(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=32)

class DuoSettingsUpdate(BaseModel):
    timezone: Optional[str] = None
    deadline_time: Optional[str] = None
    grace_period_minutes: Optional[int] = Field(default=None, ge=0, le=360)
    project_mode: Optional[str] = Field(default=None, pattern="^(SEPARATE|SHARED)$")
    workflow_type: Optional[str] = Field(default=None, pattern="^(SAME_BRANCH|SEPARATE_BRANCHES|PULL_REQUESTS)$")

class DuoMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    github_username: Optional[str] = None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True

class DuoResponse(BaseModel):
    id: str
    name: str
    invite_code: str
    created_by: str
    timezone: str
    deadline_time: str
    grace_period_minutes: int
    project_mode: str
    workflow_type: str
    created_at: datetime
    members: List[DuoMemberResponse] = []
    streak: Optional[StreakResponse] = None

    class Config:
        from_attributes = True
