import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { apiClient } from '@shared/lib/api';
import { QUERY_KEYS } from '@shared/config/constants';
import { useAuthStore } from '@shared/lib/store';
import type { BalancesResponse, AuthState } from '@shared/config/types';

/**
 * Hook for fetching user balances
 */
export const useBalances = (
  options?: Partial<UseQueryOptions<BalancesResponse, Error>>
) => {
  const isAuthenticated = useAuthStore(
    (state: AuthState) => state.isAuthenticated,
  );

  return useQuery({
    queryKey: [QUERY_KEYS.USER, 'balances'],
    queryFn: async () => {
      const response = await apiClient.getBalances();
      return response;
    },
    enabled: isAuthenticated,
    retry: (failureCount, error) => {
      // Don't retry on authentication errors
      if (error && 'status' in error && error.status === 401) {
        return false;
      }
      // Don't retry if no exchange accounts (404) - this is expected
      if (error && 'status' in error && error.status === 404) {
        return false;
      }
      return failureCount < 3;
    },
    staleTime: 1000 * 60 * 2, // Consider data fresh for 2 minutes
    refetchInterval: 1000 * 30, // Refetch every 30 seconds when component is focused
    ...options,
  });
};
