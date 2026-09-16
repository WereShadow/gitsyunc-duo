from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    github_repo_owner: str
    github_repo_name: str
    branch: str = "main"
    assigned_area: Optional[str] = None  # e.g., "Backend / FastAPI" or "Frontend / React"
    verification_enabled: bool = True
    required_checks: Optional[Dict[str, bool]] = None

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    description: Optional[str] = None
    branch: Optional[str] = None
    assigned_area: Optional[str] = None
    verification_enabled: Optional[bool] = None
    required_checks: Optional[Dict[str, bool]] = None

class ProjectResponse(BaseModel):
    id: str
    duo_id: str
    user_id: Optional[str] = None
    project_name: str
    description: Optional[str] = None
    github_repo_owner: str
    github_repo_name: str
    github_repo_full_name: str
    github_repo_id: Optional[str] = None
    branch: str
    assigned_area: Optional[str] = None
    verification_enabled: bool
    required_checks: Dict[str, bool] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
