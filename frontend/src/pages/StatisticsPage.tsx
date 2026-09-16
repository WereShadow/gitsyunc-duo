import React, { useState, useEffect } from 'react';
import { BarChart3, Flame, Trophy, CheckCircle2, XCircle, TrendingUp, Award, Calendar } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { StreakData, CalendarHistory } from '../types';

export const StatisticsPage: React.FC = () => {
  const { duo } = useAuth();
  const [streak, setStreak] = useState<StreakData | null>(null);
  const [history, setHistory] = useState<CalendarHistory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [sData, hData] = await Promise.all([
          api.getStreak(),
          api.getCalendarHistory(),
        ]);
        setStreak(sData);
        setHistory(hData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const totalDays = (streak?.completed_days || 0) + (streak?.missed_days || 0);
  const completionRate = totalDays > 0 ? Math.round(((streak?.completed_days || 0) / totalDays) * 100) : 100;

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl lg:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <BarChart3 className="w-6 h-6 text-emerald-400" />
          <span>Accountability Statistics</span>
        </h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Comprehensive performance and habit consistency metrics for {duo?.name}.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Current Streak</span>
            <Flame className="w-4 h-4 text-amber-500 fill-amber-500" />
          </div>
          <span className="text-3xl font-extrabold text-white font-mono block">
            {streak?.current_streak || 0}
          </span>
          <span className="text-[11px] text-zinc-500 block">Consecutive completed days</span>
        </div>

        <div className="p-5 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Longest Streak</span>
            <Trophy className="w-4 h-4 text-yellow-400" />
          </div>
          <span className="text-3xl font-extrabold text-white font-mono block">
            {streak?.longest_streak || 0}
          </span>
          <span className="text-[11px] text-zinc-500 block">All-time record</span>
        </div>

        <div className="p-5 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Completion Rate</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-3xl font-extrabold text-emerald-400 font-mono block">
            {completionRate}%
          </span>
          <span className="text-[11px] text-zinc-500 block">Of target deadlines met</span>
        </div>

        <div className="p-5 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Total Days Completed</span>
            <Award className="w-4 h-4 text-purple-400" />
          </div>
          <span className="text-3xl font-extrabold text-white font-mono block">
            {streak?.completed_days || 0}
          </span>
          <span className="text-[11px] text-zinc-500 block">Mutual commitments kept</span>
        </div>
      </div>

      {/* Breakdown Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-4">
          <h3 className="text-sm font-bold text-white">Daily Habit Consistency</h3>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-zinc-400">Completed Days</span>
                <span className="text-emerald-400 font-mono font-bold">{streak?.completed_days || 0}</span>
              </div>
              <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full"
                  style={{ width: `${completionRate}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-zinc-400">Missed Deadlines</span>
                <span className="text-red-400 font-mono font-bold">{streak?.missed_days || 0}</span>
              </div>
              <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-red-500 rounded-full"
                  style={{ width: `${100 - completionRate}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-4">
          <h3 className="text-sm font-bold text-white">Duo Configuration Details</h3>
          <div className="space-y-2.5 text-xs text-zinc-300">
            <div className="flex justify-between py-1.5 border-b border-zinc-800">
              <span className="text-zinc-500">Project Mode:</span>
              <span className="font-mono font-bold text-purple-400">{duo?.project_mode}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-zinc-800">
              <span className="text-zinc-500">Configured Timezone:</span>
              <span className="font-mono">{duo?.timezone}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-zinc-800">
              <span className="text-zinc-500">Daily Cutoff Time:</span>
              <span className="font-mono">{duo?.deadline_time}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-zinc-500">Configured Grace Period:</span>
              <span className="font-mono text-emerald-400">{duo?.grace_period_minutes} minutes</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
