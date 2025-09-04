import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  UseMutationOptions,
  UseQueryOptions,
} from '@tanstack/react-query';

import { apiClient } from '@shared/lib/api';
import { QUERY_KEYS } from '@shared/config/constants';
import type {
  Strategy,
  StrategyResponse,
  StrategyCreateRequest,
  StrategyUpdateRequest,
  StrategyActivateRequest,
  RebalancePlanResponse,
  RebalanceExecuteRequest,
  RebalanceExecuteResponse,
} from './model';

/**
 * Hook to fetch user's current strategy
 */
export const useStrategy = (
  options?: Partial<UseQueryOptions<StrategyResponse, Error>>,
) => {
  return useQuery({
    queryKey: [QUERY_KEYS.STRATEGY],
    queryFn: () => apiClient.getStrategy(),
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
    retry: (failureCount, error) => {
      // Don't retry on 401 (auth) or 404 (no strategy)
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

/**
 * Hook to create a new strategy
 */
export const useCreateStrategy = (
  options?: UseMutationOptions<StrategyResponse, Error, StrategyCreateRequest>,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StrategyCreateRequest) => apiClient.createStrategy(data),
    onSuccess: data => {
      // Update strategy cache
      queryClient.setQueryData([QUERY_KEYS.STRATEGY], data);
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REBALANCE_PLAN] });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.PORTFOLIO_SUMMARY],
      });
    },
    ...options,
  });
};

/**
 * Hook to update existing strategy
 */
export const useUpdateStrategy = (
  options?: UseMutationOptions<StrategyResponse, Error, StrategyUpdateRequest>,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StrategyUpdateRequest) => apiClient.updateStrategy(data),
    onSuccess: data => {
      // Update strategy cache
      queryClient.setQueryData([QUERY_KEYS.STRATEGY], data);
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REBALANCE_PLAN] });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.PORTFOLIO_SUMMARY],
      });
    },
    ...options,
  });
};

/**
 * Hook to activate/deactivate strategy
 */
export const useActivateStrategy = (
  options?: UseMutationOptions<
    StrategyResponse,
    Error,
    StrategyActivateRequest
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StrategyActivateRequest) =>
      apiClient.activateStrategy(data),
    onSuccess: data => {
      // Update strategy cache
      queryClient.setQueryData([QUERY_KEYS.STRATEGY], data);
      // Invalidate rebalance plan as activation status affects it
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REBALANCE_PLAN] });
    },
    ...options,
  });
};

/**
 * Hook to fetch rebalance plan
 */
export const useRebalancePlan = (
  forceRefresh?: boolean,
  options?: Partial<UseQueryOptions<RebalancePlanResponse, Error>>,
) => {
  return useQuery({
    queryKey: [QUERY_KEYS.REBALANCE_PLAN, { forceRefresh }],
    queryFn: () => apiClient.getRebalancePlan(forceRefresh),
    staleTime: 1000 * 30, // Consider data fresh for 30 seconds
    refetchOnMount: true,
    retry: (failureCount, error) => {
      // Don't retry on 401 (auth), 404 (no strategy/account), or 400 (invalid strategy)
      if (
        error &&
        'status' in error &&
        (error.status === 401 || error.status === 404 || error.status === 400)
      ) {
        return false;
      }
      return failureCount < 3;
    },
    ...options,
  });
};

/**
 * Hook to force refresh rebalance plan
 */
export const useRefreshRebalancePlan = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      // Invalidate and refetch both cached and fresh data
      await queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.REBALANCE_PLAN],
      });
      await queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.PORTFOLIO_SUMMARY],
      });

      // Fetch fresh data
      return apiClient.getRebalancePlan(true);
    },
    onSuccess: data => {
      // Update cache with fresh data
      queryClient.setQueryData(
        [QUERY_KEYS.REBALANCE_PLAN, { forceRefresh: true }],
        data,
      );
    },
  });
};

/**
 * Utility hook to get strategy data directly (for forms)
 */
export const useStrategyData = (): Strategy | null => {
  const { data } = useStrategy();
  return data?.strategy || null;
};

/**
 * Utility hook to check if user has a strategy
 */
export const useHasStrategy = (): boolean => {
  const { data } = useStrategy();
  return !!data?.strategy;
};

/**
 * Utility hook to check if strategy is active
 */
export const useIsStrategyActive = (): boolean => {
  const { data } = useStrategy();
  return !!data?.strategy?.is_active;
};

/**
 * Hook to execute rebalance (create orders)
 */
export const useExecuteRebalance = (
  options?: UseMutationOptions<
    RebalanceExecuteResponse,
    Error,
    RebalanceExecuteRequest
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RebalanceExecuteRequest) =>
      apiClient.executeRebalance(data),
    onSuccess: () => {
      // Invalidate and refetch related data after successful rebalance
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REBALANCE_PLAN] });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.PORTFOLIO_SUMMARY],
      });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.ORDERS] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.STRATEGY] });
    },
    ...options,
  });
};
