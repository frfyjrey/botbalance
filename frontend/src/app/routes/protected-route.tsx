import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ROUTES } from '@shared/config/constants';
import { tokenManager } from '@shared/lib/api';

interface ProtectedRouteProps {
  children: ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const isAuthenticated = tokenManager.isAuthenticated();

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <>{children}</>;
};
