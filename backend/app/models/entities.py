import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    github_account: Mapped[Optional["GitHubAccount"]] = relationship("GitHubAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")
    duo_memberships: Mapped[List["DuoMember"]] = relationship("DuoMember", back_populates="user", cascade="all, delete-orphan")
    daily_progress: Mapped[List["DailyUserProgress"]] = relationship("DailyUserProgress", back_populates="user")
    reviews_given: Mapped[List["TaskReview"]] = relationship("TaskReview", foreign_keys="TaskReview.reviewer_id", back_populates="reviewer")
    reviews_received: Mapped[List["TaskReview"]] = relationship("TaskReview", foreign_keys="TaskReview.task_owner_id", back_populates="task_owner")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class GitHubAccount(Base):
    __tablename__ = "github_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    github_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_username: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="github_account")


class Duo(Base):
    __tablename__ = "duos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default="Asia/Kolkata", nullable=False)
    deadline_time: Mapped[str] = mapped_column(String(10), default="23:59", nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    project_mode: Mapped[str] = mapped_column(String(50), default="SEPARATE", nullable=False)  # SEPARATE or SHARED
    workflow_type: Mapped[str] = mapped_column(String(50), default="SEPARATE_BRANCHES", nullable=False)  # SAME_BRANCH, SEPARATE_BRANCHES, PULL_REQUESTS
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    members: Mapped[List["DuoMember"]] = relationship("DuoMember", back_populates="duo", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="duo", cascade="all, delete-orphan")
    daily_tasks: Mapped[List["DailyTask"]] = relationship("DailyTask", back_populates="duo", cascade="all, delete-orphan")
    streak: Mapped[Optional["Streak"]] = relationship("Streak", back_populates="duo", uselist=False, cascade="all, delete-orphan")


class DuoMember(Base):
    __tablename__ = "duo_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    duo_id: Mapped[str] = mapped_column(String(36), ForeignKey("duos.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="PARTNER", nullable=False)  # CREATOR, PARTNER
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("duo_id", "user_id", name="uq_duo_member"),
    )

    duo: Mapped["Duo"] = relationship("Duo", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="duo_memberships")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    duo_id: Mapped[str] = mapped_column(String(36), ForeignKey("duos.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_repo_owner: Mapped[str] = mapped_column(String(150), nullable=False)
    github_repo_name: Mapped[str] = mapped_column(String(150), nullable=False)
    github_repo_full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    github_repo_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    branch: Mapped[str] = mapped_column(String(150), default="main", nullable=False)
    assigned_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # e.g., "Backend / FastAPI"
    verification_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    required_checks: Mapped[str] = mapped_column(Text, default='{"ci": true, "build": true, "tests": true, "lint": false}', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    duo: Mapped["Duo"] = relationship("Duo", back_populates="projects")
    user: Mapped[Optional["User"]] = relationship("User")
    milestones: Mapped[List["ProjectMilestone"]] = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[List["ProjectTask"]] = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    activity_logs: Mapped[List["TaskActivityLog"]] = relationship("TaskActivityLog", back_populates="project", cascade="all, delete-orphan")


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    duo_id: Mapped[str] = mapped_column(String(36), ForeignKey("duos.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_a_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_b_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_requirement: Mapped[str] = mapped_column(String(100), default="1 commit", nullable=False)
    min_commits_required: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    deadline_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, WAITING_FOR_USER_A, WAITING_FOR_USER_B, WAITING_FOR_REVIEW, COMPLETED, MISSED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("duo_id", "date", name="uq_duo_date"),
    )

    duo: Mapped["Duo"] = relationship("Duo", back_populates="daily_tasks")
    user_progress: Mapped[List["DailyUserProgress"]] = relationship("DailyUserProgress", back_populates="daily_task", cascade="all, delete-orphan")
    reviews: Mapped[List["TaskReview"]] = relationship("TaskReview", back_populates="daily_task", cascade="all, delete-orphan")
    verifications: Mapped[List["ProjectVerification"]] = relationship("ProjectVerification", back_populates="daily_task", cascade="all, delete-orphan")


class DailyUserProgress(Base):
    __tablename__ = "daily_user_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    daily_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("daily_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    github_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    commit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latest_commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latest_commit_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latest_commit_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latest_commit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    changed_files: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    pull_request_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    submission_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, IN_PROGRESS, SUBMITTED, CHANGES_REQUESTED, APPROVED
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, UNDER_REVIEW, APPROVED, CHANGES_REQUESTED
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("daily_task_id", "user_id", name="uq_task_user_progress"),
    )

    daily_task: Mapped["DailyTask"] = relationship("DailyTask", back_populates="user_progress")
    user: Mapped["User"] = relationship("User", back_populates="daily_progress")


class TaskReview(Base):
    __tablename__ = "task_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    daily_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("daily_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    task_owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVED, CHANGES_REQUESTED
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    daily_task: Mapped["DailyTask"] = relationship("DailyTask", back_populates="reviews")
    task_owner: Mapped["User"] = relationship("User", foreign_keys=[task_owner_id], back_populates="reviews_received")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")


class ProjectVerification(Base):
    __tablename__ = "project_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    daily_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("daily_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    repository: Mapped[str] = mapped_column(String(300), nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    build_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PASSED, FAILED, SKIPPED, PENDING
    test_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)   # PASSED, FAILED, SKIPPED, PENDING
    lint_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)   # PASSED, FAILED, SKIPPED, PENDING
    ci_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)     # PASSED, FAILED, SKIPPED, PENDING
    overall_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PASSED, FAILED, PENDING
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON details
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    daily_task: Mapped["DailyTask"] = relationship("DailyTask", back_populates="verifications")


class Streak(Base):
    __tablename__ = "streaks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    duo_id: Mapped[str] = mapped_column(String(36), ForeignKey("duos.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missed_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_completed_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    duo: Mapped["Duo"] = relationship("Duo", back_populates="streak")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    duo_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("duos.id", ondelete="CASCADE"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # REMINDER, PARTNER_COMPLETED, DEADLINE_WARNING, STREAK_WARNING, REVIEW_REQUESTED, CHANGES_REQUESTED, TASK_APPROVED, DAY_COMPLETED
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    delivery_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PROCESSED", nullable=False)  # PROCESSED, IGNORED, FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)  # OPEN, COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="milestones")
    tasks: Mapped[List["ProjectTask"]] = relationship("ProjectTask", back_populates="milestone")


class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    milestone_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True)
    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, URGENT
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="BACKLOG", index=True, nullable=False)
    # BACKLOG, TODO, IN_PROGRESS, SUBMITTED, UNDER_REVIEW, CHANGES_REQUESTED, APPROVED, COMPLETED

    # GitHub Evidence & Verification Fields
    github_repo: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    pull_request_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pull_request_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latest_commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latest_commit_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_files: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of file paths
    
    # Verification & CI
    verification_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, PASSED, FAILED, SKIPPED
    verification_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON check summary

    # Submission & Completion tracking
    submission_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    milestone: Mapped[Optional["ProjectMilestone"]] = relationship("ProjectMilestone", back_populates="tasks")
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])
    
    dependencies: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    dependents: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan"
    )
    comments: Mapped[List["TaskComment"]] = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    reviews: Mapped[List["TaskReviewLog"]] = relationship("TaskReviewLog", back_populates="task", cascade="all, delete-orphan")
    activity_logs: Mapped[List["TaskActivityLog"]] = relationship("TaskActivityLog", back_populates="task", cascade="all, delete-orphan")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    depends_on_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
    )

    task: Mapped["ProjectTask"] = relationship("ProjectTask", foreign_keys=[task_id], back_populates="dependencies")
    depends_on_task: Mapped["ProjectTask"] = relationship("ProjectTask", foreign_keys=[depends_on_task_id], back_populates="dependents")


class TaskReviewLog(Base):
    __tablename__ = "project_task_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVED, CHANGES_REQUESTED
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    task: Mapped["ProjectTask"] = relationship("ProjectTask", back_populates="reviews")
    reviewer: Mapped["User"] = relationship("User")


class TaskComment(Base):
    __tablename__ = "project_task_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    task: Mapped["ProjectTask"] = relationship("ProjectTask", back_populates="comments")
    user: Mapped["User"] = relationship("User")


class TaskActivityLog(Base):
    __tablename__ = "project_activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "TASK_CREATED", "TASK_SUBMITTED", "CHANGES_REQUESTED", "TASK_APPROVED", "TASK_COMPLETED", "GITHUB_COMMITS_VERIFIED"
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="activity_logs")
    task: Mapped[Optional["ProjectTask"]] = relationship("ProjectTask", back_populates="activity_logs")
    user: Mapped[Optional["User"]] = relationship("User")
