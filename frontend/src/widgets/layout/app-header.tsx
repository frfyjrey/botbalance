import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';

import { Button } from '@shared/ui/Button';
import { useUserProfile, useLogout } from '@entities/user';
import { useThemeStore } from '@shared/lib/store';
import { ROUTES } from '@shared/config/constants';

export const AppHeader: React.FC = () => {
  const { t } = useTranslation(['common', 'auth']);
  const navigate = useNavigate();
  const location = useLocation();
  const { data: user } = useUserProfile();
  const { theme, setTheme } = useThemeStore();
  const logout = useLogout();

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSuccess: () => {
        navigate('/login', { replace: true });
      },
    });
  };

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark');
    } else if (theme === 'dark') {
      setTheme('system');
    } else {
      setTheme('dark');
    }
  };

  const getThemeIcon = () => {
    if (theme === 'dark') {
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      );
    } else if (theme === 'light') {
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      );
    } else {
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      );
    }
  };

  const getThemeLabel = () => {
    if (theme === 'dark') return 'Темная';
    if (theme === 'light') return 'Светлая';
    return 'Авто';
  };

  const isCurrentRoute = (route: string) => location.pathname === route;

  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{
        backgroundColor: 'rgb(var(--canvas-default))',
        borderBottomColor: 'rgb(var(--border))',
      }}
    >
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8">
        <div className="flex items-center justify-between py-3 sm:py-4 min-h-[56px] sm:min-h-[60px]">
          {/* Left side - Logo and navigation */}
          <div className="flex items-center space-x-3 sm:space-x-6">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center cursor-pointer flex-shrink-0"
                style={{ backgroundColor: 'rgb(var(--fg-default))' }}
                onClick={() => navigate(ROUTES.DASHBOARD)}
              >
                <span
                  className="text-xs sm:text-sm font-bold"
                  style={{ color: 'rgb(var(--fg-onEmphasis))' }}
                >
                  B
                </span>
              </div>

              <h1
                className="text-base sm:text-lg font-semibold truncate"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                BotBalance
              </h1>
            </div>

            {/* Navigation - скрыто на мобильных, показано на планшетах+ */}
            <nav className="hidden md:flex items-center space-x-3 sm:space-x-4">
              <Button
                onClick={() => navigate(ROUTES.DASHBOARD)}
                className={`btn-github text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5 ${
                  isCurrentRoute(ROUTES.DASHBOARD)
                    ? 'btn-github-secondary'
                    : 'btn-github-invisible'
                }`}
              >
                Dashboard
              </Button>
              <Button
                onClick={() => navigate(ROUTES.STRATEGY)}
                className={`btn-github text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5 ${
                  isCurrentRoute(ROUTES.STRATEGY)
                    ? 'btn-github-secondary'
                    : 'btn-github-invisible'
                }`}
              >
                Strategy
              </Button>
              <Button
                onClick={() => navigate(ROUTES.ORDERS)}
                className={`btn-github text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5 ${
                  isCurrentRoute(ROUTES.ORDERS)
                    ? 'btn-github-secondary'
                    : 'btn-github-invisible'
                }`}
              >
                Orders
              </Button>
              <Button
                onClick={() => navigate(ROUTES.EXCHANGES)}
                className={`btn-github text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5 ${
                  isCurrentRoute(ROUTES.EXCHANGES)
                    ? 'btn-github-secondary'
                    : 'btn-github-invisible'
                }`}
              >
                Exchanges
              </Button>
            </nav>
          </div>

          {/* Right side - User controls */}
          <div className="flex items-center space-x-1 sm:space-x-2">
            {/* Admin Panel Link (only for staff/superusers) */}
            {(user?.is_staff || user?.is_superuser) && (
              <Button
                onClick={() => navigate(ROUTES.ADMIN_DASHBOARD)}
                className="btn-github btn-github-secondary text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5"
                title="Панель администратора"
              >
                <svg
                  className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span className="hidden md:inline ml-1 sm:ml-2">Admin</span>
              </Button>
            )}

            {/* Theme Toggle */}
            <Button
              onClick={toggleTheme}
              className="btn-github btn-github-invisible p-1 sm:p-2"
              title={`Текущая тема: ${getThemeLabel()}`}
            >
              {getThemeIcon()}
            </Button>

            {/* User Menu */}
            <Button
              onClick={handleLogout}
              disabled={logout.isPending}
              className="btn-github btn-github-secondary text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5"
              title={t('auth:logout')}
            >
              {logout.isPending ? (
                <div className="w-3 h-3 sm:w-4 sm:h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin flex-shrink-0" />
              ) : (
                <svg
                  className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
              )}
              <span className="hidden md:inline ml-1 sm:ml-2">
                {t('auth:logout')}
              </span>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};
