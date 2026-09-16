from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class StreakResponse(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    completed_days: int = 0
    missed_days: int = 0
    last_completed_date: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
