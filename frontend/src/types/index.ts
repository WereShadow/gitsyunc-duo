export interface User {
  id: str;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  created_at: string;
  github_connected: boolean;
  github_username?: string | null;
  current_duo_id?: string | null;
}

export type str = string;

export interface DuoMember {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  github_username?: string | null;
  role: 'CREATOR' | 'PARTNER';
  joined_at: string;
}

export interface StreakData {
  current_streak: number;
  longest_streak: number;
  completed_days: number;
  missed_days: number;
  last_completed_date?: string | null;
  updated_at?: string | null;
}

export interface Duo {
  id: string;
  name: string;
  invite_code: string;
  created_by: string;
  timezone: string;
  deadline_time: string;
  grace_period_minutes: number;
  project_mode: 'SEPARATE' | 'SHARED';
  workflow_type: 'SAME_BRANCH' | 'SEPARATE_BRANCHES' | 'PULL_REQUESTS';
  created_at: string;
  members: DuoMember[];
  streak?: StreakData | null;
}

export interface Project {
  id: string;
  duo_id: string;
  user_id?: string | null;
  project_name: string;
  description?: string | null;
  github_repo_owner: string;
  github_repo_name: string;
  github_repo_full_name: string;
  branch: string;
  assigned_area?: string | null;
  verification_enabled: boolean;
  required_checks: Record<string, boolean>;
  created_at: string;
  updated_at: string;
}

export interface UserTaskProgress {
  user_id: string;
  user_name: string;
  user_email: string;
  avatar_url?: string | null;
  github_username?: string | null;
  assigned_task?: string | null;
  github_verified: boolean;
  commit_count: number;
  latest_commit_sha?: string | null;
  latest_commit_message?: string | null;
  latest_commit_url?: string | null;
  latest_commit_time?: string | null;
  changed_files: string[];
  pull_request_url?: string | null;
  submission_status: 'PENDING' | 'IN_PROGRESS' | 'SUBMITTED' | 'CHANGES_REQUESTED' | 'APPROVED';
  review_status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'CHANGES_REQUESTED';
  submitted_at?: string | null;
  approved_at?: string | null;
  verified_at?: string | null;
}

export interface ProjectVerification {
  id: string;
  repository: string;
  commit_sha?: string | null;
  build_status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'PENDING';
  test_status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'PENDING';
  lint_status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'PENDING';
  ci_status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'PENDING';
  overall_status: 'PASSED' | 'FAILED' | 'PENDING';
  details?: Record<string, any>;
  checked_at: string;
}

export interface TaskReview {
  id: string;
  daily_task_id: string;
  task_owner_id: string;
  task_owner_name?: string | null;
  reviewer_id: string;
  reviewer_name: string;
  status: 'APPROVED' | 'CHANGES_REQUESTED';
  comment: string;
  commit_sha?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DailyTask {
  id: string;
  duo_id: string;
  date: string;
  title: string;
  description?: string | null;
  user_a_task?: string | null;
  user_b_task?: string | null;
  github_requirement: string;
  min_commits_required: number;
  deadline_utc: string;
  status: 'ACTIVE' | 'WAITING_FOR_USER_A' | 'WAITING_FOR_USER_B' | 'WAITING_FOR_REVIEW' | 'COMPLETED' | 'MISSED' | 'CHANGES_REQUESTED';
  created_at: string;
  updated_at: string;
  user_progress: UserTaskProgress[];
  reviews: TaskReview[];
  verifications: ProjectVerification[];
}

export interface TodayProgress {
  task_id?: string | null;
  duo_id: string;
  date: string;
  status: string;
  deadline_utc?: string | null;
  grace_period_minutes: number;
  is_expired: boolean;
  title?: string | null;
  description?: string | null;
  current_user_progress?: UserTaskProgress | null;
  partner_user_progress?: UserTaskProgress | null;
  project_verification?: ProjectVerification | null;
  can_submit: boolean;
  can_review: boolean;
  project_mode: 'SEPARATE' | 'SHARED';
}

export interface CalendarDayItem {
  date: string;
  status: 'COMPLETED' | 'PARTIAL' | 'MISSED' | 'FUTURE' | 'NO_TASK';
  task_id?: string | null;
  task_title?: string | null;
  both_completed: boolean;
  user_a_verified: boolean;
  user_b_verified: boolean;
  user_a_name?: string | null;
  user_b_name?: string | null;
  completed_at?: string | null;
}

export interface CalendarHistory {
  duo_id: string;
  days: CalendarDayItem[];
  current_streak: number;
  longest_streak: number;
  total_completed: number;
  total_missed: number;
}

export interface GitHubActivity {
  user_id: string;
  github_username: string;
  repository?: string | null;
  branch?: string | null;
  today_commits: {
    sha: string;
    message: string;
    author_name: string;
    author_username?: string | null;
    date: string;
    url: string;
    files_changed: string[];
  }[];
  total_today_commits: number;
  pushes_count: number;
  verification_status: boolean;
  last_activity_at?: string | null;
}

export interface AppNotification {
  id: string;
  user_id: string;
  duo_id?: string | null;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}
