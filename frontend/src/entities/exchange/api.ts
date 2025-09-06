/**
 * Exchange account API functions.
 */

import { apiClient } from '@shared/lib/api';
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
