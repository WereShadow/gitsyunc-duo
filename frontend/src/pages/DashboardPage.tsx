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
import { TodayProgress, DailyTask, UserTaskProgress } from '../types';
import { PeerReviewModal } from '../components/reviews/PeerReviewModal';

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

  const fetchDashboardData = async () => {
    try {
      const [progData, taskData] = await Promise.all([
        api.getTodayProgress(),
        api.getTodayTask(),
      ]);
      setProgress(progData);
      setTask(taskData);

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

  const isCompleted = progress?.status === 'COMPLETED';
  const isShared = duo?.project_mode === 'SHARED';

  const userProg = progress?.current_user_progress;
  const partnerProg = progress?.partner_user_progress;

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-7xl mx-auto animate-in fade-in duration-200">
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
  );
};
