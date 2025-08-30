import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, tokenManager } from '@shared/lib/api';
import { useAuthStore } from '@shared/lib/store';
import { QUERY_KEYS } from '@shared/config/constants';
import type { LoginRequest, LoginResponse } from '@shared/config/types';

// Query hooks
export const useUserProfile = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  return useQuery({
    queryKey: [QUERY_KEYS.USER, 'profile'],
    queryFn: async () => {
      // Double-check authentication before making the request
      if (!tokenManager.isAuthenticated()) {
        throw new Error('User not authenticated');
      }
      
      try {
        const response = await apiClient.getUserProfile();
        return response.data || null; // Ensure we never return undefined
      } catch (error) {
        // If it's an auth error, clear tokens and update store
        if (error && typeof error === 'object' && 'status' in error && (error as { status: number }).status === 401) {
          tokenManager.clearTokens();
          useAuthStore.getState().setIsAuthenticated(false);
        }
        throw error;
      }
    },
    enabled: isAuthenticated, // Use reactive state instead of direct token check
    retry: false, // Don't retry on auth errors
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
  });
};

// Mutation hooks  
export const useLogin = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: LoginRequest) => apiClient.login(credentials),
    onSuccess: (data: LoginResponse) => {
      if (data.status === 'success' && data.user) {
        // Update auth store immediately
        useAuthStore.getState().setIsAuthenticated(true);
        
        // Cache user data
        queryClient.setQueryData([QUERY_KEYS.USER, 'profile'], data.user);
        
        // Trigger a global event for auth state change
        window.dispatchEvent(new CustomEvent('auth:login', { detail: data.user }));
      }
    },
    onError: (error) => {
      console.error('Login failed:', error);
      // Make sure auth state is false on login failure
      useAuthStore.getState().setIsAuthenticated(false);
    },
  });
};

export const useLogout = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.logout(),
    onSuccess: () => {
      // Update auth store immediately
      useAuthStore.getState().setIsAuthenticated(false);
      
      // Clear all cached data
      queryClient.clear();
      
      // Trigger a global event for auth state change
      window.dispatchEvent(new CustomEvent('auth:logout'));
    },
  });
};
