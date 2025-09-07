/**
 * Exchange account API functions and React hooks.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@shared/lib/api';
import { QUERY_KEYS } from '@shared/config/constants';
import type {
  ExchangeAccount,
  ExchangeAccountCreateRequest,
  ExchangeAccountUpdateRequest,
  HealthCheckResponse,
} from './model';

export const exchangeApi = {
  async getAll(): Promise<ExchangeAccount[]> {
    const response = await apiClient.getExchangeAccounts();
    return response.accounts;
  },

  async getById(id: number): Promise<ExchangeAccount> {
    const response = await apiClient.getExchangeAccount(id);
    return response.account;
  },

  async create(data: ExchangeAccountCreateRequest): Promise<ExchangeAccount> {
    console.log('exchangeApi.create called with data:', data);
    try {
      const response = await apiClient.createExchangeAccount(data);
      console.log('exchangeApi.create response:', response);
      return response.account;
    } catch (error) {
      console.error('exchangeApi.create error:', error);
      throw error;
    }
  },

  async update(
    id: number,
    data: ExchangeAccountUpdateRequest,
  ): Promise<ExchangeAccount> {
    const response = await apiClient.updateExchangeAccount(id, data);
    return response.account;
  },

  async delete(id: number): Promise<void> {
    await apiClient.deleteExchangeAccount(id);
  },

  async check(id: number): Promise<HealthCheckResponse> {
    return await apiClient.checkExchangeAccount(id);
  },
};

/**
 * Hook to fetch user's exchange accounts
 */
export const useExchangeAccounts = () => {
  return useQuery({
    queryKey: [QUERY_KEYS.EXCHANGE_ACCOUNTS],
    queryFn: () => exchangeApi.getAll(),
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
    retry: (failureCount, error) => {
      // Don't retry on 401 (auth)
      if (error && 'status' in error && error.status === 401) {
        return false;
      }
      return failureCount < 3;
    },
  });
};
