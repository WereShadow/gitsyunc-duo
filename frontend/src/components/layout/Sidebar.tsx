import React from 'react';
import {
  LayoutDashboard,
  CheckSquare,
  GitCommit,
  Calendar,
  History,
  BarChart3,
  Settings,
  Flame,
  UserCheck,
  ShieldCheck,
  ChevronRight,
  ExternalLink,
  FolderKanban
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange }) => {
  const { user, duo } = useAuth();

  const partner = duo?.members.find(m => m.user_id !== user?.id);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects', label: 'Project Pipeline', icon: FolderKanban },
    { id: 'task', label: "Today's Task", icon: CheckSquare },
    { id: 'github', label: 'GitHub Activity', icon: GitCommit },
    { id: 'calendar', label: 'Calendar', icon: Calendar },
    { id: 'history', label: 'History', icon: History },
    { id: 'statistics', label: 'Statistics', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-[#30363d] bg-[#161b22] flex flex-col shrink-0 h-[calc(100vh-4rem)] select-none">
      {/* Navigation items */}
      <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-zinc-800 text-white border border-[#30363d] shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-400'}`} />
              <span className="flex-1 text-left">{item.label}</span>
              {isActive && <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400" />}
            </button>
          );
        })}
      </div>

      {/* Partner Status Box */}
      {partner && (
        <div className="p-3 border-t border-[#30363d]">
          <div className="p-3 bg-[#0d1117] border border-[#30363d] rounded-xl">
            <div className="flex items-center justify-between text-[11px] text-zinc-400 font-medium mb-2">
              <span>Accountability Partner</span>
              <span className="text-[10px] text-emerald-400 font-mono">Duo Active</span>
            </div>
            <div className="flex items-center gap-2.5">
              <img
                src={partner.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${partner.email}`}
                alt={partner.full_name}
                className="w-8 h-8 rounded-full border border-zinc-700 bg-zinc-800"
              />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-zinc-200 truncate">{partner.full_name}</p>
                <p className="text-[10px] text-zinc-500 font-mono truncate">@{partner.github_username || 'no-gh'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Streak Widget */}
      <div className="p-3 border-t border-[#30363d] bg-[#0d1117]/50">
        <div className="p-3 bg-gradient-to-br from-amber-500/10 via-zinc-900 to-emerald-500/10 border border-amber-500/20 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Flame className="w-5 h-5 text-amber-500 fill-amber-500 animate-pulse" />
              <div>
                <span className="text-xs font-bold text-zinc-100">
                  {duo?.streak?.current_streak || 0} Day Streak
                </span>
                <p className="text-[10px] text-zinc-400">Longest: {duo?.streak?.longest_streak || 0} days</p>
              </div>
            </div>
          </div>
          <div className="mt-2 text-[10px] text-zinc-400 flex items-center justify-between border-t border-zinc-800/80 pt-2">
            <span>Completed: {duo?.streak?.completed_days || 0}</span>
            <span>Missed: {duo?.streak?.missed_days || 0}</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
