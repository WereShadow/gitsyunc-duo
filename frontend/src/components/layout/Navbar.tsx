import React, { useState } from 'react';
import { GitBranch, Flame, Users, Sparkles, LogOut, ArrowLeftRight, Check, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { NotificationDropdown } from '../common/NotificationDropdown';
import { SimulatePushModal } from '../common/SimulatePushModal';

interface NavbarProps {
  onRefresh?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onRefresh }) => {
  const { user, duo, logout, switchDemoUser } = useAuth();
  const [isSimulateOpen, setIsSimulateOpen] = useState(false);

  const isAlex = user?.email === 'alex@gitsync.dev';

  return (
    <header className="sticky top-0 z-30 h-16 bg-[#161b22]/90 backdrop-blur-md border-b border-[#30363d] px-4 lg:px-8 flex items-center justify-between">
      {/* Left: Brand & Duo Context */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-lg shadow-sm shadow-emerald-950/50">
            <GitBranch className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-extrabold text-white text-base tracking-tight flex items-center gap-1.5">
              GitSync <span className="text-emerald-400 font-mono">Duo</span>
            </span>
          </div>
        </div>

        {duo && (
          <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-[#30363d]">
            <span className="text-xs font-semibold text-zinc-200">{duo.name}</span>
            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full tracking-wider border ${
              duo.project_mode === 'SHARED'
                ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                : 'bg-blue-500/10 text-blue-300 border-blue-500/30'
            }`}>
              {duo.project_mode} MODE
            </span>
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-bold font-mono">
              <Flame className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
              <span>{duo.streak?.current_streak || 0}D</span>
            </div>
          </div>
        )}
      </div>

      {/* Right: Quick User Switcher, Simulator, Notifications & Profile */}
      <div className="flex items-center gap-3">
        {/* Quick Demo Switcher (Alex <-> Morgan) */}
        <div className="flex items-center bg-[#0d1117] border border-[#30363d] rounded-lg p-0.5 text-xs">
          <button
            onClick={() => switchDemoUser('alex@gitsync.dev')}
            className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
              isAlex
                ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
            title="Switch to Alex (Backend User A)"
          >
            {isAlex && <Check className="w-3 h-3" />}
            <span>Alex</span>
          </button>
          <button
            onClick={() => switchDemoUser('morgan@gitsync.dev')}
            className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
              !isAlex
                ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
            title="Switch to Morgan (Frontend User B)"
          >
            {!isAlex && <Check className="w-3 h-3" />}
            <span>Morgan</span>
          </button>
        </div>

        {/* Simulate Push Button */}
        <button
          onClick={() => setIsSimulateOpen(true)}
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>Simulate Push</span>
        </button>

        {/* Notifications */}
        <NotificationDropdown />

        {/* User Avatar & Logout */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-[#30363d]">
          <img
            src={user?.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${user?.email}`}
            alt={user?.full_name}
            className="w-8 h-8 rounded-full border border-[#30363d] object-cover bg-zinc-800"
          />
          <div className="hidden lg:block text-left">
            <p className="text-xs font-semibold text-zinc-200 leading-none">{user?.full_name}</p>
            <p className="text-[10px] text-zinc-500 font-mono mt-0.5">{user?.github_username || 'No GitHub'}</p>
          </div>
          <button
            onClick={logout}
            className="p-1.5 text-zinc-400 hover:text-red-400 rounded-lg hover:bg-zinc-800/80 transition-colors"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      <SimulatePushModal
        isOpen={isSimulateOpen}
        onClose={() => setIsSimulateOpen(false)}
        onSuccess={() => onRefresh && onRefresh()}
      />
    </header>
  );
};
