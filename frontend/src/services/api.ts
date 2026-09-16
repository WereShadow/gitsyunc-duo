import {
  User,
  Duo,
  Project,
  DailyTask,
  TodayProgress,
  CalendarHistory,
  GitHubActivity,
  StreakData,
  AppNotification,
  TaskReview
} from '../types';

const API_BASE = '/api';

class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('gitsync_token');
  }

  public setToken(token: string) {
    localStorage.setItem('gitsync_token', token);
  }

  public removeToken() {
    localStorage.removeItem('gitsync_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Network error occurred' }));
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async register(data: { email: string; password: str; full_name: string }) {
    const res = await this.request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    return res;
  }

  async login(data: { email: string; password: str }) {
    const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // Duos
  async createDuo(data: {
    name: string;
    project_mode: 'SEPARATE' | 'SHARED';
    workflow_type?: string;
    timezone: string;
    deadline_time: string;
    grace_period_minutes: number;
  }): Promise<Duo> {
    return this.request<Duo>('/duos', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async joinDuo(invite_code: string): Promise<Duo> {
    return this.request<Duo>('/duos/join', {
      method: 'POST',
      body: JSON.stringify({ invite_code }),
    });
  }

  async getCurrentDuo(): Promise<Duo> {
    return this.request<Duo>('/duos/current');
  }

  async getDuoById(id: string): Promise<Duo> {
    return this.request<Duo>(`/duos/${id}`);
  }

  async updateDuoSettings(id: string, data: Partial<Duo>): Promise<Duo> {
    return this.request<Duo>(`/duos/${id}/settings`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Projects
  async createOrUpdateProject(data: Partial<Project>): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMyProject(): Promise<Project | null> {
    return this.request<Project | null>('/projects/my');
  }

  async getDuoProjects(duoId: string): Promise<Project[]> {
    return this.request<Project[]>(`/projects/duo/${duoId}`);
  }

  // Tasks
  async createDailyTask(data: {
    title: string;
    description?: string;
    user_a_task?: string;
    user_b_task?: string;
    github_requirement?: string;
    min_commits_required?: number;
    date?: string;
  }): Promise<DailyTask> {
    return this.request<DailyTask>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTodayTask(): Promise<DailyTask | null> {
    return this.request<DailyTask | null>('/tasks/today');
  }

  async getTaskHistory(): Promise<DailyTask[]> {
    return this.request<DailyTask[]>('/tasks/history');
  }

  async getTaskById(id: string): Promise<DailyTask> {
    return this.request<DailyTask>(`/tasks/${id}`);
  }

  async submitTask(id: string) {
    return this.request<{ success: boolean; submission_status: string }>(`/tasks/${id}/submit`, {
      method: 'POST',
    });
  }

  async verifyProject(id: string) {
    return this.request<{ success: boolean; overall_status: string }>(`/tasks/${id}/verify-project`, {
      method: 'POST',
    });
  }

  // Reviews
  async submitReview(taskId: string, data: { status: 'APPROVED' | 'CHANGES_REQUESTED'; comment: string; commit_sha?: string }): Promise<TaskReview> {
    return this.request<TaskReview>(`/tasks/${taskId}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTaskReviews(taskId: string): Promise<TaskReview[]> {
    return this.request<TaskReview[]>(`/tasks/${taskId}/reviews`);
  }

  // GitHub
  async getGitHubStatus() {
    return this.request<{ connected: boolean; github_username?: string; scopes?: string }>('/github/status');
  }

  async connectGitHubToken(data: { github_username: string; access_token: string }) {
    return this.request<{ connected: boolean; github_username: string }>('/github/connect-token', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getGitHubRepositories() {
    return this.request<any[]>('/github/repositories');
  }

  async getGitHubActivity(targetUserId?: string): Promise<GitHubActivity> {
    const q = targetUserId ? `?target_user_id=${targetUserId}` : '';
    return this.request<GitHubActivity>(`/github/activity${q}`);
  }

  async verifyGitHub() {
    return this.request<{ task_id: string; daily_status: string; completed: boolean }>('/github/verify', {
      method: 'POST',
    });
  }

  async simulatePush(data: {
    repository_full_name: string;
    branch: string;
    commit_message: string;
    commit_sha?: string;
    author_username?: string;
    files_changed?: string[];
    target_user_id?: string;
  }) {
    return this.request<{ success: boolean; message: string; task_status: string }>('/github/simulate-push', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Progress & Calendar
  async getTodayProgress(): Promise<TodayProgress> {
    return this.request<TodayProgress>('/progress/today');
  }

  async getCalendarHistory(): Promise<CalendarHistory> {
    return this.request<CalendarHistory>('/progress/history');
  }

  // Streaks
  async getStreak(): Promise<StreakData> {
    return this.request<StreakData>('/streaks');
  }

  // Notifications
  async getNotifications(): Promise<AppNotification[]> {
    return this.request<AppNotification[]>('/notifications');
  }

  async markNotificationRead(id: string) {
    return this.request<{ success: boolean }>(`/notifications/${id}/read`, {
      method: 'PUT',
    });
  }

  async markAllNotificationsRead() {
    return this.request<{ success: boolean }>('/notifications/read-all', {
      method: 'POST',
    });
  }
}

type str = string;

export const api = new ApiClient();
