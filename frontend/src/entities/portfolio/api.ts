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
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes (reduced frequency)
    refetchOnMount: false, // Don't refetch on component mount (reduces requests)
    refetchOnWindowFocus: false, // Don't refetch when user focuses window
    retry: (failureCount, error) => {
      // Don't retry on 401 (auth), 404 (no accounts), or 503 (fallback already used)
      if (
        error &&
        'status' in error &&
        (error.status === 401 || error.status === 404 || error.status === 503)
      ) {
        return false;
      }
      return failureCount < 3;
    },
    retryDelay: attemptIndex => {
      // Exponential backoff: 2s, 8s, 32s for dev; 5s, 20s, 60s for prod
      const isProd = import.meta.env.PROD;
      const baseDelay = isProd ? 5000 : 2000;
      return Math.min(
        baseDelay * Math.pow(4, attemptIndex),
        isProd ? 60000 : 32000,
      );
    },
    ...options,
  });
};
