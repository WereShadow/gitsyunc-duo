import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from './context/AuthContext';

// Layout
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { MobileNav } from './components/layout/MobileNav';

// Pages — unauthenticated
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';

// Pages — post-auth, pre-duo
import { CreateDuoPage } from './pages/CreateDuoPage';
import { JoinDuoPage } from './pages/JoinDuoPage';
import { OnboardingPage } from './pages/OnboardingPage';

// Pages — main app (no custom props needed; they use useAuth internally)
import { DashboardPage } from './pages/DashboardPage';
import { TodaysTaskPage } from './pages/TodaysTaskPage';
import { GitHubActivityPage } from './pages/GitHubActivityPage';
import { CalendarPage } from './pages/CalendarPage';
import { HistoryPage } from './pages/HistoryPage';
import { StatisticsPage } from './pages/StatisticsPage';
import SettingsPage from './pages/SettingsPage';

// ------------------------------------------------------------
// Types
// ------------------------------------------------------------
type PublicPage = 'landing' | 'login' | 'register';
type OnboardPage = 'onboarding' | 'create-duo' | 'join-duo';
type AppTab = 'dashboard' | 'task' | 'github' | 'calendar' | 'history' | 'statistics' | 'settings';

// ------------------------------------------------------------
// Loading Spinner
// ------------------------------------------------------------
const FullPageSpinner: React.FC = () => (
  <div className="min-h-screen bg-slate-950 flex items-center justify-center">
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-4 border-slate-700" />
        <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin" />
      </div>
      <p className="text-slate-400 text-sm">Loading GitSync Duo…</p>
    </div>
  </div>
);

// ------------------------------------------------------------
// App
// ------------------------------------------------------------
const App: React.FC = () => {
  const { user, duo, loading, refreshState } = useAuth();

  // Page state for unauthenticated flow
  const [publicPage, setPublicPage] = useState<PublicPage>('landing');

  // Page state for post-auth, pre-duo flow
  const [onboardPage, setOnboardPage] = useState<OnboardPage>('onboarding');

  // Active tab for authenticated app
  const [currentTab, setCurrentTab] = useState<AppTab>('dashboard');

  // Global refresh counter — increment to force polling components to re-fetch
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    setRefreshKey(k => k + 1);
    refreshState();
  }, [refreshState]);

  // When user logs in with a duo, reset to dashboard
  useEffect(() => {
    if (user && duo) {
      setCurrentTab('dashboard');
    }
  }, [user?.id, duo?.id]);

  // When user logs in but has no duo yet, show onboarding
  useEffect(() => {
    if (user && !duo) {
      setOnboardPage('onboarding');
    }
  }, [user?.id]);

  // ------------------------------------------------------------
  // Loading
  // ------------------------------------------------------------
  if (loading) {
    return <FullPageSpinner />;
  }

  // ------------------------------------------------------------
  // Unauthenticated
  // ------------------------------------------------------------
  if (!user) {
    switch (publicPage) {
      case 'login':
        return <LoginPage onNavigate={setPublicPage as (p: string) => void} />;
      case 'register':
        return <RegisterPage onNavigate={setPublicPage as (p: string) => void} />;
      default:
        return <LandingPage onNavigate={setPublicPage as (p: string) => void} />;
    }
  }

  // ------------------------------------------------------------
  // Authenticated — no duo yet
  // ------------------------------------------------------------
  if (!duo) {
    switch (onboardPage) {
      case 'create-duo':
        return <CreateDuoPage onNavigate={setOnboardPage as (p: string) => void} />;
      case 'join-duo':
        return <JoinDuoPage onNavigate={setOnboardPage as (p: string) => void} />;
      default:
        return <OnboardingPage onNavigate={setOnboardPage as (p: string) => void} />;
    }
  }

  // ------------------------------------------------------------
  // Authenticated + has duo — main app shell
  // ------------------------------------------------------------
  const renderPage = () => {
    switch (currentTab) {
      case 'task':
        return <TodaysTaskPage key={refreshKey} />;
      case 'github':
        return <GitHubActivityPage key={refreshKey} />;
      case 'calendar':
        return <CalendarPage key={refreshKey} />;
      case 'history':
        return <HistoryPage key={refreshKey} />;
      case 'statistics':
        return <StatisticsPage key={refreshKey} />;
      case 'settings':
        return <SettingsPage key={refreshKey} />;
      default:
        return <DashboardPage key={refreshKey} onNavigate={(tab: string) => setCurrentTab(tab as AppTab)} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Top Navbar */}
      <Navbar onRefresh={handleRefresh} />

      <div className="flex">
        {/* Sidebar — hidden on mobile */}
        <div className="hidden lg:block">
          <Sidebar
            currentTab={currentTab}
            onTabChange={(tab: string) => setCurrentTab(tab as AppTab)}
          />
        </div>

        {/* Main content */}
        <main className="flex-1 min-h-[calc(100vh-4rem)] p-4 sm:p-6 pb-24 lg:pb-6 overflow-x-hidden">
          {renderPage()}
        </main>
      </div>

      {/* Mobile bottom nav — visible on mobile only */}
      <div className="lg:hidden">
        <MobileNav
          currentTab={currentTab}
          onTabChange={(tab: string) => setCurrentTab(tab as AppTab)}
        />
      </div>
    </div>
  );
};

export default App;
