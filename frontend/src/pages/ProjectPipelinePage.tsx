import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderKanban, Plus, RefreshCw, GitCommit, GitPullRequest, CheckCircle2,
  XCircle, Clock, AlertTriangle, Lock, Eye,
  Activity, AlertCircle, ExternalLink,
  User, Check, X
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { ProjectTaskItem, ProjectDashboardData, Project } from '../types';

type TaskStatus =
  | 'TODO' | 'IN_PROGRESS' | 'UNDER_REVIEW' | 'CHANGES_REQUESTED'
  | 'APPROVED' | 'COMPLETED' | 'BACKLOG';

interface SubmitData {
  github_repo?: string;
  branch?: string;
  pull_request_url?: string;
  pull_request_number?: number;
  commit_sha?: string;
  commit_message?: string;
  submission_notes?: string;
}

interface CreateData {
  title: string;
  description?: string;
  assignee_id?: string;
  priority: string;
  deadline?: string;
  github_repo?: string;
  branch?: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  BACKLOG:           { label: 'Backlog',           color: 'text-zinc-400',    dot: 'bg-zinc-500' },
  TODO:              { label: 'To Do',              color: 'text-blue-300',    dot: 'bg-blue-400' },
  IN_PROGRESS:       { label: 'In Progress',        color: 'text-yellow-300',  dot: 'bg-yellow-400' },
  UNDER_REVIEW:      { label: 'Under Review',       color: 'text-purple-300',  dot: 'bg-purple-400' },
  CHANGES_REQUESTED: { label: 'Changes Requested',  color: 'text-orange-300',  dot: 'bg-orange-400' },
  APPROVED:          { label: 'Approved',            color: 'text-emerald-300', dot: 'bg-emerald-400' },
  COMPLETED:         { label: 'Completed',           color: 'text-emerald-400', dot: 'bg-emerald-500' },
};

const PRIORITY_COLOR: Record<string, string> = {
  LOW: 'text-zinc-400 border-zinc-600',
  MEDIUM: 'text-blue-300 border-blue-700',
  HIGH: 'text-orange-300 border-orange-700',
  URGENT: 'text-red-300 border-red-700',
};

const HEALTH_CONFIG: Record<string, { label: string; color: string }> = {
  ON_TRACK: { label: 'On Track',   color: 'bg-emerald-900/40 border-emerald-700 text-emerald-300' },
  AT_RISK:  { label: 'At Risk',    color: 'bg-yellow-900/40 border-yellow-700 text-yellow-300'   },
  DELAYED:  { label: 'Delayed',    color: 'bg-red-900/40 border-red-700 text-red-300'            },
};

const KANBAN_COLUMNS: TaskStatus[] = [
  'TODO', 'IN_PROGRESS', 'UNDER_REVIEW', 'CHANGES_REQUESTED', 'COMPLETED'
];

