import React, { useState } from 'react';
import { GitCommit, X, ArrowRight, Check, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface SimulatePushModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const SimulatePushModal: React.FC<SimulatePushModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { user, duo } = useAuth();
  const [targetUserId, setTargetUserId] = useState<string>(user?.id || '');
  const [commitMessage, setCommitMessage] = useState('feat: implement daily accountability check');
  const [branch, setBranch] = useState('main');
  const [files, setFiles] = useState('src/auth.py, src/api.py');
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const repoName = duo?.project_mode === 'SHARED' ? 'campus-ai/assistant' : `${user?.github_username || 'user'}/project`;

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);
    try {
      const fileList = files.split(',').map(f => f.trim()).filter(Boolean);
      const res = await api.simulatePush({
        repository_full_name: repoName,
        branch,
        commit_message: commitMessage,
        files_changed: fileList,
        target_user_id: targetUserId || user?.id,
      });

      setStatusMsg(`Success! Commit pushed. Task status: ${res.task_status}`);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1000);
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message || 'Simulation failed'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-2xl shadow-2xl p-6 overflow-hidden">
        {/* Decorative subtle gradient */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-blue-500 to-purple-500" />
        
        <div className="flex items-center justify-between pb-4 border-b border-[#30363d]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <GitCommit className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Simulate GitHub Push</h3>
              <p className="text-xs text-zinc-400">Test verification & peer reviews without live webhooks</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSimulate} className="mt-5 space-y-4">
          {/* Target User */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
              Simulate Push For
            </label>
            <div className="grid grid-cols-2 gap-2">
              {duo?.members.map(m => (
                <button
                  type="button"
                  key={m.user_id}
                  onClick={() => setTargetUserId(m.user_id)}
                  className={`px-3 py-2 text-xs font-medium rounded-lg border text-left flex items-center justify-between transition-all ${
                    (targetUserId === m.user_id || (!targetUserId && m.user_id === user?.id))
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                      : 'bg-[#0d1117] border-[#30363d] text-zinc-400 hover:border-zinc-600'
                  }`}
                >
                  <span className="truncate">{m.full_name.split(' ')[0]} ({m.role})</span>
                  {(targetUserId === m.user_id || (!targetUserId && m.user_id === user?.id)) && (
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Repository & Branch */}
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2">
              <label className="block text-xs font-semibold text-zinc-300 mb-1">Target Repository</label>
              <input
                type="text"
                disabled
                value={repoName}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-1.5 text-xs text-zinc-400 cursor-not-allowed font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-300 mb-1">Branch</label>
              <input
                type="text"
                value={branch}
                onChange={e => setBranch(e.target.value)}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>
          </div>

          {/* Commit Message */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1">Commit Message</label>
            <input
              type="text"
              required
              value={commitMessage}
              onChange={e => setCommitMessage(e.target.value)}
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>

          {/* Files Changed */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1">Changed Files (comma-separated)</label>
            <input
              type="text"
              value={files}
              onChange={e => setFiles(e.target.value)}
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>

          {statusMsg && (
            <div className={`p-3 rounded-lg text-xs font-medium ${
              statusMsg.includes('Success')
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-red-500/10 text-red-400 border border-red-500/20'
            }`}>
              {statusMsg}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? 'Simulating...' : (
                <>
                  <span>Push Commit</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
