import React, { useState, useEffect } from 'react';
import { Calendar as CalendarIcon, CheckCircle2, Clock, XCircle, ChevronRight, X, Flame } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { CalendarHistory, CalendarDayItem } from '../types';

export const CalendarPage: React.FC = () => {
  const { duo } = useAuth();
  const [history, setHistory] = useState<CalendarHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState<CalendarDayItem | null>(null);

  const fetchCalendar = async () => {
    try {
      const data = await api.getCalendarHistory();
      setHistory(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendar();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-[#238636] border-[#3fb950] hover:ring-2 hover:ring-emerald-400';
      case 'PARTIAL':
        return 'bg-[#d29922] border-yellow-500 hover:ring-2 hover:ring-yellow-400';
      case 'MISSED':
        return 'bg-[#da3633] border-red-500 hover:ring-2 hover:ring-red-400';
      default:
        return 'bg-[#21262d] border-[#30363d] hover:bg-zinc-700';
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <CalendarIcon className="w-6 h-6 text-emerald-400" />
            <span>Accountability Calendar</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            GitHub contribution grid tracking mutual daily consistency.
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs bg-[#161b22] px-3 py-1.5 rounded-xl border border-[#30363d]">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#238636] border border-[#3fb950]" />
            <span className="text-zinc-300">Both Completed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#d29922] border border-yellow-500" />
            <span className="text-zinc-300">Partial</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#da3633] border border-red-500" />
            <span className="text-zinc-300">Missed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#21262d] border border-[#30363d]" />
            <span className="text-zinc-500">None</span>
          </div>
        </div>
      </div>

      {/* Main Contribution Grid Card */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-[#30363d] pb-4">
          <div>
            <span className="text-xs text-zinc-400 block">Duo Consistency Grid (Past 60 Days)</span>
            <span className="text-sm font-bold text-white">{duo?.name}</span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-zinc-500 block text-[10px]">CURRENT STREAK</span>
              <span className="text-emerald-400 font-bold">{history?.current_streak || 0} Days</span>
            </div>
            <div>
              <span className="text-zinc-500 block text-[10px]">TOTAL COMPLETED</span>
              <span className="text-white font-bold">{history?.total_completed || 0} Days</span>
            </div>
          </div>
        </div>

        {/* The Contribution Heatmap Grid */}
        <div className="overflow-x-auto pb-2">
          <div className="grid grid-flow-col grid-rows-7 gap-1.5 min-w-[650px]">
            {history?.days.map((day) => (
              <button
                key={day.date}
                onClick={() => setSelectedDay(day)}
                title={`${day.date}: ${day.status}`}
                className={`w-4 h-4 rounded-sm border transition-all cursor-pointer ${getStatusColor(day.status)}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Day Details Modal / Drawer */}
      {selectedDay && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#30363d] pb-3">
              <div>
                <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase block">Daily Activity Inspection</span>
                <h3 className="text-base font-bold text-white">{selectedDay.date}</h3>
              </div>
              <button
                onClick={() => setSelectedDay(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center p-3 bg-[#0d1117] rounded-xl border border-[#30363d]">
                <span className="text-zinc-400">Day Outcome:</span>
                <span className={`font-bold px-2 py-0.5 rounded-full ${
                  selectedDay.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                  selectedDay.status === 'PARTIAL' ? 'bg-yellow-500/20 text-yellow-400' :
                  selectedDay.status === 'MISSED' ? 'bg-red-500/20 text-red-400' : 'bg-zinc-800 text-zinc-400'
                }`}>
                  {selectedDay.status}
                </span>
              </div>

              {selectedDay.task_title && (
                <div className="p-3 bg-[#0d1117] rounded-xl border border-[#30363d]">
                  <span className="text-zinc-500 block text-[10px] uppercase font-bold mb-0.5">Task Objective</span>
                  <p className="font-semibold text-zinc-200">{selectedDay.task_title}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 bg-[#0d1117] rounded-xl border border-[#30363d] text-center">
                  <span className="text-zinc-500 block text-[10px]">User A (Alex)</span>
                  <span className={`font-bold mt-1 inline-block ${
                    selectedDay.user_a_verified ? 'text-emerald-400' : 'text-zinc-500'
                  }`}>
                    {selectedDay.user_a_verified ? '✓ Satisfied' : 'Pending/None'}
                  </span>
                </div>

                <div className="p-3 bg-[#0d1117] rounded-xl border border-[#30363d] text-center">
                  <span className="text-zinc-500 block text-[10px]">User B (Morgan)</span>
                  <span className={`font-bold mt-1 inline-block ${
                    selectedDay.user_b_verified ? 'text-emerald-400' : 'text-zinc-500'
                  }`}>
                    {selectedDay.user_b_verified ? '✓ Satisfied' : 'Pending/None'}
                  </span>
                </div>
              </div>

              {selectedDay.completed_at && (
                <p className="text-[11px] text-zinc-500 text-center font-mono pt-1">
                  Completed at: {new Date(selectedDay.completed_at).toLocaleString()}
                </p>
              )}
            </div>

            <button
              onClick={() => setSelectedDay(null)}
              className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-bold text-xs rounded-xl"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
