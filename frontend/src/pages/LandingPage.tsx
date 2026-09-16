import React from 'react';
import { GitBranch, Flame, ShieldCheck, Users, ArrowRight, CheckCircle2, GitPullRequest, Code2, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface LandingPageProps {
  onNavigate: (page: string) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const { switchDemoUser } = useAuth();

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#c9d1d9] flex flex-col selection:bg-emerald-500 selection:text-white">
      {/* Navigation Header */}
      <header className="h-16 border-b border-[#30363d] px-6 lg:px-12 flex items-center justify-between bg-[#161b22]/70 backdrop-blur-md sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-lg shadow-sm">
            <GitBranch className="w-5 h-5 text-white" />
          </div>
          <span className="font-extrabold text-lg text-white tracking-tight">
            GitSync <span className="text-emerald-400 font-mono">Duo</span>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('login')}
            className="px-3.5 py-1.5 text-xs font-semibold text-zinc-300 hover:text-white rounded-lg hover:bg-zinc-800 transition-colors"
          >
            Sign In
          </button>
          <button
            onClick={() => onNavigate('register')}
            className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors shadow-sm"
          >
            Get Started
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-16 lg:py-24 max-w-5xl mx-auto space-y-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold animate-pulse-subtle">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Two-Developer Daily GitHub Accountability</span>
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-[1.1]">
          Build together.<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-blue-400">
            Ship every single day.
          </span>
        </h1>

        <p className="text-base sm:text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          A two-person daily accountability platform where daily tasks are marked <span className="text-emerald-400 font-semibold">COMPLETED</span> only when <span className="text-zinc-200 font-semibold">BOTH</span> members verify their GitHub activity. No manual checkoffs. The backend is the sole authority.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto pt-2">
          <button
            onClick={() => onNavigate('create-duo')}
            className="w-full sm:w-auto px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold rounded-xl transition-all shadow-lg shadow-emerald-900/30 flex items-center justify-center gap-2"
          >
            <Users className="w-4 h-4" />
            <span>Create Duo</span>
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => onNavigate('join-duo')}
            className="w-full sm:w-auto px-6 py-3 bg-[#161b22] hover:bg-[#1f242c] text-zinc-200 border border-[#30363d] text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <span>Join Duo with Code</span>
          </button>
          <button
            onClick={() => switchDemoUser('alex@gitsync.dev')}
            className="w-full sm:w-auto px-5 py-3 bg-gradient-to-r from-purple-900/50 to-indigo-900/50 hover:from-purple-800/60 hover:to-indigo-800/60 text-purple-200 border border-purple-500/30 text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <Sparkles className="w-4 h-4 text-purple-300" />
            <span>Try Live Interactive Demo</span>
          </button>
        </div>

        {/* Live Rule Preview Card */}
        <div className="w-full max-w-3xl mt-12 p-6 bg-[#161b22] border border-[#30363d] rounded-2xl text-left shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-[#30363d] pb-3">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/80" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <span className="w-3 h-3 rounded-full bg-green-500/80" />
              <span className="text-xs font-mono text-zinc-500 ml-2">core-completion-engine.ts</span>
            </div>
            <div className="flex items-center gap-1 text-xs text-emerald-400 font-mono font-bold">
              <Flame className="w-4 h-4 fill-emerald-500 text-emerald-500" />
              <span>14 DAY STREAK</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-zinc-200">YOU (Alex)</span>
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 3 Commits ✓
                </span>
              </div>
              <p className="text-xs text-zinc-400">Implement FastAPI JWT Authentication</p>
              <div className="text-[10px] text-zinc-500 font-mono">Branch: backend • Status: Approved</div>
            </div>

            <div className="p-4 bg-[#0d1117] border border-[#30363d] rounded-xl space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-zinc-200">PARTNER (Morgan)</span>
                <span className="text-amber-400 font-medium">Waiting for push...</span>
              </div>
              <p className="text-xs text-zinc-400">Build Authentication UI & Review Modals</p>
              <div className="text-[10px] text-zinc-500 font-mono">Branch: frontend • Status: In Progress</div>
            </div>
          </div>

          <div className="p-3 bg-zinc-900/80 border border-zinc-800 rounded-xl flex items-center justify-between text-xs">
            <span className="text-zinc-400">DUO COMPLETION STATUS:</span>
            <span className="text-amber-400 font-bold font-mono uppercase">WAITING FOR PARTNER</span>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left pt-8">
          <div className="p-6 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-3">
            <div className="p-2.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl w-fit">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-white text-base">Authoritative Verification</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Users can NEVER manually mark a day complete. Commits are verified via GitHub REST API and secure HMAC webhooks.
            </p>
          </div>

          <div className="p-6 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-3">
            <div className="p-2.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-xl w-fit">
              <GitPullRequest className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-white text-base">Shared Project Mode</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Work on the same repo across branches or pull requests. Features built-in peer review, commit diffs, and automated checks.
            </p>
          </div>

          <div className="p-6 bg-[#161b22] border border-[#30363d] rounded-2xl space-y-3">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-xl w-fit">
              <Flame className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-white text-base">Timezone & Streak Protection</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Daily task boundaries align with your duo's configured timezone (default Asia/Kolkata) with configurable grace periods.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#30363d] py-6 text-center text-xs text-zinc-500">
        GitSync Duo © 2026 • Two-person daily accountability platform
      </footer>
    </div>
  );
};
