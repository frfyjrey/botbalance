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

  // Generic request method for custom calls
  async request<T = unknown>(
    endpoint: string,
    options?: RequestInit,
  ): Promise<T> {
    return apiRequest<T>(endpoint, options);
  },
};
