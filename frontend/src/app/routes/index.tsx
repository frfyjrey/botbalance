import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { ROUTES } from '@shared/config/constants';
import { ProtectedRoute } from './protected-route';
import { AdminProtectedRoute } from './admin-protected-route';
import { AuthGuard } from './auth-guard';

// Lazy load pages
const LoginPage = lazy(() => import('@pages/login'));
const DashboardPage = lazy(() => import('@pages/dashboard'));
const StrategyPage = lazy(() => import('@pages/strategy'));
const AdminDashboardPage = lazy(() => import('@pages/admin-dashboard'));

// Loading fallback
// eslint-disable-next-line react-refresh/only-export-components
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
  </div>
);

// Route components with Suspense
// eslint-disable-next-line react-refresh/only-export-components
const SuspenseWrapper = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<PageLoader />}>{children}</Suspense>
);

export const router = createBrowserRouter([
  {
    path: ROUTES.HOME,
    element: <Navigate to={ROUTES.DASHBOARD} replace />,
  },
  {
    path: ROUTES.LOGIN,
    element: (
      <AuthGuard>
        <SuspenseWrapper>
          <LoginPage />
        </SuspenseWrapper>
      </AuthGuard>
    ),
  },
  {
    path: ROUTES.DASHBOARD,
    element: (
      <ProtectedRoute>
        <SuspenseWrapper>
          <DashboardPage />
        </SuspenseWrapper>
      </ProtectedRoute>
    ),
  },
  {
    path: ROUTES.STRATEGY,
    element: (
      <ProtectedRoute>
        <SuspenseWrapper>
          <StrategyPage />
        </SuspenseWrapper>
      </ProtectedRoute>
    ),
  },
  {
    path: ROUTES.ADMIN_DASHBOARD,
    element: (
      <AdminProtectedRoute>
        <SuspenseWrapper>
          <AdminDashboardPage />
        </SuspenseWrapper>
      </AdminProtectedRoute>
    ),
  },
  {
    path: '*',
    element: <Navigate to={ROUTES.DASHBOARD} replace />,
  },
]);
