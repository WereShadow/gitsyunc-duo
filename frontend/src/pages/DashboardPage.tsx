import React, { useState, useEffect } from 'react';
import {
  Flame,
  CheckCircle2,
  Clock,
  GitCommit,
  GitPullRequest,
  ShieldCheck,
  Sparkles,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  AlertCircle,
  Play,
  Share2,
  Plus
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  TodayProgress,
  DailyTask,
  UserTaskProgress,
  ProjectDashboardData,
  ProjectTaskItem,
  TaskPriority
} from '../types';
import { PeerReviewModal } from '../components/reviews/PeerReviewModal';
import { FolderKanban, Lock } from 'lucide-react';

interface DashboardPageProps {
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const { user, duo } = useAuth();
  const [progress, setProgress] = useState<TodayProgress | null>(null);
  const [task, setTask] = useState<DailyTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [selectedPartnerProgress, setSelectedPartnerProgress] = useState<UserTaskProgress | null>(null);

  // Project Execution State
  const [activeTabMode, setActiveTabMode] = useState<'PROJECT_PIPELINE' | 'DAILY_HABIT'>('PROJECT_PIPELINE');
  const [projectData, setProjectData] = useState<ProjectDashboardData | null>(null);
  const [selectedTask, setSelectedTask] = useState<ProjectTaskItem | null>(null);

  // Peer review dialog state
  const [isTaskReviewOpen, setIsTaskReviewOpen] = useState(false);
  const [taskReviewStatus, setTaskReviewStatus] = useState<'APPROVED' | 'CHANGES_REQUESTED'>('APPROVED');
  const [taskReviewComment, setTaskReviewComment] = useState('');
  const [taskReviewSubmitting, setTaskReviewSubmitting] = useState(false);

  // Submit task evidence dialog state
  const [isTaskSubmitOpen, setIsTaskSubmitOpen] = useState(false);
  const [submitBranch, setSubmitBranch] = useState('');
  const [submitSha, setSubmitSha] = useState('');
  const [submitMessage, setSubmitMessage] = useState('');
  const [submitNotes, setSubmitNotes] = useState('');
  const [taskSubmittingWork, setTaskSubmittingWork] = useState(false);

  // Create Task dialog state
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState<TaskPriority>('MEDIUM');
  const [newAssigneeId, setNewAssigneeId] = useState('');
  const [newMilestoneId, setNewMilestoneId] = useState('');
  const [isCreatingTask, setIsCreatingTask] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const [progData, taskData, projects] = await Promise.all([
        api.getTodayProgress().catch(() => null),
        api.getTodayTask().catch(() => null),
        api.getProjects().catch(() => []),
      ]);
      setProgress(progData);
      setTask(taskData);

      if (projects && projects.length > 0) {
        const pDash = await api.getProjectDashboard(projects[0].id).catch(() => null);
        setProjectData(pDash);
      }

