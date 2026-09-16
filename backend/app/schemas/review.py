from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    status: str = Field(..., pattern="^(APPROVED|CHANGES_REQUESTED)$")
    comment: str = Field(..., min_length=3, max_length=2000)
    commit_sha: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    daily_task_id: str
    task_owner_id: str
    task_owner_name: Optional[str] = None
    reviewer_id: str
    reviewer_name: Optional[str] = None
    status: str
    comment: str
    commit_sha: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
