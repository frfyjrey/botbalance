import { useState, useEffect } from 'react';
import { tokenManager } from '@shared/lib/api';
import type { User } from '@shared/config/types';

// Auth state hook
export const useAuthState = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(
    tokenManager.isAuthenticated(),
  );
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const handleAuthLogin = (event: CustomEvent<User>) => {
      setIsAuthenticated(true);
      setUser(event.detail);
    };

    const handleAuthLogout = () => {
      setIsAuthenticated(false);
      setUser(null);
    };

    const handleStorageChange = () => {
      setIsAuthenticated(tokenManager.isAuthenticated());
    };

    // Listen to auth events
    window.addEventListener('auth:login', handleAuthLogin as EventListener);
    window.addEventListener('auth:logout', handleAuthLogout);
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener(
        'auth:login',
        handleAuthLogin as EventListener,
      );
      window.removeEventListener('auth:logout', handleAuthLogout);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  return { isAuthenticated, user };
};

// User utilities
export const getUserDisplayName = (user: User): string => {
  if (user.first_name || user.last_name) {
    return `${user.first_name} ${user.last_name}`.trim();
  }
  return user.username;
};

export const getUserInitials = (user: User): string => {
  const displayName = getUserDisplayName(user);
  const names = displayName.split(' ');
  return names
    .map(name => name[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
};