      // Trigger celebration if day complete
      if (progData?.status === 'COMPLETED') {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 }
        });
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, [user]);

  const handleVerifyNow = async () => {
    setVerifying(true);
    try {
      await api.verifyGitHub();
      await fetchDashboardData();
    } catch (err: any) {
      alert(err.message || 'Verification check failed');
    } finally {
      setVerifying(false);
    }
  };

  const handleSubmitWork = async () => {
    if (!task) return;
    setSubmitting(true);
    try {
      await api.submitTask(task.id);
      await fetchDashboardData();
    } catch (err: any) {
      alert(err.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenReview = (prog: UserTaskProgress) => {
    setSelectedPartnerProgress(prog);
    setIsReviewModalOpen(true);
  };

  // Collaborative Project Action Handlers
  const handleProjectTaskReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !taskReviewComment.trim()) return;

    try {
      setTaskReviewSubmitting(true);
      await api.reviewProjectTask(selectedTask.id, {
        status: taskReviewStatus,
        comment: taskReviewComment.trim(),
        commit_sha: selectedTask.latest_commit_sha || undefined
      });
      setIsTaskReviewOpen(false);
      setTaskReviewComment('');
      setSelectedTask(null);
      await fetchDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to submit review');
    } finally {
      setTaskReviewSubmitting(false);
    }
  };

  const handleProjectTaskEvidenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;

    try {
      setTaskSubmittingWork(true);
      await api.submitTaskEvidence(selectedTask.id, {
        branch: submitBranch.trim() || selectedTask.branch || 'main',
        commit_sha: submitSha.trim() || 'f2b84c1',
        commit_message: submitMessage.trim() || 'feat: completed task requirements',
        submission_notes: submitNotes.trim()
      });
      setIsTaskSubmitOpen(false);
      setSelectedTask(null);
      await fetchDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to submit task evidence');
    } finally {
      setTaskSubmittingWork(false);
    }
  };

  const handleProjectTaskCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectData || !newTitle.trim()) return;

    try {
      setIsCreatingTask(true);
      await api.createProjectTask(projectData.project_id, {
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        priority: newPriority,
        assignee_id: newAssigneeId || undefined,
        milestone_id: newMilestoneId || undefined
      });
      setIsCreateTaskOpen(false);
      setNewTitle('');
      setNewDesc('');
      await fetchDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to create task');
    } finally {
      setIsCreatingTask(false);
    }
  };

  const isCompleted = progress?.status === 'COMPLETED';
  const isShared = duo?.project_mode === 'SHARED';

  const userProg = progress?.current_user_progress;
  const partnerProg = progress?.partner_user_progress;

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-7xl mx-auto animate-in fade-in duration-200">
      {/* View Mode Toggle: Collaborative Project Execution vs Daily Habit */}
      <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTabMode('PROJECT_PIPELINE')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTabMode === 'PROJECT_PIPELINE'
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            <FolderKanban className="w-4 h-4" />
            <span>Project Execution & Pipeline</span>
          </button>
          <button
            onClick={() => setActiveTabMode('DAILY_HABIT')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTabMode === 'DAILY_HABIT'
                ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            <Flame className="w-4 h-4" />
            <span>Daily Duo Streak Habit</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {activeTabMode === 'PROJECT_PIPELINE' && (
            <button
              onClick={() => setIsCreateTaskOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 rounded-lg transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Task</span>
            </button>
          )}
          <button
            onClick={fetchDashboardData}
            className="p-2 text-zinc-400 hover:text-white bg-zinc-900 border border-zinc-800 rounded-lg transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {activeTabMode === 'PROJECT_PIPELINE' && projectData ? (
        <div className="space-y-6">
          {/* Project Platform Banner */}
          <div className="p-6 bg-gradient-to-r from-zinc-900 via-zinc-900 to-zinc-950 rounded-2xl border border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                  Project Execution
                </span>
                <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase ${
                  projectData.project_health === 'ON_TRACK'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                }`}>
                  {projectData.project_health.replace('_', ' ')}
                </span>
              </div>
              <h2 className="text-2xl font-black text-white flex items-center gap-2">
                {projectData.project_name}
                <span className="text-xs font-normal text-zinc-400">({projectData.github_repo_full_name})</span>
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                PLAN → ASSIGN → WORK → SUBMIT → VERIFY → REVIEW → COMPLETE
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="p-3 bg-zinc-950/80 border border-zinc-800 rounded-xl text-center min-w-[100px]">
                <span className="text-[10px] uppercase text-zinc-500 font-bold block">Completion</span>
                <span className="text-lg font-black text-emerald-400">{projectData.completion_percentage}%</span>
              </div>
            </div>
          </div>

          {/* Project KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl">
              <span className="text-[10px] font-bold text-zinc-400 block uppercase">Total Tasks</span>
              <span className="text-xl font-black text-white">{projectData.total_tasks}</span>
              <span className="text-[11px] text-zinc-500 block mt-1">{projectData.completed_tasks} completed</span>
            </div>
            <div className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl">
              <span className="text-[10px] font-bold text-zinc-400 block uppercase">Under Review</span>
              <span className="text-xl font-black text-purple-400">{projectData.tasks_awaiting_review}</span>
              <span className="text-[11px] text-purple-400/80 block mt-1">Awaiting teammate</span>
            </div>
            <div className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl">
              <span className="text-[10px] font-bold text-zinc-400 block uppercase">Blocked Tasks</span>
              <span className="text-xl font-black text-amber-400">{projectData.blocked_tasks}</span>
              <span className="text-[11px] text-amber-400/80 block mt-1">Unmet dependencies</span>
            </div>
            <div className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl">
              <span className="text-[10px] font-bold text-zinc-400 block uppercase">Overdue</span>
              <span className="text-xl font-black text-rose-400">{projectData.overdue_tasks}</span>
              <span className="text-[11px] text-rose-400/80 block mt-1">Past deadline</span>
            </div>
          </div>

          {/* Member Work & Responsibility Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projectData.member_activities.map((mem) => {
              const isMe = mem.user_id === user?.id;
              return (
                <div key={mem.user_id} className="p-4 bg-zinc-900/90 border border-zinc-800 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      {mem.avatar_url ? (
                        <img src={mem.avatar_url} alt={mem.full_name} className="w-8 h-8 rounded-full border border-zinc-700" />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-blue-600/30 text-blue-400 flex items-center justify-center text-xs font-bold">
                          {mem.full_name[0]}
                        </div>
                      )}
                      <div>
                        <span className="text-xs font-bold text-white block">
                          {mem.full_name} {isMe && <span className="text-[10px] text-zinc-400 font-normal">(You)</span>}
                        </span>
                        <span className="text-[10px] text-zinc-400">{mem.assigned_count} assigned tasks</span>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {mem.completed_count} done
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs pt-2 border-t border-zinc-800/80">
                    <div className="bg-zinc-950 p-1.5 rounded-lg">
                      <span className="text-[10px] text-zinc-500 block">IN PROGRESS</span>
                      <span className="font-bold text-blue-400">{mem.in_progress_count}</span>
                    </div>
                    <div className="bg-zinc-950 p-1.5 rounded-lg">
                      <span className="text-[10px] text-zinc-500 block">SUBMITTED</span>
                      <span className="font-bold text-purple-400">{mem.submitted_count}</span>
                    </div>
                    <div className="bg-zinc-950 p-1.5 rounded-lg">
                      <span className="text-[10px] text-zinc-500 block">AWAITING REVIEW</span>
                      <span className="font-bold text-amber-400">{mem.awaiting_review_count}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Collaborative Project Tasks Pipeline */}
          <div className="space-y-3">
            <h3 className="text-base font-bold text-white flex items-center justify-between">
              <span>Task Pipeline & Evidence Inspector</span>
              <span className="text-xs font-normal text-zinc-400">{projectData.recent_tasks.length} tasks</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projectData.recent_tasks.map((pt) => {
                const isAssignedToMe = pt.assignee_id === user?.id;
                const canReview = !isAssignedToMe && (pt.status === 'UNDER_REVIEW' || pt.status === 'SUBMITTED');
                const canSubmit = isAssignedToMe && (pt.status === 'IN_PROGRESS' || pt.status === 'TODO' || pt.status === 'CHANGES_REQUESTED') && !pt.is_blocked;

                return (
                  <div
                    key={pt.id}
                    className={`p-4 bg-zinc-900 border rounded-xl flex flex-col justify-between transition-all ${
                      pt.is_blocked
                        ? 'border-amber-500/40 bg-amber-950/10'
                        : pt.status === 'COMPLETED'
                        ? 'border-emerald-500/30'
                        : 'border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          pt.status === 'COMPLETED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : pt.status === 'UNDER_REVIEW'
                            ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                            : pt.status === 'CHANGES_REQUESTED'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            : pt.status === 'IN_PROGRESS'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                        }`}>
                          {pt.status.replace('_', ' ')}
                        </span>

                        <span className="text-[10px] font-mono text-zinc-400 bg-zinc-800 px-1.5 py-0.5 rounded">
                          {pt.priority}
                        </span>
                      </div>

                      <h4 className="text-sm font-bold text-white mb-1">{pt.title}</h4>
                      {pt.description && (
                        <p className="text-xs text-zinc-400 line-clamp-2 mb-2.5">{pt.description}</p>
                      )}

                      {/* Blocked Badge */}
                      {pt.is_blocked && (
                        <div className="p-2 mb-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300 flex items-start gap-1.5">
                          <Lock className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold block text-[11px]">Blocked by:</span>
                            <span className="text-[11px]">{pt.blocked_by.filter(b => b.is_blocking).map(b => b.depends_on_title).join(', ')}</span>
                          </div>
                        </div>
                      )}

                      {/* Evidence Details */}
                      <div className="flex flex-wrap items-center gap-1.5 mb-2.5 text-[11px] text-zinc-400">
                        {pt.branch && (
                          <span className="bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800 flex items-center gap-1 font-mono">
                            <GitCommit className="w-3 h-3 text-blue-400" />
                            {pt.branch}
                          </span>
                        )}
                        {pt.latest_commit_sha && (
                          <span className="bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800 font-mono text-emerald-400">
                            {pt.latest_commit_sha}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Bottom row: Assignee & Action Buttons */}
                    <div className="pt-2.5 border-t border-zinc-800/80 flex items-center justify-between">
                      <span className="text-xs text-zinc-400">{pt.assignee_name || 'Unassigned'}</span>

                      <div className="flex items-center gap-1.5">
                        {canSubmit && (
                          <button
                            onClick={() => {
                              setSelectedTask(pt);
                              setSubmitBranch(pt.branch || '');
                              setIsTaskSubmitOpen(true);
                            }}
                            className="px-2.5 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                          >
                            Submit
                          </button>
                        )}

                        {canReview && (
                          <button
                            onClick={() => {
                              setSelectedTask(pt);
                              setTaskReviewStatus('APPROVED');
                              setTaskReviewComment('');
                              setIsTaskReviewOpen(true);
                            }}
                            className="px-2.5 py-1 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
                          >
                            Review
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}

      {/* When in DAILY_HABIT mode (or if no project data yet), show the classic daily duo accountability layout */}
      {activeTabMode === 'DAILY_HABIT' && (
        <div className="space-y-6">
      {/* Top Banner: Duo Completion Status */}
      {isCompleted ? (
        <div className="relative overflow-hidden rounded-2xl p-6 bg-gradient-to-r from-emerald-950/80 via-zinc-900 to-teal-950/80 border border-emerald-500/40 shadow-2xl">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 relative z-10">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 shadow-lg shadow-emerald-950">
                <Sparkles className="w-6 h-6 animate-spin" style={{ animationDuration: '6s' }} />
              </div>
              <div>
                <span className="text-xs uppercase font-extrabold tracking-widest text-emerald-400 font-mono">
                  ACCOUNTABILITY ACHIEVED
                </span>
                <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                  🎉 DAY COMPLETED!
                </h1>
                <p className="text-xs text-zinc-300 mt-0.5">
                  Both duo members satisfied their requirements. Daily habit secured!
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 bg-[#0d1117]/80 px-4 py-2.5 rounded-xl border border-emerald-500/30">
              <Flame className="w-6 h-6 text-amber-500 fill-amber-500 animate-pulse" />
              <div>
                <span className="text-[10px] uppercase font-bold text-zinc-400 block font-mono">Current Streak</span>
                <span className="text-lg font-extrabold text-white font-mono leading-none">
                  {duo?.streak?.current_streak || 1} DAYS
                </span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl p-5 bg-[#161b22] border border-[#30363d] flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl border ${
              progress?.status.includes('WAITING')
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
            }`}>
              <Clock className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-zinc-500 font-mono tracking-wider">
                TODAY'S DUO STATUS
              </span>
              <h2 className="text-base font-bold text-white tracking-tight">
                {progress?.status === 'WAITING_FOR_USER_B' && 'Waiting for Partner Upload'}
                {progress?.status === 'WAITING_FOR_USER_A' && 'Waiting for Your Upload'}
                {progress?.status === 'WAITING_FOR_REVIEW' && 'Awaiting Peer Review Approval'}
                {progress?.status === 'CHANGES_REQUESTED' && 'Changes Requested by Partner'}
                {progress?.status === 'ACTIVE' && 'Active — Push today to protect your streak'}
                {progress?.status === 'NO_TASK' && 'No task created yet today'}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleVerifyNow}
              disabled={verifying}
              className="px-3 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${verifying ? 'animate-spin' : ''}`} />
              <span>{verifying ? 'Verifying...' : 'Verify Commits'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Today's Task Card */}
      {task ? (
        <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  {task.github_requirement}
                </span>
                <span className="text-xs text-zinc-500 font-mono">Date: {task.date}</span>
              </div>
              <h3 className="text-lg font-bold text-white">{task.title}</h3>
              <p className="text-xs text-zinc-400 leading-relaxed max-w-3xl">{task.description}</p>
            </div>

            <button
              onClick={() => onNavigate('task')}
              className="text-xs font-semibold text-zinc-400 hover:text-white flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-zinc-800 transition-colors"
            >
              <span>View Details</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Two-Person Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {/* Current User Card */}
            <div className="p-5 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center font-bold text-xs text-emerald-400">
                    YOU
                  </div>
                  <div>
                    <span className="text-xs font-bold text-white block">{user?.full_name}</span>
                    <span className="text-[10px] text-zinc-500 font-mono">@{user?.github_username || 'no-gh'}</span>
                  </div>
                </div>

                {userProg?.github_verified ? (
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Requirement Satisfied
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">
                    <Clock className="w-3.5 h-3.5" />
                    Pending Commits
                  </span>
                )}
              </div>

              <div className="text-xs space-y-1 bg-zinc-900/60 p-3 rounded-lg border border-zinc-800">
                <div className="flex justify-between text-zinc-400">
                  <span>Today's Commits:</span>
                  <span className="font-mono font-bold text-zinc-200">{userProg?.commit_count || 0}</span>
                </div>
                {userProg?.latest_commit_message && (
                  <div className="text-[11px] text-zinc-400 truncate pt-1 border-t border-zinc-800">
                    <span className="text-zinc-500">Latest:</span> "{userProg.latest_commit_message}"
                  </div>
                )}
              </div>

              {/* Action: Submit for peer review if shared mode and uploaded */}
              {isShared && userProg?.github_verified && (
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] text-zinc-400">
                    Peer Review: <span className="font-bold text-zinc-200">{userProg.review_status}</span>
                  </span>
                  {userProg.submission_status === 'PENDING' && (
                    <button
                      onClick={handleSubmitWork}
                      disabled={submitting}
                      className="px-3 py-1 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
                    >
                      {submitting ? 'Submitting...' : 'Submit for Review'}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Partner Card */}
            <div className="p-5 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-purple-600/20 border border-purple-500/30 flex items-center justify-center font-bold text-xs text-purple-400">
                    PARTNER
                  </div>
                  <div>
                    <span className="text-xs font-bold text-white block">{partnerProg?.user_name || 'Partner'}</span>
                    <span className="text-[10px] text-zinc-500 font-mono">@{partnerProg?.github_username || 'partner'}</span>
                  </div>
                </div>

                {partnerProg?.github_verified ? (
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Satisfied ({partnerProg.commit_count})
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">
                    <Clock className="w-3.5 h-3.5" />
                    Waiting...
                  </span>
                )}
              </div>

              <div className="text-xs space-y-1 bg-zinc-900/60 p-3 rounded-lg border border-zinc-800">
                <div className="flex justify-between text-zinc-400">
                  <span>Today's Commits:</span>
                  <span className="font-mono font-bold text-zinc-200">{partnerProg?.commit_count || 0}</span>
                </div>
                {partnerProg?.latest_commit_message && (
                  <div className="text-[11px] text-zinc-400 truncate pt-1 border-t border-zinc-800">
                    <span className="text-zinc-500">Latest:</span> "{partnerProg.latest_commit_message}"
                  </div>
                )}
              </div>

              {/* Action: Review partner task */}
              {isShared && partnerProg && (
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] text-zinc-400">
                    Review Status: <span className="font-bold text-zinc-200">{partnerProg.review_status}</span>
                  </span>
                  {partnerProg.github_verified && (
                    <button
                      onClick={() => handleOpenReview(partnerProg)}
                      className="px-3 py-1 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors flex items-center gap-1"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Review Work</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Shared Project Verification Status Bar */}
          {isShared && progress?.project_verification && (
            <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-blue-400" />
                  Shared Project Checks
                </span>
                <span className={`font-mono text-xs font-bold ${
                  progress.project_verification.overall_status === 'PASSED' ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  Overall: {progress.project_verification.overall_status}
                </span>
              </div>

              <div className="grid grid-cols-4 gap-2 pt-1">
                {[
                  { label: 'Build', status: progress.project_verification.build_status },
                  { label: 'Tests', status: progress.project_verification.test_status },
                  { label: 'Lint', status: progress.project_verification.lint_status },
                  { label: 'CI', status: progress.project_verification.ci_status },
                ].map((chk) => (
                  <div key={chk.label} className="p-2 bg-zinc-900/60 rounded-lg border border-zinc-800 text-center">
                    <span className="text-[10px] text-zinc-500 block">{chk.label}</span>
                    <span className={`text-xs font-bold ${
                      chk.status === 'PASSED' ? 'text-emerald-400' :
                      chk.status === 'FAILED' ? 'text-red-400' : 'text-zinc-400'
                    }`}>
                      {chk.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="p-8 bg-[#161b22] border border-[#30363d] rounded-2xl text-center space-y-3">
          <h3 className="text-base font-bold text-white">No Task Configured for Today</h3>
          <p className="text-xs text-zinc-400 max-w-md mx-auto">
            Set up today's daily focus and commit requirements for both duo members.
          </p>
          <button
            onClick={() => onNavigate('task')}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg transition-colors inline-flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Create Today's Task</span>
          </button>
        </div>
      )}

      {/* Review Modal */}
      <PeerReviewModal
        isOpen={isReviewModalOpen}
        task={task}
        partnerProgress={selectedPartnerProgress}
        onClose={() => setIsReviewModalOpen(false)}
        onSuccess={fetchDashboardData}
      />
        </div>
      )}

      {/* Project Execution Peer Review Modal */}
      {isTaskReviewOpen && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-purple-400" />
                <span>Peer Review: {selectedTask.title}</span>
              </h3>
              <button onClick={() => setIsTaskReviewOpen(false)} className="text-zinc-400 hover:text-white text-sm">✕</button>
            </div>

            <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-xl space-y-1 text-xs">
              <div className="text-zinc-400">Assignee: <span className="text-white font-bold">{selectedTask.assignee_name}</span></div>
              {selectedTask.branch && <div className="text-zinc-400">Branch: <span className="text-blue-400 font-mono">{selectedTask.branch}</span></div>}
              {selectedTask.latest_commit_sha && <div className="text-zinc-400">Commit SHA: <span className="text-emerald-400 font-mono">{selectedTask.latest_commit_sha}</span></div>}
            </div>

            <form onSubmit={handleProjectTaskReviewSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-2">Review Decision</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setTaskReviewStatus('APPROVED')}
                    className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all ${
                      taskReviewStatus === 'APPROVED'
                        ? 'bg-emerald-600/20 text-emerald-400 border-emerald-500/50'
                        : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                    }`}
                  >
                    ✓ APPROVE TASK
                  </button>
                  <button
                    type="button"
                    onClick={() => setTaskReviewStatus('CHANGES_REQUESTED')}
                    className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all ${
                      taskReviewStatus === 'CHANGES_REQUESTED'
                        ? 'bg-rose-600/20 text-rose-400 border-rose-500/50'
                        : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                    }`}
                  >
                    ⚠ REQUEST CHANGES
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Feedback Comments *</label>
                <textarea
                  required
                  rows={3}
                  value={taskReviewComment}
                  onChange={(e) => setTaskReviewComment(e.target.value)}
                  placeholder="Provide feedback on the submitted code and test coverage..."
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsTaskReviewOpen(false)}
                  className="px-3 py-1.5 bg-zinc-800 text-zinc-300 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={taskReviewSubmitting}
                  className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg"
                >
                  {taskReviewSubmitting ? 'Submitting...' : 'Submit Review'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Project Task Evidence Submission Modal */}
      {isTaskSubmitOpen && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <GitCommit className="w-5 h-5 text-blue-400" />
                <span>Submit Task: {selectedTask.title}</span>
              </h3>
              <button onClick={() => setIsTaskSubmitOpen(false)} className="text-zinc-400 hover:text-white text-sm">✕</button>
            </div>

            <form onSubmit={handleProjectTaskEvidenceSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Branch Name</label>
                <input
                  type="text"
                  value={submitBranch}
                  onChange={(e) => setSubmitBranch(e.target.value)}
                  placeholder="e.g. feature/auth-api"
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Commit SHA</label>
                <input
                  type="text"
                  value={submitSha}
                  onChange={(e) => setSubmitSha(e.target.value)}
                  placeholder="e.g. 7-digit sha or full commit hash"
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Commit Message</label>
                <input
                  type="text"
                  value={submitMessage}
                  onChange={(e) => setSubmitMessage(e.target.value)}
                  placeholder="e.g. feat: complete database schema & migrations"
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Notes for Teammate Review</label>
                <textarea
                  rows={2}
                  value={submitNotes}
                  onChange={(e) => setSubmitNotes(e.target.value)}
                  placeholder="Summary of changes and testing instructions..."
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsTaskSubmitOpen(false)}
                  className="px-3 py-1.5 bg-zinc-800 text-zinc-300 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={taskSubmittingWork}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
                >
                  {taskSubmittingWork ? 'Submitting...' : 'Submit Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Project Task Modal */}
      {isCreateTaskOpen && projectData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-400" />
                <span>Create New Project Task</span>
              </h3>
              <button onClick={() => setIsCreateTaskOpen(false)} className="text-zinc-400 hover:text-white text-sm">✕</button>
            </div>

            <form onSubmit={handleProjectTaskCreate} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Task Title *</label>
                <input
                  required
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Implement GitHub Webhook validation"
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Acceptance criteria and deliverables..."
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-zinc-300 mb-1">Assignee</label>
                  <select
                    value={newAssigneeId}
                    onChange={(e) => setNewAssigneeId(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                  >
                    <option value="">Unassigned (Backlog)</option>
                    {duo?.members.map((m) => (
                      <option key={m.user_id} value={m.user_id}>{m.full_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-300 mb-1">Priority</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as TaskPriority)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Milestone</label>
                <select
                  value={newMilestoneId}
                  onChange={(e) => setNewMilestoneId(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white"
                >
                  <option value="">None</option>
                  {projectData.milestones.map((m) => (
                    <option key={m.id} value={m.id}>{m.title}</option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateTaskOpen(false)}
                  className="px-3 py-1.5 bg-zinc-800 text-zinc-300 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingTask}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
                >
                  {isCreatingTask ? 'Creating...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
