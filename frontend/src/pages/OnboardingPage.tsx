import React, { useState } from 'react';
import { GitBranch, CheckCircle2, ArrowRight, ShieldCheck, Users, Terminal as Github } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface OnboardingPageProps {
  onNavigate: (page: string) => void;
}

export const OnboardingPage: React.FC<OnboardingPageProps> = ({ onNavigate }) => {
  const { user, refreshState } = useAuth();
  const [step, setStep] = useState(1);
  const [projectName, setProjectName] = useState('Campus AI Assistant');
  const [repoOwner, setRepoOwner] = useState(user?.github_username || 'campus-ai');
  const [repoName, setRepoName] = useState('assistant');
  const [branch, setBranch] = useState('main');
  const [assignedArea, setAssignedArea] = useState('Backend API & Services');
  const [githubUsername, setGithubUsername] = useState(user?.github_username || 'alexrivera-dev');
  const [githubToken, setGithubToken] = useState('ghp_demo_user_token');
  const [loading, setLoading] = useState(false);

  const handleConnectGitHub = async () => {
    setLoading(true);
    try {
      await api.connectGitHubToken({
        github_username: githubUsername,
        access_token: githubToken,
      });
      await refreshState();
      setStep(3);
    } catch (err: any) {
      alert(err.message || 'GitHub connection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProject = async () => {
    setLoading(true);
    try {
      await api.createOrUpdateProject({
        project_name: projectName,
        github_repo_owner: repoOwner,
        github_repo_name: repoName,
        branch,
        assigned_area: assignedArea,
        verification_enabled: true,
      });
      onNavigate('dashboard');
    } catch (err: any) {
      // If user is not yet in duo, route to duo choice
      onNavigate('create-duo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-[#161b22] border border-[#30363d] rounded-2xl p-8 shadow-2xl space-y-6">
        {/* Step Indicator */}
        <div className="flex items-center justify-between border-b border-[#30363d] pb-4">
          <div className="flex items-center gap-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  step === s
                    ? 'bg-emerald-600 text-white'
                    : step > s
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-zinc-800 text-zinc-500'
                }`}
              >
                {step > s ? '✓' : s}
              </div>
            ))}
          </div>
          <span className="text-xs text-zinc-400 font-mono">Step {step} of 3</span>
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white">Connect GitHub Account</h2>
            <p className="text-xs text-zinc-400 leading-relaxed">
              We verify your daily accountability requirements through your commits and pull requests.
            </p>

            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">GitHub Username</label>
                <input
                  type="text"
                  value={githubUsername}
                  onChange={e => setGithubUsername(e.target.value)}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">
                  GitHub Personal Access Token (or test token)
                </label>
                <input
                  type="password"
                  value={githubToken}
                  onChange={e => setGithubToken(e.target.value)}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                />
                <p className="text-[10px] text-zinc-500 mt-1">
                  Tokens are encrypted with Fernet AES-128 and never transmitted to the browser.
                </p>
              </div>
            </div>

            <button
              onClick={handleConnectGitHub}
              disabled={loading}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <span>Connect & Continue</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white">Join or Create a Duo</h2>
            <p className="text-xs text-zinc-400 leading-relaxed">
              GitSync is designed for two people. Start a new duo or join your partner's existing code.
            </p>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                onClick={() => onNavigate('create-duo')}
                className="p-4 bg-[#0d1117] hover:bg-zinc-800 border border-[#30363d] rounded-xl text-left space-y-1 transition-all"
              >
                <Users className="w-5 h-5 text-emerald-400 mb-2" />
                <span className="text-xs font-bold text-white block">Create Duo</span>
                <span className="text-[11px] text-zinc-400 block">Start a team and get an invite code.</span>
              </button>

              <button
                onClick={() => onNavigate('join-duo')}
                className="p-4 bg-[#0d1117] hover:bg-zinc-800 border border-[#30363d] rounded-xl text-left space-y-1 transition-all"
              >
                <ShieldCheck className="w-5 h-5 text-purple-400 mb-2" />
                <span className="text-xs font-bold text-white block">Join Duo</span>
                <span className="text-[11px] text-zinc-400 block">Enter an 8-character invite code.</span>
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white">Select Accountability Project</h2>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Configure the repository and branch that will be monitored for your daily commits.
            </p>

            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">Project Name</label>
                <input
                  type="text"
                  value={projectName}
                  onChange={e => setProjectName(e.target.value)}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1">Repo Owner</label>
                  <input
                    type="text"
                    value={repoOwner}
                    onChange={e => setRepoOwner(e.target.value)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1">Repo Name</label>
                  <input
                    type="text"
                    value={repoName}
                    onChange={e => setRepoName(e.target.value)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1">Monitored Branch</label>
                  <input
                    type="text"
                    value={branch}
                    onChange={e => setBranch(e.target.value)}
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1">Assigned Area</label>
                  <input
                    type="text"
                    value={assignedArea}
                    onChange={e => setAssignedArea(e.target.value)}
                    placeholder="e.g. Backend API"
                    className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-3 py-2 text-xs text-zinc-100"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleSaveProject}
              disabled={loading}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <span>Save & Complete Onboarding</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
