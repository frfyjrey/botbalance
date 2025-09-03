import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';

import { apiClient } from '@shared/lib/api';
import { QUERY_KEYS } from '@shared/config/constants';
import type { PortfolioSummaryResponse } from './model';

/**
 * Hook to fetch user's portfolio summary with NAV and asset allocations
 */
export const usePortfolioSummary = (
  options?: Partial<UseQueryOptions<PortfolioSummaryResponse, Error>>,
) => {
  return useQuery({
    queryKey: [QUERY_KEYS.PORTFOLIO_SUMMARY],
    queryFn: () => apiClient.getPortfolioSummary(),
    staleTime: 1000 * 30, // Consider data fresh for 30 seconds
    refetchOnMount: true,
    retry: (failureCount, error) => {
      // Don't retry on 401 (auth) or 404 (no accounts)
      if (
        error &&
        'status' in error &&
        (error.status === 401 || error.status === 404)
      ) {
        return false;
      }
      return failureCount < 3;
    },
    ...options,
  });
};
