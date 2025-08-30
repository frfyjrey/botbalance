import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Button } from '@shared/ui/Button';
// Removed Card components - using GitHub-style design directly
import { QUERY_KEYS, ROUTES } from '@shared/config/constants';
import { apiClient } from '@shared/lib/api';
import { useUserProfile, getUserDisplayName, useLogout } from '@entities/user';
import {
  useCreateEchoTask,
  useTaskPolling,
  getTaskStateLabel,
} from '@entities/task';
import { formatDate } from '@shared/lib/utils';
import { useThemeStore } from '@shared/lib/store';

export const DashboardContent = () => {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const { data: user, isLoading: userLoading } = useUserProfile();
  const { theme, setTheme } = useThemeStore();
  const logout = useLogout();

  const [taskId, setTaskId] = useState<string | null>(null);

  // Ensure theme is applied on component mount
  useEffect(() => {
    const { theme, setTheme } = useThemeStore.getState();
    setTheme(theme);
  }, []);

  // System queries
  const { data: health } = useQuery({
    queryKey: [QUERY_KEYS.HEALTH],
    queryFn: () => apiClient.getHealth(),
  });

  const { data: version } = useQuery({
    queryKey: [QUERY_KEYS.VERSION],
    queryFn: () => apiClient.getVersion(),
  });

  // Task mutations
  const createEchoTask = useCreateEchoTask();
  const { task, isComplete } = useTaskPolling(taskId);

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSuccess: () => {
        // Redirect to login page after successful logout
        navigate(ROUTES.LOGIN, { replace: true });
      },
    });
  };

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark');
    } else if (theme === 'dark') {
      setTheme('system');
    } else {
      // If theme is 'system', always go to 'dark' first for predictable testing
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

  const handleCreateTask = async () => {
    try {
      const response = await createEchoTask.mutateAsync({
        message: 'Hello from Dashboard!',
        delay: 2,
      });

      if (response.status === 'success' && response.task_id) {
        setTaskId(response.task_id);
      }
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  // Removed getStatusColor - using GitHub-style inline styles instead

  if (userLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>{t('loading_dashboard')}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: 'rgb(var(--canvas-default))' }}
    >
      {/* Header - GitHub style */}
      <header
        className="sticky top-0 z-50 border-b"
        style={{
          backgroundColor: 'rgb(var(--canvas-default))',
          borderBottomColor: 'rgb(var(--border))',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4 min-h-[60px]">
            {/* Left side - Logo and welcome */}
            <div className="flex items-center space-x-3 flex-1 min-w-0">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: 'rgb(var(--fg-default))' }}
              >
                <span
                  className="text-sm font-bold"
                  style={{ color: 'rgb(var(--fg-onEmphasis))' }}
                >
                  B
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <h1
                  className="text-lg sm:text-xl font-semibold truncate"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  {t('welcome', {
                    username: user ? getUserDisplayName(user) : 'User',
                  })}
                </h1>
                <p
                  className="text-xs sm:text-sm truncate"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  {t('subtitle')}
                </p>
              </div>
            </div>

            {/* Right side - Theme toggle & Logout buttons */}
            <div className="flex-shrink-0 ml-4 flex items-center space-x-2">
              {/* Theme Toggle */}
              <Button
                onClick={toggleTheme}
                className="btn-github btn-github-secondary text-sm px-3 py-1.5"
                title={`Текущая тема: ${getThemeLabel()}`}
              >
                {getThemeIcon()}
                <span className="ml-2 hidden lg:inline">{getThemeLabel()}</span>
              </Button>

              {/* Logout */}
              <Button
                onClick={handleLogout}
                disabled={logout.isPending}
                className="btn-github btn-github-secondary text-sm px-3 py-1.5"
                title={t('auth:logout')}
              >
                {logout.isPending ? (
                  <>
                    <div className="w-3 h-3 sm:w-4 sm:h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
                    <span className="ml-2 hidden sm:inline">
                      {t('auth:logging_out')}
                    </span>
                  </>
                ) : (
                  <>
                    <svg
                      className="w-3 h-3 sm:w-4 sm:h-4"
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
                    <span className="ml-2 hidden sm:inline">
                      {t('auth:logout')}
                    </span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Information */}
          <div className="card-github">
            <div
              className="p-4 border-b"
              style={{ borderBottomColor: 'rgb(var(--border))' }}
            >
              <h3
                className="text-base font-semibold"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                {t('user_information')}
              </h3>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex justify-between">
                <span
                  className="font-medium text-sm"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  {t('user_info.username')}
                </span>
                <span
                  className="text-sm"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  {user?.username}
                </span>
              </div>
              <div className="flex justify-between">
                <span
                  className="font-medium text-sm"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  {t('user_info.email')}
                </span>
                <span
                  className="text-sm"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  {user?.email}
                </span>
              </div>
              <div className="flex justify-between">
                <span
                  className="font-medium text-sm"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  {t('user_info.joined')}
                </span>
                <span
                  className="text-sm"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  {user?.date_joined
                    ? formatDate(user.date_joined)
                    : t('user_info.unknown')}
                </span>
              </div>
            </div>
          </div>

          {/* System Health */}
          <div className="card-github">
            <div
              className="p-4 border-b"
              style={{ borderBottomColor: 'rgb(var(--border))' }}
            >
              <h3
                className="text-base font-semibold"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                {t('system_health')}
              </h3>
            </div>
            <div className="p-4 space-y-3">
              {health && (
                <>
                  <div className="flex justify-between items-center">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('health.database')}
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor:
                          health.database.status === 'healthy'
                            ? 'rgb(var(--alert-success-bg))'
                            : 'rgb(var(--alert-error-bg))',
                        color: 'rgb(var(--fg-default))',
                      }}
                    >
                      {health.database.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('health.redis')}
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor:
                          health.redis.status === 'healthy'
                            ? 'rgb(var(--alert-success-bg))'
                            : 'rgb(var(--alert-error-bg))',
                        color: 'rgb(var(--fg-default))',
                      }}
                    >
                      {health.redis.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('health.celery')}
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor:
                          health.celery.status === 'healthy'
                            ? 'rgb(var(--alert-success-bg))'
                            : 'rgb(var(--alert-error-bg))',
                        color: 'rgb(var(--fg-default))',
                      }}
                    >
                      {health.celery.status} (
                      {t('health.workers', { count: health.celery.workers })})
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('health.overall')}
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor:
                          health.status === 'healthy'
                            ? 'rgb(var(--alert-success-bg))'
                            : 'rgb(var(--alert-error-bg))',
                        color: 'rgb(var(--fg-default))',
                      }}
                    >
                      {health.status}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Version Information */}
          <div className="card-github">
            <div
              className="p-4 border-b"
              style={{ borderBottomColor: 'rgb(var(--border))' }}
            >
              <h3
                className="text-base font-semibold"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                {t('version_information')}
              </h3>
            </div>
            <div className="p-4 space-y-3">
              {version && (
                <>
                  <div className="flex justify-between">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('version.app')}
                    </span>
                    <span
                      className="text-sm"
                      style={{ color: 'rgb(var(--fg-muted))' }}
                    >
                      {version.name} v{version.version}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('version.environment')}
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor: 'rgb(var(--alert-info-bg))',
                        color: 'rgb(var(--fg-default))',
                      }}
                    >
                      {version.environment}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span
                      className="font-medium text-sm"
                      style={{ color: 'rgb(var(--fg-default))' }}
                    >
                      {t('version.description')}
                    </span>
                    <span
                      className="text-sm"
                      style={{ color: 'rgb(var(--fg-muted))' }}
                    >
                      {version.description}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Celery Task Demo */}
          <div className="card-github">
            <div
              className="p-4 border-b"
              style={{ borderBottomColor: 'rgb(var(--border))' }}
            >
              <h3
                className="text-base font-semibold"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                {t('celery_task_demo')}
              </h3>
            </div>
            <div className="p-4 space-y-4">
              <Button
                onClick={handleCreateTask}
                disabled={createEchoTask.isPending}
                className="btn-github btn-github-primary w-full"
              >
                {createEchoTask.isPending
                  ? t('tasks.creating_task')
                  : t('tasks.create_echo_task')}
              </Button>

              {taskId && (
                <div
                  className="p-4 rounded"
                  style={{ backgroundColor: 'rgb(var(--canvas-inset))' }}
                >
                  <h4
                    className="font-medium mb-2 text-sm"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    {t('tasks.task_id', { taskId })}
                  </h4>
                  {task && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span
                          className="font-medium text-sm"
                          style={{ color: 'rgb(var(--fg-default))' }}
                        >
                          {t('tasks.state')}
                        </span>
                        <span
                          className="px-2 py-1 rounded text-xs font-medium"
                          style={{
                            backgroundColor:
                              task.state === 'SUCCESS'
                                ? 'rgb(var(--alert-success-bg))'
                                : task.state === 'FAILURE'
                                  ? 'rgb(var(--alert-error-bg))'
                                  : 'rgb(var(--alert-warning-bg))',
                            color: 'rgb(var(--fg-default))',
                          }}
                        >
                          {getTaskStateLabel(task.state)}
                        </span>
                      </div>
                      {isComplete &&
                        task.result !== null &&
                        task.result !== undefined && (
                          <div>
                            <div
                              className="font-medium mb-1 text-sm"
                              style={{ color: 'rgb(var(--fg-default))' }}
                            >
                              {t('tasks.result')}
                            </div>
                            <pre
                              className="p-2 rounded text-xs overflow-x-auto font-mono"
                              style={{
                                backgroundColor: 'rgb(var(--canvas-subtle))',
                                color: 'rgb(var(--fg-default))',
                              }}
                            >
                              {JSON.stringify(
                                task.result as Record<string, unknown>,
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
