import React, { useState, useEffect } from 'react';
import {
  CheckSquare,
  Clock,
  GitCommit,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Plus,
  RefreshCw,
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { DailyTask, UserTaskProgress } from '../types';
import { PeerReviewModal } from '../components/reviews/PeerReviewModal';

export const TodaysTaskPage: React.FC = () => {
  const { user, duo } = useAuth();
  const [task, setTask] = useState<DailyTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [userATask, setUserATask] = useState('');
  const [userBTask, setUserBTask] = useState('');
  const [githubReq, setGithubReq] = useState('1 commit');
  const [minCommits, setMinCommits] = useState(1);
  const [saving, setSaving] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [partnerToReview, setPartnerToReview] = useState<UserTaskProgress | null>(null);

  const fetchTask = async () => {
    try {
      const data = await api.getTodayTask();
      setTask(data);
      if (data) {
        setTitle(data.title);
        setDescription(data.description || '');
        setUserATask(data.user_a_task || '');
        setUserBTask(data.user_b_task || '');
        setGithubReq(data.github_requirement);
        setMinCommits(data.min_commits_required);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTask();
  }, [user]);

  const handleSaveTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const saved = await api.createDailyTask({
        title,
        description,
        user_a_task: userATask,
        user_b_task: userBTask,
        github_requirement: githubReq,
        min_commits_required: minCommits,
      });
      setTask(saved);
      setIsEditing(false);
    } catch (err: any) {
      alert(err.message || 'Failed to save task');
    } finally {
      setSaving(false);
    }
  };

  const partnerProg = task?.user_progress.find(p => p.user_id !== user?.id) || null;
  const myProg = task?.user_progress.find(p => p.user_id === user?.id) || null;

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <CheckSquare className="w-6 h-6 text-emerald-400" />
            <span>Today's Task</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Defined targets for both duo members. Verified automatically via GitHub.
          </p>
        </div>

        <button
          onClick={() => setIsEditing(!isEditing)}
          className="px-3.5 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg transition-colors"
        >
          {isEditing ? 'Cancel Edit' : task ? 'Edit Task' : 'Create Task'}
        </button>
      </div>

      {isEditing ? (
        <form onSubmit={handleSaveTask} className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white">Configure Daily Task</h3>
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1">Task Title</label>
            <input
              type="text"
              required
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. Implement Authentication & Reviews"
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3.5 py-2 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1">Overall Description</label>
            <textarea
              rows={3}
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Context and deliverable goals for today..."
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl p-3 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-purple-400 mb-1">User A (Alex) Focus Area</label>
              <textarea
                rows={2}
                value={userATask}
                onChange={e => setUserATask(e.target.value)}
                placeholder="Specific task for User A..."
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl p-2.5 text-xs text-zinc-100 focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-blue-400 mb-1">User B (Morgan) Focus Area</label>
              <textarea
                rows={2}
                value={userBTask}
                onChange={e => setUserBTask(e.target.value)}
                placeholder="Specific task for User B..."
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl p-2.5 text-xs text-zinc-100 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-300 mb-1">Requirement Label</label>
              <input
                type="text"
                value={githubReq}
                onChange={e => setGithubReq(e.target.value)}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-300 mb-1">Minimum Commits</label>
              <input
                type="number"
                min={1}
                max={50}
                value={minCommits}
                onChange={e => setMinCommits(Number(e.target.value))}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition-colors"
            >
              {saving ? 'Saving...' : 'Save Task'}
            </button>
          </div>
        </form>
      ) : task ? (
        <div className="space-y-6">
          {/* Main Task Header */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                Requirement: {task.github_requirement}
              </span>
              <span className="text-xs font-mono text-zinc-400">
                Deadline: {new Date(task.deadline_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ({duo?.timezone})
              </span>
            </div>
            <h2 className="text-xl font-bold text-white">{task.title}</h2>
            <p className="text-xs text-zinc-300 leading-relaxed">{task.description}</p>
          </div>

          {/* Assigned Focus for User A & User B */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {task.user_progress.map((p, idx) => {
              const isMe = p.user_id === user?.id;
              return (
                <div key={p.user_id} className="p-5 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                        isMe ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                      }`}>
                        {isMe ? 'YOU' : 'PARTNER'}
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-white">{p.user_name}</h4>
                        <span className="text-[10px] text-zinc-500 font-mono">@{p.github_username || 'no-gh'}</span>
                      </div>
                    </div>

                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                      p.github_verified
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    }`}>
                      {p.github_verified ? '✓ Verified' : 'Pending'}
                    </span>
                  </div>

                  {p.assigned_task && (
                    <div className="p-3 bg-[#0d1117] border border-[#30363d] rounded-xl">
                      <span className="text-[10px] uppercase font-bold text-zinc-500 block mb-1">Assigned Scope:</span>
                      <p className="text-xs text-zinc-200 font-medium">{p.assigned_task}</p>
                    </div>
                  )}

                  <div className="text-xs space-y-1 bg-[#0d1117] p-3 rounded-xl border border-[#30363d]">
                    <div className="flex justify-between text-zinc-400">
                      <span>Verified Commits:</span>
                      <span className="font-mono font-bold text-zinc-200">{p.commit_count}</span>
                    </div>
                    <div className="flex justify-between text-zinc-400">
                      <span>Peer Review:</span>
                      <span className="font-bold text-zinc-200">{p.review_status}</span>
                    </div>
                    {p.latest_commit_sha && (
                      <div className="flex justify-between text-zinc-400 pt-1 border-t border-zinc-800">
                        <span>Latest SHA:</span>
                        <span className="font-mono text-emerald-400">{p.latest_commit_sha}</span>
                      </div>
                    )}
                  </div>

                  {!isMe && p.github_verified && (
                    <button
                      onClick={() => {
                        setPartnerToReview(p);
                        setReviewModalOpen(true);
                      }}
                      className="w-full py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-1.5"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      <span>Review Partner's Work</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="p-8 bg-[#161b22] border border-[#30363d] rounded-2xl text-center space-y-3">
          <p className="text-xs text-zinc-400">No task defined for today yet.</p>
          <button
            onClick={() => setIsEditing(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg"
          >
            Create Task
          </button>
        </div>
      )}

      <PeerReviewModal
        isOpen={reviewModalOpen}
        task={task}
        partnerProgress={partnerToReview}
        onClose={() => setReviewModalOpen(false)}
        onSuccess={fetchTask}
      />
    </div>
  );
};
