import React, { useState } from 'react';
import { Users, GitBranch, Clock, Globe, ArrowRight, ShieldCheck, Check, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface CreateDuoPageProps {
  onNavigate: (page: string) => void;
}

export const CreateDuoPage: React.FC<CreateDuoPageProps> = ({ onNavigate }) => {
  const { refreshState } = useAuth();
  const [name, setName] = useState('Super Builders');
  const [projectMode, setProjectMode] = useState<'SEPARATE' | 'SHARED'>('SHARED');
  const [workflowType, setWorkflowType] = useState<'SEPARATE_BRANCHES' | 'SAME_BRANCH' | 'PULL_REQUESTS'>('SEPARATE_BRANCHES');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [deadlineTime, setDeadlineTime] = useState('23:59');
  const [gracePeriod, setGracePeriod] = useState(30);
  const [loading, setLoading] = useState(false);
  const [createdDuo, setCreatedDuo] = useState<any | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const duo = await api.createDuo({
        name,
        project_mode: projectMode,
        workflow_type: workflowType,
        timezone,
        deadline_time: deadlineTime,
        grace_period_minutes: gracePeriod,
      });
      setCreatedDuo(duo);
      await refreshState();
    } catch (err: any) {
      alert(err.message || 'Failed to create Duo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-[#161b22] border border-[#30363d] rounded-2xl p-8 shadow-2xl space-y-6">
        {createdDuo ? (
          <div className="text-center space-y-6 animate-in fade-in duration-200">
            <div className="inline-flex p-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-2xl">
              <Sparkles className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Duo Created Successfully!</h2>
              <p className="text-xs text-zinc-400 mt-1">Share this invite code with your partner to begin accountability.</p>
            </div>

            <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold text-zinc-500 block text-left">Partner Invite Code</span>
                <span className="text-2xl font-extrabold text-emerald-400 font-mono tracking-wider">{createdDuo.invite_code}</span>
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(createdDuo.invite_code)}
                className="px-3 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg border border-zinc-700 transition-colors"
              >
                Copy Code
              </button>
            </div>

            <button
              onClick={() => onNavigate('dashboard')}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <span>Enter Duo Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <>
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">Create a New Duo</h1>
              <p className="text-xs text-zinc-400">Establish daily accountability with your partner.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Duo Name */}
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Duo Team Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. NextGen Builders"
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3.5 py-2.5 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Project Mode Selection */}
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-2">Project Architecture Mode</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div
                    onClick={() => setProjectMode('SEPARATE')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      projectMode === 'SEPARATE'
                        ? 'bg-emerald-500/10 border-emerald-500/40 shadow-sm'
                        : 'bg-[#0d1117] border-[#30363d] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-zinc-100">Separate Projects</span>
                      {projectMode === 'SEPARATE' && <Check className="w-4 h-4 text-emerald-400" />}
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      Each person works on their own separate GitHub repository. Day completes when both push.
                    </p>
                  </div>

                  <div
                    onClick={() => setProjectMode('SHARED')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      projectMode === 'SHARED'
                        ? 'bg-purple-500/10 border-purple-500/40 shadow-sm'
                        : 'bg-[#0d1117] border-[#30363d] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-zinc-100">Shared Project</span>
                      {projectMode === 'SHARED' && <Check className="w-4 h-4 text-purple-400" />}
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      Both work on different parts of the same repo. Includes peer review and automated project checks.
                    </p>
                  </div>
                </div>
              </div>

              {/* Workflow selection for shared project */}
              {projectMode === 'SHARED' && (
                <div className="p-3.5 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-2">
                  <label className="block text-[11px] font-semibold text-purple-400 uppercase tracking-wider">
                    Shared Git Workflow
                  </label>
                  <select
                    value={workflowType}
                    onChange={e => setWorkflowType(e.target.value as any)}
                    className="w-full bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-purple-500"
                  >
                    <option value="SEPARATE_BRANCHES">Separate Branches (e.g. backend / frontend)</option>
                    <option value="SAME_BRANCH">Same Branch (main - tracked by author login)</option>
                    <option value="PULL_REQUESTS">Pull Requests into main</option>
                  </select>
                </div>
              )}

              {/* Timezone & Deadline */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Timezone</label>
                  <select
                    value={timezone}
                    onChange={e => setTimezone(e.target.value)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
                  >
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                    <option value="America/Los_Angeles">America/Los_Angeles (PST)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="UTC">UTC</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Daily Deadline</label>
                  <input
                    type="time"
                    value={deadlineTime}
                    onChange={e => setDeadlineTime(e.target.value)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
              </div>

              {/* Grace Period */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-zinc-300">Grace Period (Minutes)</label>
                  <span className="text-xs text-emerald-400 font-mono">{gracePeriod} mins</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={120}
                  step={15}
                  value={gracePeriod}
                  onChange={e => setGracePeriod(Number(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => onNavigate('dashboard')}
                  className="px-4 py-2.5 text-xs font-semibold text-zinc-400 hover:text-white rounded-xl hover:bg-zinc-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition-colors shadow-sm disabled:opacity-50"
                >
                  {loading ? 'Creating Duo...' : 'Create Duo & Get Invite Code'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
};
