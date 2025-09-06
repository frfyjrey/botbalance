/**
 * API Client with TanStack Query integration
 *
 * Features:
 * - JWT token storage in localStorage
 * - Fetch wrapper with automatic token attachment
 * - Error interceptor (401 -> logout)
 * - TypeScript support
 * - TanStack Query integration
 */

import { API_BASE, STORAGE_KEYS } from '../config/constants';
import type {
  LoginRequest,
  LoginResponse,
  ApiResponse,
  BalancesResponse,
  HealthCheckResponse,
  VersionResponse,
  TaskResponse,
  TaskStatusResponse,
  User,
} from '../config/types';
import type {
  ExchangeAccount,
  ExchangeAccountCreateRequest,
} from '../../entities/exchange';

/**
 * Token management
 */
export const tokenManager = {
  getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  },

  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
  },

  clearTokens(): void {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  },

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  },
};

/**
 * API Error class
 */
export class ApiClientError extends Error {
  status: number;
  errors?: Record<string, string[]>;

  constructor(
    message: string,
    status: number,
    errors?: Record<string, string[]>,
  ) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.errors = errors;
  }
}

/**
 * Fetch wrapper with automatic token attachment and error handling
 */
async function apiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const token = tokenManager.getAccessToken();

  // Default headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  // Add authorization header if token exists
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);

    // Handle 401 - token expired, logout user
    if (response.status === 401) {
      tokenManager.clearTokens();
      // Trigger logout event for the app
      window.dispatchEvent(new CustomEvent('auth:logout'));
      throw new ApiClientError('Authentication failed', 401);
    }

    // Parse response
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const message = data.message || data.detail || `HTTP ${response.status}`;
      throw new ApiClientError(message, response.status, data.errors);
    }

    return data;
  } catch (error) {
    // Re-throw ApiClientError as-is
    if (error instanceof ApiClientError) {
      throw error;
    }

    // Handle network errors
    if (error instanceof TypeError) {
      throw new ApiClientError('Network error', 0);
    }

    throw new ApiClientError('Unknown error', 500);
  }
}

/**
 * API Client methods
 */
