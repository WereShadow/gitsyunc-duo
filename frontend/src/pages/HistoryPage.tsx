import React, { useState, useEffect } from 'react';
import { History as HistoryIcon, Search, CheckCircle2, Clock, AlertCircle, ChevronRight, ExternalLink } from 'lucide-react';
import { api } from '../services/api';
import { DailyTask } from '../types';

export const HistoryPage: React.FC = () => {
  const [tasks, setTasks] = useState<DailyTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'ALL' | 'COMPLETED' | 'MISSED'>('ALL');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await api.getTaskHistory();
        setTasks(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const filteredTasks = tasks.filter(t => {
    const matchesSearch = t.title.toLowerCase().includes(search.toLowerCase()) ||
      (t.description && t.description.toLowerCase().includes(search.toLowerCase()));
    const matchesFilter = filter === 'ALL' || t.status === filter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <HistoryIcon className="w-6 h-6 text-emerald-400" />
            <span>Task History</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Historical log of daily accountability tasks, commits, and review milestones.
          </p>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search history..."
              className="bg-[#161b22] border border-[#30363d] rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 w-44 sm:w-52 font-mono"
            />
          </div>

          <select
            value={filter}
            onChange={e => setFilter(e.target.value as any)}
            className="bg-[#161b22] border border-[#30363d] rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
          >
            <option value="ALL">All Outcomes</option>
            <option value="COMPLETED">Completed</option>
            <option value="MISSED">Missed</option>
          </select>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {filteredTasks.length === 0 ? (
          <div className="p-8 bg-[#161b22] border border-[#30363d] rounded-2xl text-center text-xs text-zinc-500">
            No tasks found matching your filter criteria.
          </div>
        ) : (
          filteredTasks.map((t) => {
            const userA = t.user_progress[0];
            const userB = t.user_progress[1];
            const isCompleted = t.status === 'COMPLETED';

            return (
              <div
                key={t.id}
                className="p-5 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-3 hover:border-zinc-700 transition-colors shadow-sm"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#30363d]/60 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-zinc-500">{t.date}</span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                        isCompleted
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-red-500/10 text-red-400 border-red-500/30'
                      }`}>
                        {t.status}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-white mt-1">{t.title}</h3>
                  </div>

                  <span className="text-xs font-mono text-zinc-500">
                    Requirement: {t.github_requirement}
                  </span>
                </div>

                {t.description && (
                  <p className="text-xs text-zinc-400">{t.description}</p>
                )}

                {/* Two Member Outcome Badges */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {userA && (
                    <div className="p-3 bg-[#0d1117] rounded-xl border border-[#30363d] flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-zinc-200 block">{userA.user_name}</span>
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {userA.commit_count} commits {userA.latest_commit_sha ? `(${userA.latest_commit_sha})` : ''}
                        </span>
                      </div>
                      <span className={`text-[11px] font-bold ${userA.github_verified ? 'text-emerald-400' : 'text-zinc-500'}`}>
                        {userA.github_verified ? '✓ Satisfied' : 'Pending'}
                      </span>
                    </div>
                  )}

                  {userB && (
                    <div className="p-3 bg-[#0d1117] rounded-xl border border-[#30363d] flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-zinc-200 block">{userB.user_name}</span>
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {userB.commit_count} commits {userB.latest_commit_sha ? `(${userB.latest_commit_sha})` : ''}
                        </span>
                      </div>
                      <span className={`text-[11px] font-bold ${userB.github_verified ? 'text-emerald-400' : 'text-zinc-500'}`}>
                        {userB.github_verified ? '✓ Satisfied' : 'Pending'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
