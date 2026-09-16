import React, { useState } from 'react';
import { Users, ArrowRight, AlertCircle, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface JoinDuoPageProps {
  onNavigate: (page: string) => void;
}

export const JoinDuoPage: React.FC<JoinDuoPageProps> = ({ onNavigate }) => {
  const { refreshState } = useAuth();
  const [inviteCode, setInviteCode] = useState('SYNC-7721');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.joinDuo(inviteCode.trim().toUpperCase());
      await refreshState();
      onNavigate('dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to join Duo. Check code or capacity.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-2xl p-8 shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-xl shadow-md">
            <Users className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Join a Duo</h1>
          <p className="text-xs text-zinc-400">Enter the invite code shared by your accountability partner.</p>
        </div>

        <form onSubmit={handleJoin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Invite Code</label>
            <input
              type="text"
              required
              value={inviteCode}
              onChange={e => setInviteCode(e.target.value.toUpperCase())}
              placeholder="e.g. SYNC-7721"
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-xl px-4 py-3 text-center text-lg font-mono font-bold tracking-widest text-emerald-400 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
          >
            {loading ? 'Joining Duo...' : (
              <>
                <span>Join Duo</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="text-center text-xs text-zinc-400 pt-2">
          Want to start your own Duo?{' '}
          <button
            onClick={() => onNavigate('create-duo')}
            className="text-emerald-400 hover:underline font-semibold"
          >
            Create Duo
          </button>
        </div>
      </div>
    </div>
  );
};
