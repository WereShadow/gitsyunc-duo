import React, { useState, useEffect } from 'react';
import { GitCommit, GitBranch, RefreshCw, ExternalLink, CheckCircle2, Clock, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { GitHubActivity } from '../types';

export const GitHubActivityPage: React.FC = () => {
  const { user, duo } = useAuth();
  const [activity, setActivity] = useState<GitHubActivity | null>(null);
  const [partnerActivity, setPartnerActivity] = useState<GitHubActivity | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const partner = duo?.members.find(m => m.user_id !== user?.id);

  const fetchActivities = async () => {
    try {
      const myAct = await api.getGitHubActivity(user?.id);
      setActivity(myAct);

      if (partner) {
        const pAct = await api.getGitHubActivity(partner.user_id);
        setPartnerActivity(pAct);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, [user]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await api.verifyGitHub();
    await fetchActivities();
  };

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <GitCommit className="w-6 h-6 text-emerald-400" />
            <span>GitHub Activity Stream</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Real-time feed of qualifying commits and push events for your Duo.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-3.5 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg transition-colors flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Sync Activity</span>
        </button>
      </div>

      {/* Two user activity columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current User Activity */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white">Your Commits ({user?.full_name})</span>
              <span className="text-[10px] font-mono text-zinc-500">@{activity?.github_username}</span>
            </div>
            {activity?.verification_status ? (
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Verified
              </span>
            ) : (
              <span className="text-xs text-amber-400">Waiting for commit</span>
            )}
          </div>

          <div className="space-y-2">
            {activity?.today_commits && activity.today_commits.length > 0 ? (
              activity.today_commits.map((c) => (
                <div
                  key={c.sha}
                  className="p-4 bg-[#161b22] border border-[#30363d] rounded-xl space-y-2 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {c.sha}
                    </span>
                    <span className="text-[10px] text-zinc-500">
                      {new Date(c.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-200 font-mono">"{c.message}"</p>
                  {c.files_changed && c.files_changed.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {c.files_changed.map((f, i) => (
                        <span key={i} className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="p-8 bg-[#161b22] border border-[#30363d] rounded-xl text-center text-xs text-zinc-500">
                No commits detected for today yet. Use 'Simulate Push' or push to your configured branch.
              </div>
            )}
          </div>
        </div>

        {/* Partner Activity */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white">Partner Commits ({partner?.full_name || 'Partner'})</span>
              <span className="text-[10px] font-mono text-zinc-500">@{partnerActivity?.github_username}</span>
            </div>
            {partnerActivity?.verification_status ? (
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Verified
              </span>
            ) : (
              <span className="text-xs text-amber-400">Waiting for commit</span>
            )}
          </div>

          <div className="space-y-2">
            {partnerActivity?.today_commits && partnerActivity.today_commits.length > 0 ? (
              partnerActivity.today_commits.map((c) => (
                <div
                  key={c.sha}
                  className="p-4 bg-[#161b22] border border-[#30363d] rounded-xl space-y-2 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                      {c.sha}
                    </span>
                    <span className="text-[10px] text-zinc-500">
                      {new Date(c.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-200 font-mono">"{c.message}"</p>
                  {c.files_changed && c.files_changed.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {c.files_changed.map((f, i) => (
                        <span key={i} className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="p-8 bg-[#161b22] border border-[#30363d] rounded-xl text-center text-xs text-zinc-500">
                Partner has not pushed today's commits yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
