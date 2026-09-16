import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.entities import Project, Duo, DuoMember, User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

def _format_project_response(p: Project) -> ProjectResponse:
    checks = {}
    if p.required_checks:
        try:
            checks = json.loads(p.required_checks)
        except Exception:
            checks = {}

    return ProjectResponse(
        id=p.id,
        duo_id=p.duo_id,
        user_id=p.user_id,
        project_name=p.project_name,
        description=p.description,
        github_repo_owner=p.github_repo_owner,
        github_repo_name=p.github_repo_name,
        github_repo_full_name=p.github_repo_full_name,
        github_repo_id=p.github_repo_id,
        branch=p.branch,
        assigned_area=p.assigned_area,
        verification_enabled=p.verification_enabled,
        required_checks=checks,
        created_at=p.created_at,
        updated_at=p.updated_at
    )

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user belongs to a duo
    mem_res = await db.execute(
        select(DuoMember, Duo)
        .join(Duo, DuoMember.duo_id == Duo.id)
        .where(DuoMember.user_id == current_user.id)
    )
    record = mem_res.first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be a member of a Duo to configure a project."
        )
    membership, duo = record

    repo_full = f"{data.github_repo_owner.strip()}/{data.github_repo_name.strip()}".lower()
    checks_str = json.dumps(data.required_checks or {"ci": True, "build": True, "tests": True, "lint": False})
    now = datetime.now(timezone.utc)

    # In SHARED mode, project can be tied to duo (or user assigned area)
    # Check if a project already exists for this user / duo
    if duo.project_mode == "SHARED":
        existing_res = await db.execute(
            select(Project).where(
                and_(
                    Project.duo_id == duo.id,
                    (Project.user_id == current_user.id) | (Project.user_id == None)
                )
            )
        )
    else:
        existing_res = await db.execute(
            select(Project).where(
                and_(
                    Project.duo_id == duo.id,
                    Project.user_id == current_user.id
                )
            )
        )
    existing_proj = existing_res.scalar_one_or_none()

    if existing_proj:
        # Update existing
        existing_proj.project_name = data.project_name
        existing_proj.description = data.description
        existing_proj.github_repo_owner = data.github_repo_owner.strip()
        existing_proj.github_repo_name = data.github_repo_name.strip()
        existing_proj.github_repo_full_name = repo_full
        existing_proj.branch = data.branch.strip()
        existing_proj.assigned_area = data.assigned_area
        existing_proj.verification_enabled = data.verification_enabled
        existing_proj.required_checks = checks_str
        existing_proj.updated_at = now
        await db.commit()
        await db.refresh(existing_proj)
        return _format_project_response(existing_proj)

    # Create new project
    proj = Project(
        duo_id=duo.id,
        user_id=current_user.id,
        project_name=data.project_name,
        description=data.description,
        github_repo_owner=data.github_repo_owner.strip(),
        github_repo_name=data.github_repo_name.strip(),
        github_repo_full_name=repo_full,
        branch=data.branch.strip(),
        assigned_area=data.assigned_area,
        verification_enabled=data.verification_enabled,
        required_checks=checks_str,
        created_at=now,
        updated_at=now
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)

    return _format_project_response(proj)

@router.get("/my", response_model=Optional[ProjectResponse])
async def get_my_project(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    mem_res = await db.execute(
        select(DuoMember).where(DuoMember.user_id == current_user.id)
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        return None

    res = await db.execute(
        select(Project).where(
            and_(
                Project.duo_id == membership.duo_id,
                (Project.user_id == current_user.id) | (Project.user_id == None)
            )
        )
    )
    proj = res.scalar_one_or_none()
    if not proj:
        return None
    return _format_project_response(proj)

@router.get("/duo/{duo_id}", response_model=List[ProjectResponse])
async def get_duo_projects(
    duo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify current user belongs to this duo
    mem_res = await db.execute(
        select(DuoMember).where(
            and_(
                DuoMember.duo_id == duo_id,
                DuoMember.user_id == current_user.id
            )
        )
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    res = await db.execute(
        select(Project).where(Project.duo_id == duo_id)
    )
    projects = res.scalars().all()
    return [_format_project_response(p) for p in projects]

@router.put("/{id}", response_model=ProjectResponse)
async def update_project(
    id: str,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    proj_res = await db.execute(select(Project).where(Project.id == id))
    proj = proj_res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify authorization
    mem_res = await db.execute(
        select(DuoMember).where(
            and_(
                DuoMember.duo_id == proj.duo_id,
                DuoMember.user_id == current_user.id
            )
        )
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    if data.project_name is not None:
        proj.project_name = data.project_name
    if data.description is not None:
        proj.description = data.description
    if data.branch is not None:
        proj.branch = data.branch
    if data.assigned_area is not None:
        proj.assigned_area = data.assigned_area
    if data.verification_enabled is not None:
        proj.verification_enabled = data.verification_enabled
    if data.required_checks is not None:
        proj.required_checks = json.dumps(data.required_checks)

    proj.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(proj)
    return _format_project_response(proj)
