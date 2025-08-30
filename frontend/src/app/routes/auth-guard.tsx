import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ROUTES } from '@shared/config/constants';
import { tokenManager } from '@shared/lib/api';

interface AuthGuardProps {
  children: ReactNode;
}

export const AuthGuard = ({ children }: AuthGuardProps) => {
  const isAuthenticated = tokenManager.isAuthenticated();

  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return <>{children}</>;
};