export const apiClient = {
  // Authentication
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiRequest<LoginResponse>('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    // Store tokens if login successful
    if (response.status === 'success' && response.tokens) {
      tokenManager.setTokens(response.tokens.access, response.tokens.refresh);
    }

    return response;
  },

  async getUserProfile(): Promise<ApiResponse<User>> {
    return apiRequest<ApiResponse<User>>('/api/auth/profile/');
  },

  async logout(): Promise<void> {
    tokenManager.clearTokens();
    // Could also call a logout endpoint if needed
    // return apiRequest('/api/auth/logout/', { method: 'POST' });
  },

  // System endpoints
  async getHealth(): Promise<HealthCheckResponse> {
    return apiRequest<HealthCheckResponse>('/api/health/');
  },

  async getVersion(): Promise<VersionResponse> {
    return apiRequest<VersionResponse>('/api/version/');
  },

  // Task management
  async createEchoTask(
    message: string,
    delay: number = 0,
  ): Promise<TaskResponse> {
    return apiRequest<TaskResponse>('/api/tasks/echo/', {
      method: 'POST',
      body: JSON.stringify({ message, delay }),
    });
  },

  async createHeartbeatTask(): Promise<TaskResponse> {
    return apiRequest<TaskResponse>('/api/tasks/heartbeat/', {
      method: 'POST',
    });
  },

  async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return apiRequest<TaskStatusResponse>(
      `/api/tasks/status/?task_id=${taskId}`,
    );
  },

  // User account endpoints
  async getBalances(): Promise<BalancesResponse> {
    return apiRequest<BalancesResponse>('/api/me/balances/');
  },

  async getPortfolioSummary(): Promise<
    import('@entities/portfolio').PortfolioSummaryResponse
  > {
    return apiRequest<import('@entities/portfolio').PortfolioSummaryResponse>(
      '/api/me/portfolio/summary/',
    );
  },

  // Portfolio snapshots endpoints
  async getPortfolioSnapshots(params?: {
    limit?: number;
    from?: string;
    to?: string;
  }): Promise<{
    status: string;
    snapshots?: unknown[];
    count: number;
    has_more: boolean;
    message?: string;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.from) queryParams.set('from', params.from);
    if (params?.to) queryParams.set('to', params.to);

    const url = `/api/me/portfolio/snapshots/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return apiRequest(url);
  },

  async createPortfolioSnapshot(force = false): Promise<{
    status: string;
    snapshot?: unknown;
    message?: string;
    error_code?: string;
  }> {
    return apiRequest('/api/me/portfolio/snapshots/create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ force }),
    });
  },

  async deleteAllPortfolioSnapshots(): Promise<{
    status: string;
    message: string;
    deleted_count: number;
  }> {
    return apiRequest('/api/me/portfolio/snapshots/delete_all/', {
      method: 'DELETE',
    });
  },

  async getLatestPortfolioSnapshot(): Promise<{
    status: string;
    snapshot?: unknown;
    message?: string;
    error_code?: string;
  }> {
    return apiRequest('/api/me/portfolio/last_snapshot/');
  },

  // Strategy endpoints
  async getStrategy(): Promise<import('@entities/strategy').StrategyResponse> {
    return apiRequest<import('@entities/strategy').StrategyResponse>(
      '/api/me/strategy/',
    );
  },

  async createStrategy(
    data: import('@entities/strategy').StrategyCreateRequest,
  ): Promise<import('@entities/strategy').StrategyResponse> {
    return apiRequest<import('@entities/strategy').StrategyResponse>(
      '/api/me/strategy/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    );
  },

  async updateStrategy(
    data: import('@entities/strategy').StrategyUpdateRequest,
  ): Promise<import('@entities/strategy').StrategyResponse> {
    return apiRequest<import('@entities/strategy').StrategyResponse>(
      '/api/me/strategy/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    );
  },

  async activateStrategy(
    data: import('@entities/strategy').StrategyActivateRequest,
  ): Promise<import('@entities/strategy').StrategyResponse> {
    return apiRequest<import('@entities/strategy').StrategyResponse>(
      '/api/me/strategy/activate/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    );
  },

  async getRebalancePlan(
    forceRefresh?: boolean,
  ): Promise<import('@entities/strategy').RebalancePlanResponse> {
    const url = forceRefresh
      ? '/api/me/strategy/rebalance/plan/?force_refresh=true'
      : '/api/me/strategy/rebalance/plan/';

    return apiRequest<import('@entities/strategy').RebalancePlanResponse>(url);
  },

  async executeRebalance(
    data: import('@entities/strategy').RebalanceExecuteRequest,
  ): Promise<import('@entities/strategy').RebalanceExecuteResponse> {
    return apiRequest<import('@entities/strategy').RebalanceExecuteResponse>(
      '/api/me/strategy/rebalance/execute/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    );
  },

  // Orders endpoints
  async getOrders(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    symbol?: string;
    side?: string;
    exchange?: string;
  }): Promise<{
    status: string;
    orders: Array<{
      id: number;
      exchange_order_id: string | null;
      client_order_id: string | null;
      exchange: string;
      symbol: string;
      side: 'buy' | 'sell';
      status: string;
      limit_price: string;
      quote_amount: string;
      filled_amount: string;
      fill_percentage: string;
      fee_amount: string;
      fee_asset: string | null;
      created_at: string;
      submitted_at: string | null;
      filled_at: string | null;
      updated_at: string;
      error_message: string | null;
      strategy_name: string | null;
      execution_id: number | null;
      is_active: boolean;
    }>;
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  }> {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', params.limit.toString());
    if (params?.offset) qs.set('offset', params.offset.toString());
    if (params?.status) qs.set('status', params.status);
    if (params?.symbol) qs.set('symbol', params.symbol);
    if (params?.side) qs.set('side', params.side);
    if (params?.exchange) qs.set('exchange', params.exchange);
    const url = `/api/me/orders/${qs.toString() ? `?${qs.toString()}` : ''}`;
    return apiRequest(url);
  },

  async cancelOrder(
    orderId: number,
  ): Promise<{ status: string; order_id?: number }> {
    return apiRequest(`/api/me/orders/${orderId}/cancel/`, { method: 'POST' });
  },

  async cancelAllOrders(
    symbol: string,
  ): Promise<{ status: string; cancelled: number }> {
    return apiRequest(
      `/api/me/orders/cancel_all/?symbol=${encodeURIComponent(symbol)}`,
      { method: 'POST' },
    );
  },

  // Generic request method for custom calls
  async request<T = unknown>(
    endpoint: string,
    options?: RequestInit,
  ): Promise<T> {
    return apiRequest<T>(endpoint, options);
  },

  // Exchange accounts management
  async getExchangeAccounts(): Promise<{
    status: string;
    accounts: ExchangeAccount[];
  }> {
    return apiRequest<{ status: string; accounts: ExchangeAccount[] }>(
      '/api/me/exchanges/',
      {
        method: 'GET',
      },
    );
  },

  async createExchangeAccount(data: ExchangeAccountCreateRequest): Promise<{
    status: string;
    message: string;
    account: ExchangeAccount;
  }> {
    return apiRequest<{
      status: string;
      message: string;
      account: ExchangeAccount;
    }>('/api/me/exchanges/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getExchangeAccount(
    id: number,
  ): Promise<{ status: string; account: ExchangeAccount }> {
    return apiRequest<{ status: string; account: ExchangeAccount }>(
      `/api/me/exchanges/${id}/`,
      {
        method: 'GET',
      },
    );
  },

  async updateExchangeAccount(
    id: number,
    data: Partial<ExchangeAccountCreateRequest>,
  ): Promise<{
    status: string;
    message: string;
    account: ExchangeAccount;
  }> {
    return apiRequest<{
      status: string;
      message: string;
      account: ExchangeAccount;
    }>(`/api/me/exchanges/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteExchangeAccount(
    id: number,
  ): Promise<{ status: string; message: string }> {
    return apiRequest<{ status: string; message: string }>(
      `/api/me/exchanges/${id}/`,
      {
        method: 'DELETE',
      },
    );
  },

  async testExchangeAccount(id: number): Promise<{
    status: string;
    message: string;
    last_tested_at?: string;
  }> {
    return apiRequest<{
      status: string;
      message: string;
      last_tested_at?: string;
    }>(`/api/me/exchanges/${id}/test/`, {
      method: 'POST',
    });
  },
};
