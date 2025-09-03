import { Navigate } from 'react-router-dom';
import { useUserProfile } from '@entities/user';
import { ROUTES } from '@shared/config/constants';

interface AdminProtectedRouteProps {
  children: React.ReactNode;
}

export function AdminProtectedRoute({ children }: AdminProtectedRouteProps) {
  const { data: user, isLoading } = useUserProfile();

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  // If no user, redirect to login
  if (!user) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  // If user is not admin/staff/superuser, redirect to regular dashboard
  if (!user.is_staff && !user.is_superuser) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // User is authenticated and is admin - render protected content
  return <>{children}</>;
}