interface TaskCardProps {
  task: ProjectTaskItem;
  currentUserId?: string;
  onSubmit: (task: ProjectTaskItem) => void;
  onReview: (task: ProjectTaskItem) => void;
  onStatusChange: (task: ProjectTaskItem, newStatus: string) => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, currentUserId, onSubmit, onReview, onStatusChange }) => {
  const isMyTask = task.assignee_id === currentUserId;
  const canSubmit = isMyTask && ['TODO', 'IN_PROGRESS', 'CHANGES_REQUESTED'].includes(task.status) && !task.is_blocked;
  const canReview = !isMyTask && task.assignee_id !== undefined && ['UNDER_REVIEW'].includes(task.status);
  const isOverdue = !!(task.deadline && new Date(task.deadline) < new Date() && task.status !== 'COMPLETED');

  const verifyIcon = task.verification_status === 'PASSED'
    ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
    : task.verification_status === 'FAILED'
    ? <XCircle className="w-3.5 h-3.5 text-red-400" />
    : <Clock className="w-3.5 h-3.5 text-zinc-500" />;

  return (
    <div className={`bg-[#161b22] border rounded-xl p-3 space-y-2 transition-all hover:border-zinc-600 ${
      task.is_blocked ? 'border-orange-800/50 opacity-75' : 'border-[#30363d]'
    }`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold text-zinc-100 leading-tight line-clamp-2 flex-1">{task.title}</p>
        <span className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded border ${PRIORITY_COLOR[task.priority] || PRIORITY_COLOR.MEDIUM}`}>
          {task.priority}
        </span>
      </div>

      {task.is_blocked && (
        <div className="flex items-center gap-1 text-[10px] text-orange-400 font-medium">
          <Lock className="w-3 h-3" />
          <span>Blocked</span>
          {task.blocked_by.length > 0 && (
            <span className="text-zinc-600 truncate">
              {' '}by: {task.blocked_by.filter(b => b.is_blocking).map(b => b.depends_on_title).join(', ')}
            </span>
          )}
        </div>
      )}

      {isOverdue && (
        <div className="flex items-center gap-1 text-[10px] text-red-400 font-medium">
          <AlertCircle className="w-3 h-3" />
          <span>Overdue</span>
        </div>
      )}

      <div className="flex items-center justify-between text-[10px] text-zinc-500">
        <div className="flex items-center gap-1.5">
          <User className="w-3 h-3" />
          <span>{task.assignee_name || 'Unassigned'}</span>
        </div>
        <div className="flex items-center gap-1">
          {verifyIcon}
          <span className="text-[9px]">{task.verification_status}</span>
        </div>
      </div>

      {task.latest_commit_sha && (
        <div className="flex items-center gap-1 text-[10px] text-zinc-500">
          <GitCommit className="w-3 h-3" />
          <span className="font-mono">{task.latest_commit_sha.slice(0, 7)}</span>
          {task.submission_count > 0 && (
            <span className="ml-1 text-zinc-600">#{task.submission_count}</span>
          )}
        </div>
      )}

      {task.pull_request_url && (
        <a href={task.pull_request_url} target="_blank" rel="noreferrer"
          className="flex items-center gap-1 text-[10px] text-blue-400 hover:underline">
          <GitPullRequest className="w-3 h-3" />
          <span>PR #{task.pull_request_number}</span>
          <ExternalLink className="w-2.5 h-2.5" />
        </a>
      )}

      <div className="flex gap-1.5 pt-1">
        {canSubmit && (
          <button
            onClick={() => onSubmit(task)}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-[10px] font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
          >
            <GitCommit className="w-3 h-3" />
            Submit Work
          </button>
        )}
        {canReview && (
          <button
            onClick={() => onReview(task)}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-[10px] font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
          >
            <Eye className="w-3 h-3" />
            Review
          </button>
        )}
        {!canSubmit && !canReview && ['TODO', 'IN_PROGRESS'].includes(task.status) && isMyTask && !task.is_blocked && (
          <button
            onClick={() => onStatusChange(task, task.status === 'TODO' ? 'IN_PROGRESS' : 'TODO')}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-[10px] font-semibold bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors"
          >
            {task.status === 'TODO' ? 'Start' : 'Pause'}
          </button>
        )}
      </div>
    </div>
  );
};

const SubmitModal: React.FC<{ task: ProjectTaskItem; onClose: () => void; onSubmitted: () => void }> = ({ task, onClose, onSubmitted }) => {
  const [data, setData] = useState<SubmitData>({
    github_repo: task.github_repo || '',
    branch: task.branch || '',
    commit_sha: '',
    commit_message: '',
    pull_request_url: task.pull_request_url || '',
    submission_notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      await api.submitTaskEvidence(task.id, data);
      onSubmitted();
    } catch (e: any) {
      setError(e?.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-2xl shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-zinc-100">Submit Work Evidence</h3>
            <p className="text-[11px] text-zinc-400 mt-0.5 line-clamp-1">{task.title}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-zinc-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        <div className="space-y-3">
          {([
            { label: 'GitHub Repo', key: 'github_repo' as keyof SubmitData, placeholder: 'owner/repo' },
            { label: 'Branch', key: 'branch' as keyof SubmitData, placeholder: 'feature/my-work' },
            { label: 'Commit SHA', key: 'commit_sha' as keyof SubmitData, placeholder: 'abc1234...' },
            { label: 'Commit Message', key: 'commit_message' as keyof SubmitData, placeholder: 'feat: implement...' },
            { label: 'Pull Request URL', key: 'pull_request_url' as keyof SubmitData, placeholder: 'https://github.com/...' },
          ]).map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">{label}</label>
              <input
                type="text"
                placeholder={placeholder}
                value={(data[key] as string) || ''}
                onChange={e => setData(d => ({ ...d, [key]: e.target.value }))}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
              />
            </div>
          ))}
          <div>
            <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Notes</label>
            <textarea
              placeholder="Describe what you implemented..."
              value={data.submission_notes || ''}
              onChange={e => setData(d => ({ ...d, submission_notes: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-2 bg-red-900/30 border border-red-800 rounded-lg">
            <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
            <p className="text-[11px] text-red-300">{error}</p>
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors">Cancel</button>
          <button onClick={handleSubmit} disabled={submitting}
            className="flex-1 px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition-colors">
            {submitting ? 'Submitting...' : 'Submit for Review'}
          </button>
        </div>
      </div>
    </div>
  );
};

const ReviewModal: React.FC<{ task: ProjectTaskItem; onClose: () => void; onReviewed: () => void }> = ({ task, onClose, onReviewed }) => {
  const [verdict, setVerdict] = useState<'APPROVED' | 'CHANGES_REQUESTED'>('APPROVED');
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!comment.trim()) { setError('A comment is required.'); return; }
    setSubmitting(true);
    setError('');
    try {
      await api.reviewProjectTask(task.id, { status: verdict, comment: comment.trim() });
      onReviewed();
    } catch (e: any) {
      setError(e?.message || 'Review failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-2xl shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-zinc-100">Peer Review</h3>
            <p className="text-[11px] text-zinc-400 mt-0.5 line-clamp-1">{task.title}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-zinc-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        {(task.latest_commit_sha || task.branch || task.pull_request_url) && (
          <div className="p-3 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-1.5">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Submitted Evidence</p>
            {task.branch && (
              <div className="flex items-center gap-1.5 text-[11px] text-zinc-300">
                <GitCommit className="w-3 h-3 text-zinc-500" />
                <span className="font-mono">{task.branch}</span>
              </div>
            )}
            {task.latest_commit_sha && (
              <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                <span className="font-mono text-emerald-400">{task.latest_commit_sha.slice(0, 7)}</span>
                <span className="truncate">{task.latest_commit_message}</span>
              </div>
            )}
            {task.pull_request_url && (
              <a href={task.pull_request_url} target="_blank" rel="noreferrer"
                className="flex items-center gap-1.5 text-[11px] text-blue-400 hover:underline">
                <GitPullRequest className="w-3 h-3" />
                <span>PR #{task.pull_request_number}</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}
            {task.submission_notes && (
              <p className="text-[11px] text-zinc-500 italic">"{task.submission_notes}"</p>
            )}
            <p className="text-[9px] text-zinc-600">Verification: {task.verification_status} | Submission #{task.submission_count}</p>
          </div>
        )}

        <div className="flex gap-2">
          {(['APPROVED', 'CHANGES_REQUESTED'] as const).map(v => (
            <button key={v} onClick={() => setVerdict(v)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] font-semibold rounded-lg border transition-all ${
                verdict === v
                  ? v === 'APPROVED' ? 'bg-emerald-600 border-emerald-500 text-white' : 'bg-orange-700 border-orange-600 text-white'
                  : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:border-zinc-500'
              }`}>
              {v === 'APPROVED' ? <Check className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
              {v === 'APPROVED' ? 'Approve' : 'Request Changes'}
            </button>
          ))}
        </div>

        <div>
          <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Comment *</label>
          <textarea
            placeholder="LGTM! / Please address..."
            value={comment}
            onChange={e => { setComment(e.target.value); setError(''); }}
            rows={3}
            className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 p-2 bg-red-900/30 border border-red-800 rounded-lg">
            <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
            <p className="text-[11px] text-red-300">{error}</p>
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors">Cancel</button>
          <button onClick={handleSubmit} disabled={submitting}
            className={`flex-1 px-4 py-2 text-xs font-semibold disabled:opacity-50 text-white rounded-lg transition-colors ${
              verdict === 'APPROVED' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-orange-700 hover:bg-orange-600'
            }`}>
            {submitting ? 'Submitting...' : verdict === 'APPROVED' ? 'Approve & Complete' : 'Request Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

const CreateTaskModal: React.FC<{
  projectId: string;
  members: { user_id: string; full_name: string }[];
  onClose: () => void;
  onCreated: () => void;
}> = ({ projectId, members, onClose, onCreated }) => {
  const [data, setData] = useState<CreateData>({ title: '', priority: 'MEDIUM' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    if (!data.title.trim()) { setError('Title is required.'); return; }
    setSubmitting(true);
    setError('');
    try {
      await api.createProjectTask(projectId, {
        title: data.title.trim(),
        description: data.description,
        assignee_id: data.assignee_id,
        priority: data.priority,
        deadline: data.deadline,
        github_repo: data.github_repo,
        branch: data.branch,
      });
      onCreated();
    } catch (e: any) {
      setError(e?.message || 'Failed to create task');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-2xl shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-zinc-100">Create Task</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-zinc-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Title *</label>
            <input type="text" placeholder="What needs to be done?"
              value={data.title}
              onChange={e => { setData(d => ({ ...d, title: e.target.value })); setError(''); }}
              className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Description</label>
            <textarea placeholder="Acceptance criteria, context..."
              value={data.description || ''}
              onChange={e => setData(d => ({ ...d, description: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500 resize-none" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Assign To</label>
              <select value={data.assignee_id || ''}
                onChange={e => setData(d => ({ ...d, assignee_id: e.target.value || undefined }))}
                className="w-full px-2 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 focus:outline-none focus:border-blue-500">
                <option value="">Unassigned</option>
                {members.map(m => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Priority</label>
              <select value={data.priority}
                onChange={e => setData(d => ({ ...d, priority: e.target.value }))}
                className="w-full px-2 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 focus:outline-none focus:border-blue-500">
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">Deadline</label>
              <input type="date" value={data.deadline || ''}
                onChange={e => setData(d => ({ ...d, deadline: e.target.value || undefined }))}
                className="w-full px-2 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-zinc-400 mb-1 uppercase tracking-wide">GitHub Repo</label>
              <input type="text" placeholder="owner/repo"
                value={data.github_repo || ''}
                onChange={e => setData(d => ({ ...d, github_repo: e.target.value || undefined }))}
                className="w-full px-2 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500" />
            </div>
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-2 p-2 bg-red-900/30 border border-red-800 rounded-lg">
            <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
            <p className="text-[11px] text-red-300">{error}</p>
          </div>
        )}
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors">Cancel</button>
          <button onClick={handleCreate} disabled={submitting}
            className="flex-1 px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition-colors">
            {submitting ? 'Creating...' : 'Create Task'}
          </button>
        </div>
      </div>
    </div>
  );
};

const HealthBanner: React.FC<{ data: ProjectDashboardData }> = ({ data }) => {
  const hc = HEALTH_CONFIG[data.project_health] || HEALTH_CONFIG.ON_TRACK;
  const signals = [
    data.overdue_tasks > 0 && `${data.overdue_tasks} overdue`,
    data.blocked_tasks > 0 && `${data.blocked_tasks} blocked`,
    data.failed_ci_count > 0 && `${data.failed_ci_count} CI failures`,
    data.review_backlog_count > 0 && `${data.review_backlog_count} reviews stale (>48h)`,
    data.at_risk_milestones > 0 && `${data.at_risk_milestones} milestone(s) past deadline`,
  ].filter(Boolean) as string[];

  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border ${hc.color} text-sm`}>
      <span className="font-bold">{hc.label}</span>
      {signals.length > 0 && (
        <span className="text-[11px] opacity-75">â€” {signals.join(', ')}</span>
      )}
      <span className="ml-auto text-xs font-mono font-semibold">{data.completion_percentage}% complete</span>
    </div>
  );
};

interface Props {
  onNavigate?: (tab: string) => void;
}

export const ProjectPipelinePage: React.FC<Props> = ({ onNavigate }) => {
  const { user, duo } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboardData | null>(null);
  const [tasks, setTasks] = useState<ProjectTaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [submitTask, setSubmitTask] = useState<ProjectTaskItem | null>(null);
  const [reviewTask, setReviewTask] = useState<ProjectTaskItem | null>(null);
  const [showCreateTask, setShowCreateTask] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const proj = await api.getMyProject();
      if (!proj) { setLoading(false); return; }
      setProject(proj);
      const [dash, taskList] = await Promise.all([
        api.getProjectDashboard(proj.id),
        api.getProjectTasks(proj.id),
      ]);
      setDashboard(dash);
      setTasks(taskList);
    } catch (e: any) {
      setError(e?.message || 'Failed to load project data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleStatusChange = async (task: ProjectTaskItem, newStatus: string) => {
    try {
      await api.updateTaskStatus(task.id, newStatus);
      await fetchAll();
    } catch (e: any) {
      console.error('Status change failed:', e);
    }
  };

  const members = duo?.members.map(m => ({ user_id: m.user_id, full_name: m.full_name })) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-zinc-700 border-t-blue-500 animate-spin" />
          <p className="text-zinc-500 text-sm">Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <FolderKanban className="w-12 h-12 text-zinc-600" />
        <p className="text-zinc-400 text-sm">No project found for your duo yet.</p>
        <p className="text-zinc-600 text-xs">Set up a project in Settings to get started.</p>
      </div>
    );
  }

  const tasksByStatus = KANBAN_COLUMNS.reduce((acc, col) => {
    acc[col] = tasks.filter(t => t.status === col);
    return acc;
  }, {} as Record<string, ProjectTaskItem[]>);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderKanban className="w-5 h-5 text-blue-400" />
          <div>
            <h1 className="text-base font-bold text-zinc-100">{project.project_name}</h1>
            <p className="text-[11px] text-zinc-500 font-mono">{project.github_repo_full_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchAll} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors">
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button onClick={() => setShowCreateTask(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors">
            <Plus className="w-3.5 h-3.5" />
            New Task
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-800 rounded-xl">
          <XCircle className="w-4 h-4 text-red-400 shrink-0" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {dashboard && <HealthBanner data={dashboard} />}

      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[
            { label: 'Total', value: dashboard.total_tasks, color: 'text-zinc-300' },
            { label: 'Completed', value: dashboard.completed_tasks, color: 'text-emerald-400' },
            { label: 'In Review', value: dashboard.tasks_awaiting_review, color: 'text-purple-400' },
            { label: 'Blocked', value: dashboard.blocked_tasks, color: 'text-orange-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-[#161b22] border border-[#30363d] rounded-xl p-3 text-center">
              <p className={`text-xl font-bold ${color}`}>{value}</p>
              <p className="text-[10px] text-zinc-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="overflow-x-auto pb-4">
        <div className="flex gap-3 min-w-max">
          {KANBAN_COLUMNS.map(col => {
            const cfg = STATUS_CONFIG[col];
            const colTasks = tasksByStatus[col] || [];
            return (
              <div key={col} className="w-64 flex flex-col bg-[#0d1117] border border-[#30363d] rounded-2xl">
                <div className="flex items-center gap-2 p-3">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />
                  <span className={`text-xs font-bold flex-1 ${cfg.color}`}>{cfg.label}</span>
                  <span className="text-[10px] text-zinc-600 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">
                    {colTasks.length}
                  </span>
                </div>
                <div className="flex-1 px-2 pb-2 space-y-2 overflow-y-auto max-h-[65vh]">
                  {colTasks.length === 0 ? (
                    <p className="text-[10px] text-zinc-700 text-center py-4">No tasks</p>
                  ) : (
                    colTasks.map(task => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        currentUserId={user?.id}
                        onSubmit={t => setSubmitTask(t)}
                        onReview={t => setReviewTask(t)}
                        onStatusChange={handleStatusChange}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {dashboard && dashboard.recent_activity.length > 0 && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-zinc-400" />
            <h2 className="text-xs font-bold text-zinc-300">Recent Activity</h2>
          </div>
          <div className="space-y-2">
            {dashboard.recent_activity.slice(0, 10).map(a => (
              <div key={a.id} className="flex items-start gap-2 text-[11px]">
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-600 mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-zinc-400 font-mono">{a.action}</span>
                  {a.task_title && <span className="text-zinc-500"> Â· {a.task_title}</span>}
                  {a.details && <p className="text-zinc-600 truncate">{a.details}</p>}
                  {(a.previous_state || a.new_state) && (
                    <p className="text-[9px] text-zinc-700">{a.previous_state} â†’ {a.new_state}</p>
                  )}
                </div>
                <span className="text-[9px] text-zinc-700 shrink-0">
                  {new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {submitTask && (
        <SubmitModal task={submitTask} onClose={() => setSubmitTask(null)} onSubmitted={() => { setSubmitTask(null); fetchAll(); }} />
      )}
      {reviewTask && (
        <ReviewModal task={reviewTask} onClose={() => setReviewTask(null)} onReviewed={() => { setReviewTask(null); fetchAll(); }} />
      )}
      {showCreateTask && project && (
        <CreateTaskModal
          projectId={project.id}
          members={members}
          onClose={() => setShowCreateTask(false)}
          onCreated={() => { setShowCreateTask(false); fetchAll(); }}
        />
      )}
    </div>
  );
};
