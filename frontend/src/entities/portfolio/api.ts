import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  UseQueryOptions,
  UseMutationOptions,
  UseQueryResult,
} from '@tanstack/react-query';

import { apiClient } from '@shared/lib/api';
import { QUERY_KEYS } from '@shared/config/constants';
import type {
  PortfolioSummaryResponse,
  PortfolioStateResponse,
  RefreshPortfolioStateResponse,
} from './model';
import { portfolioStateToSummary } from './model';

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

// =============================================================================
// PORTFOLIO STATE HOOKS (New Architecture - Step 5)
// =============================================================================

/**
 * Hook to fetch current portfolio state (fast, no API calls to exchange)
 */
export const usePortfolioState = (
  params?: { connector_id?: number },
  options?: Partial<UseQueryOptions<PortfolioStateResponse, Error>>,
) => {
  return useQuery({
    queryKey: [QUERY_KEYS.PORTFOLIO_STATE, params?.connector_id],
    queryFn: () => apiClient.getPortfolioState(params),
    staleTime: 1000 * 30, // Consider fresh for 30 seconds (State is current)
    refetchOnMount: 'always', // Always fetch fresh State
    refetchOnWindowFocus: true, // Refetch when user returns
    retry: (failureCount, error) => {
      // Don't retry on 404 (no State found), 403 (auth), 409 (no active strategy)
      if (
        error &&
        'status' in error &&
        (error.status === 404 || error.status === 403 || error.status === 409)
      ) {
        return false;
      }
      return failureCount < 2; // Quick retry for State
    },
    retryDelay: 1000, // Fast retry - 1 second
    ...options,
  });
};

/**
 * Hook to refresh portfolio state (triggers exchange API call)
 */
export const useRefreshPortfolioState = (
  options?: UseMutationOptions<
    RefreshPortfolioStateResponse,
    Error,
    { connector_id?: number; force?: boolean }
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: params => apiClient.refreshPortfolioState(params),
    onSuccess: (_data, variables) => {
      // Invalidate relevant queries on successful refresh
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.PORTFOLIO_STATE, variables.connector_id],
      });

      // Also refresh legacy portfolio summary for compatibility
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.PORTFOLIO_SUMMARY],
      });
    },
    ...options,
  });
};

/**
 * Primary hook that uses ONLY PortfolioState API (no fallback)
 *
 * Returns 404 ERROR_NO_STATE if state doesn't exist - dashboard should show empty state.
 * User must explicitly call refresh to create initial state.
 * Converts PortfolioState to PortfolioSummary format for component compatibility.
 */
export const usePortfolioData = (
  params?: { connector_id?: number },
  options?: Partial<UseQueryOptions<PortfolioSummaryResponse, Error>>,
): UseQueryResult<PortfolioSummaryResponse, Error> => {
  const stateQuery = usePortfolioState(params, {
    enabled: true, // Always try State
    retry: (failureCount, error) => {
      // Don't retry on 404 ERROR_NO_STATE - this is expected when no state exists
      if (error && 'status' in error && error.status === 404) {
        return false;
      }
      return failureCount < 2;
    },
    ...options,
  });

  // If State is successful, convert and return
  if (stateQuery.data?.state && stateQuery.data.status === 'success') {
    const portfolioSummary = portfolioStateToSummary(stateQuery.data.state);

    return {
      ...stateQuery,
      data: {
        status: 'success',
        portfolio: portfolioSummary,
        message: `✨ Using PortfolioState API`,
      } as PortfolioSummaryResponse,
    } as UseQueryResult<PortfolioSummaryResponse, Error>;
  }

  // Return loading/error states (including 404 ERROR_NO_STATE)
  return {
    ...stateQuery,
    data: undefined, // No data when state doesn't exist
    error: stateQuery.error,
    isLoading: stateQuery.isLoading,
    isError: stateQuery.isError,
  } as UseQueryResult<PortfolioSummaryResponse, Error>;
};
