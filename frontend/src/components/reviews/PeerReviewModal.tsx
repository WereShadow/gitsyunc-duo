import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  GitCommit,
  GitBranch,
  FileCode,
  Clock,
  ShieldCheck,
  ExternalLink,
  MessageSquare,
  AlertTriangle,
  Send,
  Sparkles
} from 'lucide-react';
import { DailyTask, UserTaskProgress } from '../../types';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface PeerReviewModalProps {
  isOpen: boolean;
  task: DailyTask | null;
  partnerProgress: UserTaskProgress | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const PeerReviewModal: React.FC<PeerReviewModalProps> = ({
  isOpen,
  task,
  partnerProgress,
  onClose,
  onSuccess
}) => {
  const { user } = useAuth();
  const [actionType, setActionType] = useState<'APPROVE' | 'CHANGES' | null>(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !task || !partnerProgress) return null;

  // Verification that reviewer is NOT task owner
  const isOwnTask = partnerProgress.user_id === user?.id;

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!actionType) return;
    if (actionType === 'CHANGES' && !comment.trim()) {
      setErrorMsg('Please explain what changes are requested.');
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.submitReview(task.id, {
        status: actionType === 'APPROVE' ? 'APPROVED' : 'CHANGES_REQUESTED',
        comment: comment.trim() || (actionType === 'APPROVE' ? 'Approved work!' : 'Changes requested'),
        commit_sha: partnerProgress.latest_commit_sha || undefined
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const checks = task.verifications?.[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-[#161b22] border border-[#30363d] rounded-2xl shadow-2xl overflow-hidden">
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#30363d] bg-[#0d1117]/80">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-xl">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">Peer Task Review</h2>
                <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full font-semibold border ${
                  partnerProgress.review_status === 'APPROVED'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : partnerProgress.review_status === 'CHANGES_REQUESTED'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                }`}>
                  {partnerProgress.review_status}
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Assigned to <span className="text-zinc-200 font-semibold">{partnerProgress.user_name}</span> (@{partnerProgress.github_username})
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Task Info */}
          <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-zinc-100">{task.title}</h3>
              <span className="text-xs text-zinc-500 font-mono">{task.date}</span>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">{task.description}</p>
            {partnerProgress.assigned_task && (
              <div className="mt-2 pt-2 border-t border-zinc-800/80">
                <span className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider block">Assigned Focus:</span>
                <p className="text-xs text-zinc-300 mt-0.5 font-medium">{partnerProgress.assigned_task}</p>
              </div>
            )}
          </div>

          {/* GitHub Work & Commit Details */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
              <GitCommit className="w-4 h-4 text-emerald-400" />
              <span>GitHub Verification & Commit Info</span>
            </h4>

            <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400">Verification Status:</span>
                {partnerProgress.github_verified ? (
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Verified ({partnerProgress.commit_count} commits)
                  </span>
                ) : (
                  <span className="text-amber-400 font-medium">Pending GitHub Upload</span>
                )}
              </div>

              {partnerProgress.latest_commit_sha && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-400">Latest Commit:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded text-[11px] border border-zinc-700">
                      {partnerProgress.latest_commit_sha}
                    </span>
                    {partnerProgress.latest_commit_url && (
                      <a
                        href={partnerProgress.latest_commit_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-zinc-400 hover:text-white"
                        title="View on GitHub"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              )}

              {partnerProgress.latest_commit_message && (
                <div className="text-xs">
                  <span className="text-zinc-500 block mb-0.5">Commit Message:</span>
                  <p className="font-mono text-zinc-300 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800">
                    "{partnerProgress.latest_commit_message}"
                  </p>
                </div>
              )}

              {/* Changed Files */}
              {partnerProgress.changed_files && partnerProgress.changed_files.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 block mb-1 flex items-center gap-1">
                    <FileCode className="w-3.5 h-3.5 text-zinc-400" />
                    Changed Files:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {partnerProgress.changed_files.map((file, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 text-[11px] font-mono bg-zinc-800 text-zinc-300 rounded border border-zinc-700/60"
                      >
                        {file}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Automated Project Checks */}
          {checks && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>Automated Project Checks</span>
              </h4>

              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: 'Build', status: checks.build_status },
                  { label: 'Tests', status: checks.test_status },
                  { label: 'Lint', status: checks.lint_status },
                  { label: 'CI', status: checks.ci_status },
                ].map(c => (
                  <div key={c.label} className="p-2.5 bg-[#0d1117] border border-[#30363d] rounded-xl text-center">
                    <span className="text-[10px] text-zinc-500 block font-medium">{c.label}</span>
                    <span className={`text-xs font-bold mt-0.5 inline-block ${
                      c.status === 'PASSED' ? 'text-emerald-400' :
                      c.status === 'FAILED' ? 'text-red-400' : 'text-zinc-400'
                    }`}>
                      {c.status === 'PASSED' ? '✓ Passed' : c.status === 'FAILED' ? '✕ Failed' : '○ Skipped'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Past Review Audit History */}
          {task.reviews && task.reviews.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-4 h-4 text-zinc-400" />
                <span>Review History Audit Log</span>
              </h4>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {task.reviews.map((rev) => (
                  <div key={rev.id} className="p-3 bg-[#0d1117] border border-[#30363d] rounded-xl text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-zinc-200">{rev.reviewer_name}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                          rev.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                        }`}>
                          {rev.status}
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-500">
                        {new Date(rev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-zinc-300 italic">"{rev.comment}"</p>
                    {rev.commit_sha && (
                      <span className="text-[10px] text-zinc-500 font-mono block">
                        Commit verified: {rev.commit_sha}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Review Action Form (Only available if NOT own task) */}
          {isOwnTask ? (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>You cannot review your own task. Your partner will review and approve your submission.</span>
            </div>
          ) : (
            <form onSubmit={handleSubmitReview} className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-3">
              <span className="text-xs font-bold text-zinc-200 block">Submit Your Peer Review</span>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActionType('APPROVE')}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                    actionType === 'APPROVE'
                      ? 'bg-emerald-600 text-white border-emerald-500 shadow-sm'
                      : 'bg-zinc-800 text-zinc-300 border-zinc-700 hover:border-emerald-500/50'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                  <span>Approve Task</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActionType('CHANGES')}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                    actionType === 'CHANGES'
                      ? 'bg-amber-600 text-white border-amber-500 shadow-sm'
                      : 'bg-zinc-800 text-zinc-300 border-zinc-700 hover:border-amber-500/50'
                  }`}
                >
                  <AlertTriangle className="w-4 h-4 text-amber-300" />
                  <span>Request Changes</span>
                </button>
              </div>

              {actionType && (
                <div className="space-y-2 pt-1 animate-in fade-in duration-150">
                  <label className="block text-xs font-medium text-zinc-400">
                    {actionType === 'APPROVE' ? 'Review Note (Optional):' : 'Reason for Requesting Changes (Required):'}
                  </label>
                  <textarea
                    rows={2}
                    required={actionType === 'CHANGES'}
                    value={comment}
                    onChange={e => setComment(e.target.value)}
                    placeholder={actionType === 'APPROVE' ? 'Code is clean and verified.' : 'e.g. Please handle error response when token expires.'}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              )}

              {errorMsg && (
                <div className="p-2.5 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg">
                  {errorMsg}
                </div>
              )}

              {actionType && (
                <div className="flex justify-end pt-1">
                  <button
                    type="submit"
                    disabled={submitting}
                    className={`px-4 py-2 text-xs font-bold rounded-lg text-white transition-colors flex items-center gap-1.5 ${
                      actionType === 'APPROVE'
                        ? 'bg-emerald-600 hover:bg-emerald-500'
                        : 'bg-amber-600 hover:bg-amber-500'
                    }`}
                  >
                    {submitting ? 'Submitting...' : 'Confirm & Save Review'}
                  </button>
                </div>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
