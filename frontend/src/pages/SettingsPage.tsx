import React, { useState, useEffect } from 'react';
import {
  Settings, Copy, Check, RefreshCw, Shield, Clock,
  GitBranch, Users, Eye, EyeOff, AlertTriangle, CheckCircle, Terminal,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

interface SettingsPageProps {
  onNavigate?: (page: string) => void;
}

const SettingsPage: React.FC<SettingsPageProps> = () => {
  const { user, duo, refreshState } = useAuth();

  // Duo settings — sourced from Duo object top-level fields
  const [timezone, setTimezone] = useState('UTC');
  const [deadlineTime, setDeadlineTime] = useState('23:59');
  const [gracePeriodMinutes, setGracePeriodMinutes] = useState(60);
  const [projectMode, setProjectMode] = useState<'SEPARATE' | 'SHARED'>('SEPARATE');

  // Project settings
  const [repoOwner, setRepoOwner] = useState('');
  const [repoName, setRepoName] = useState('');
  const [repoBranch, setRepoBranch] = useState('main');

  // GitHub connect
  const [githubToken, setGithubToken] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [githubStatus, setGithubStatus] = useState<any>(null);

  // UI state
  const [copiedCode, setCopiedCode] = useState(false);
  const [savingDuo, setSavingDuo] = useState(false);
  const [savingProject, setSavingProject] = useState(false);
  const [savingGithub, setSavingGithub] = useState(false);
  const [duoSaved, setDuoSaved] = useState(false);
  const [projectSaved, setProjectSaved] = useState(false);
  const [githubSaved, setGithubSaved] = useState(false);
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<any[]>([]);

  const timezones = [
    'UTC', 'America/New_York', 'America/Chicago', 'America/Denver',
    'America/Los_Angeles', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
    'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Australia/Sydney',
  ];

  useEffect(() => {
    if (duo) {
      setTimezone(duo.timezone || 'UTC');
      setDeadlineTime(duo.deadline_time || '23:59');
      setGracePeriodMinutes(duo.grace_period_minutes ?? 60);
      setProjectMode(duo.project_mode || 'SEPARATE');
    }
    loadGithubStatus();
    loadProjects();
  }, [duo?.id]);

  const loadGithubStatus = async () => {
    try {
      const status = await api.getGitHubStatus();
      setGithubStatus(status);
      if (status?.github_username) setGithubUsername(status.github_username);
    } catch {}
  };

  const loadProjects = async () => {
    if (!duo) return;
    try {
      const data = await api.getDuoProjects(duo.id);
      setProjects(data || []);
      if (data && data.length > 0) {
        const proj = data[0];
        setRepoOwner(proj.github_repo_owner || '');
        setRepoName(proj.github_repo_name || '');
        setRepoBranch(proj.branch || 'main');
      }
    } catch {}
  };

  const copyInviteCode = async () => {
    if (!duo?.invite_code) return;
    await navigator.clipboard.writeText(duo.invite_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const saveDuoSettings = async () => {
    if (!duo) return;
    setSavingDuo(true);
    setError('');
    try {
      await api.updateDuoSettings(duo.id, {
        timezone,
        deadline_time: deadlineTime,
        grace_period_minutes: gracePeriodMinutes,
        project_mode: projectMode,
      } as any);
      await refreshState();
      setDuoSaved(true);
      setTimeout(() => setDuoSaved(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Failed to save duo settings');
    } finally {
      setSavingDuo(false);
    }
  };

  const saveProjectSettings = async () => {
    if (!duo) return;
    setSavingProject(true);
    setError('');
    try {
      await api.createOrUpdateProject({
        duo_id: duo.id,
        project_name: `${duo.name} Project`,
        github_repo_owner: repoOwner,
        github_repo_name: repoName,
        github_repo_full_name: `${repoOwner}/${repoName}`,
        branch: repoBranch,
        verification_enabled: true,
      } as any);
      await loadProjects();
      setProjectSaved(true);
      setTimeout(() => setProjectSaved(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Failed to save project settings');
    } finally {
      setSavingProject(false);
    }
  };

  const connectGitHub = async () => {
    if (!githubToken.trim() || !githubUsername.trim()) {
      setError('Please provide both your GitHub username and Personal Access Token');
      return;
    }
    setSavingGithub(true);
    setError('');
    try {
      await api.connectGitHubToken({ github_username: githubUsername, access_token: githubToken });
      await loadGithubStatus();
      setGithubToken('');
      setGithubSaved(true);
      setTimeout(() => setGithubSaved(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Failed to connect GitHub account');
    } finally {
      setSavingGithub(false);
    }
  };

  const isOwner = duo?.members?.some(
    (m: any) => m.user_id === user?.id && (m.role === 'CREATOR' || m.role === 'owner')
  );

  const gracePeriodHours = Math.round(gracePeriodMinutes / 60);

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Settings className="text-blue-400" size={28} />
          Settings
        </h1>
        <p className="text-slate-400 mt-1">Configure your duo, project, and GitHub integration.</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="text-red-400 mt-0.5 shrink-0" size={18} />
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* Invite Code */}
      {duo && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
            <Users size={20} className="text-purple-400" />
            Invite Code
          </h2>
          <p className="text-slate-400 text-sm mb-4">
            Share this code with your duo partner to join <span className="text-white font-medium">{duo.name}</span>.
          </p>
          <div className="flex items-center gap-3">
            <div className="flex-1 bg-slate-900 border border-slate-600 rounded-xl px-4 py-3 font-mono text-2xl text-center tracking-widest text-purple-300 font-bold">
              {duo.invite_code}
            </div>
            <button
              onClick={copyInviteCode}
              className="px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors flex items-center gap-2"
            >
              {copiedCode ? <Check size={18} /> : <Copy size={18} />}
              {copiedCode ? 'Copied!' : 'Copy'}
            </button>
          </div>
          {duo.members && (
            <div className="mt-4 flex items-center gap-2">
              <span className="text-slate-500 text-xs">Members:</span>
              <span className="text-slate-300 text-xs">
                {duo.members.length}/2 joined
                {duo.members.length === 2 && ' · Duo is full'}
              </span>
            </div>
          )}
        </div>
      )}

      {/* GitHub Integration */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
          <Terminal size={20} className="text-slate-300" />
          GitHub Integration
        </h2>
        <p className="text-slate-400 text-sm mb-4">
          Connect your GitHub account to enable activity verification.
        </p>

        {githubStatus?.connected && (
          <div className="flex items-center gap-3 bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-4">
            <CheckCircle className="text-green-400 shrink-0" size={20} />
            <div>
              <p className="text-green-300 font-medium">Connected as <span className="font-bold">@{githubStatus.github_username}</span></p>
              <p className="text-green-400/70 text-xs mt-0.5">GitHub account is active and verified</p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-1.5">GitHub Username</label>
            <input
              type="text"
              value={githubUsername}
              onChange={e => setGithubUsername(e.target.value)}
              placeholder="your-github-username"
              className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-1.5">
              Personal Access Token
              <span className="ml-2 text-slate-500 text-xs font-normal">(needs repo + read:user scopes)</span>
            </label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={githubToken}
                onChange={e => setGithubToken(e.target.value)}
                placeholder="ghp_••••••••••••••••••••••••••••••••••••••"
                className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors pr-12"
              />
              <button
                type="button"
                onClick={() => setShowToken(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
              >
                {showToken ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <p className="text-slate-500 text-xs mt-1.5">
              Your token is encrypted at rest and never exposed in the UI again after saving.
            </p>
          </div>
          <button
            onClick={connectGitHub}
            disabled={savingGithub}
            className="flex items-center gap-2 px-5 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-colors disabled:opacity-50"
          >
            {savingGithub ? <RefreshCw size={16} className="animate-spin" /> : <Terminal size={16} />}
            {githubSaved ? 'Connected ✓' : (githubStatus?.connected ? 'Reconnect GitHub' : 'Connect GitHub')}
          </button>
        </div>
      </div>

      {/* Duo Settings */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Clock size={20} className="text-blue-400" />
              Duo Settings
            </h2>
            <p className="text-slate-400 text-sm mt-0.5">
              Daily deadline and completion rules for your duo.
            </p>
          </div>
          {!isOwner && (
            <span className="text-xs text-slate-500 bg-slate-700/50 px-3 py-1 rounded-full">
              Owner only
            </span>
          )}
        </div>

        <div className="space-y-5">
          {/* Project Mode */}
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-2">Project Mode</label>
            <div className="grid grid-cols-2 gap-3">
              {(['SEPARATE', 'SHARED'] as const).map(mode => (
                <button
                  key={mode}
                  onClick={() => isOwner && setProjectMode(mode)}
                  disabled={!isOwner}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    projectMode === mode
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 bg-slate-900 hover:border-slate-500'
                  } disabled:cursor-not-allowed`}
                >
                  <p className={`font-semibold text-sm ${projectMode === mode ? 'text-blue-300' : 'text-slate-300'}`}>
                    {mode === 'SEPARATE' ? '⚡ Separate' : '🤝 Shared'}
                  </p>
                  <p className="text-slate-500 text-xs mt-1">
                    {mode === 'SEPARATE'
                      ? 'Each member commits independently. Day complete when both push.'
                      : 'Same repo. Requires peer code review + CI/CD checks to complete.'}
                  </p>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">Timezone</label>
              <select
                value={timezone}
                onChange={e => setTimezone(e.target.value)}
                disabled={!isOwner}
                className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
              >
                {timezones.map(tz => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">Daily Deadline</label>
              <input
                type="time"
                value={deadlineTime}
                onChange={e => setDeadlineTime(e.target.value)}
                disabled={!isOwner}
                className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 text-sm font-medium mb-1.5">
              Grace Period: <span className="text-blue-400">{gracePeriodHours}h ({gracePeriodMinutes}m)</span>
            </label>
            <input
              type="range"
              min={0}
              max={360}
              step={30}
              value={gracePeriodMinutes}
              onChange={e => isOwner && setGracePeriodMinutes(Number(e.target.value))}
              disabled={!isOwner}
              className="w-full accent-blue-500 disabled:opacity-50"
            />
            <div className="flex justify-between text-slate-500 text-xs mt-1">
              <span>0h (strict)</span>
              <span>6h</span>
            </div>
          </div>

          <button
            onClick={saveDuoSettings}
            disabled={savingDuo || !isOwner}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors disabled:opacity-50"
          >
            {savingDuo ? <RefreshCw size={16} className="animate-spin" /> : <Shield size={16} />}
            {duoSaved ? 'Saved ✓' : 'Save Duo Settings'}
          </button>
        </div>
      </div>

      {/* Project / Repository Settings */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
          <GitBranch size={20} className="text-green-400" />
          Repository Settings
        </h2>
        <p className="text-slate-400 text-sm mb-4">
          Set the GitHub repository GitSync Duo will monitor for commits.
        </p>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">Repository Owner</label>
              <input
                type="text"
                value={repoOwner}
                onChange={e => setRepoOwner(e.target.value)}
                placeholder="e.g. octocat"
                className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">Repository Name</label>
              <input
                type="text"
                value={repoName}
                onChange={e => setRepoName(e.target.value)}
                placeholder="e.g. my-project"
                className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
          </div>
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-1.5">Branch</label>
            <input
              type="text"
              value={repoBranch}
              onChange={e => setRepoBranch(e.target.value)}
              placeholder="main"
              className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          {repoOwner && repoName && (
            <a
              href={`https://github.com/${repoOwner}/${repoName}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-sm transition-colors"
            >
              <GitBranch size={14} />
              github.com/{repoOwner}/{repoName}
            </a>
          )}
          <button
            onClick={saveProjectSettings}
            disabled={savingProject}
            className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-xl transition-colors disabled:opacity-50"
          >
            {savingProject ? <RefreshCw size={16} className="animate-spin" /> : <GitBranch size={16} />}
            {projectSaved ? 'Saved ✓' : 'Save Repository'}
          </button>
        </div>
      </div>

      {/* Danger Zone */}
      {isOwner && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-red-400 mb-1">Danger Zone</h2>
          <p className="text-slate-400 text-sm mb-4">
            These actions are irreversible. Please proceed with caution.
          </p>
          <button
            className="px-5 py-2.5 border border-red-500/40 text-red-400 hover:bg-red-500/10 rounded-xl transition-colors text-sm"
            onClick={() => {
              if (window.confirm('Are you sure you want to reset the duo streak? This cannot be undone.')) {
                alert('Contact support to reset duo data.');
              }
            }}
          >
            Reset Duo Streak
          </button>
        </div>
      )}
    </div>
  );
};

export default SettingsPage;
