/**
 * Exchange account types for managing exchange API connections.
 */

export interface ExchangeAccount {
  id: number;
  exchange: 'binance' | 'okx';
  account_type: 'spot' | 'futures' | 'earn';
  name: string;
  api_key: string;
  // api_secret and passphrase are write-only and not returned in responses
  testnet: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_tested_at: string | null;
  // Health monitoring fields (Step 5 - connector health)
  last_success_at: string | null;
  last_latency_ms: number | null;
  last_error_code: string | null;
  last_error_at: string | null;
}

export interface ExchangeAccountCreateRequest {
  exchange: 'binance' | 'okx';
  account_type: 'spot' | 'futures' | 'earn';
  name: string;
  api_key: string;
  api_secret: string;
  passphrase?: string; // Required for OKX, optional for others
  testnet: boolean;
  is_active: boolean;
}

export interface ExchangeAccountUpdateRequest {
  exchange?: 'binance' | 'okx';
  account_type?: 'spot' | 'futures' | 'earn';
  name?: string;
  api_key?: string;
  api_secret?: string;
  passphrase?: string; // Required for OKX, optional for others
  testnet?: boolean;
  is_active?: boolean;
}

// Exchange choices for UI
export const EXCHANGE_CHOICES = [
  { value: 'binance' as const, label: 'Binance' },
  { value: 'okx' as const, label: 'OKX' },
];

// Account type choices for UI
export const ACCOUNT_TYPE_CHOICES = [
  { value: 'spot' as const, label: 'Spot Trading' },
  { value: 'futures' as const, label: 'Futures Trading' },
  { value: 'earn' as const, label: 'Earn/Staking' },
];

// Health check types
export type HealthStatus =
  | 'healthy'
  | 'auth_error'
  | 'rate_limited'
  | 'down'
  | 'time_skew';

export interface HealthCheckResult {
  status: HealthStatus;
  public_ms: number | null;
  signed_ms: number | null;
  total_latency_ms: number;
  checked_at: string;
  public_success: boolean;
  signed_success: boolean;
  public_error: string | null;
  signed_error: string | null;
  error?: string;
}

export interface HealthCheckResponse {
  status: 'success' | 'error';
  connector_id: number;
  connector_name: string;
  health_check?: HealthCheckResult;
  message?: string;
}

// Helper functions for health status
export const getHealthStatusColor = (
  account: ExchangeAccount,
  windowSec: number = 60,
): string => {
  if (!account.last_success_at) return 'text-gray-500';

  const now = new Date();
  const lastSuccess = new Date(account.last_success_at);
  const diffSec = (now.getTime() - lastSuccess.getTime()) / 1000;

  return diffSec <= windowSec ? 'text-green-600' : 'text-red-600';
};

export const getHealthStatusText = (
  account: ExchangeAccount,
  windowSec: number = 60,
): string => {
  if (!account.last_success_at) return 'Не проверялся';

  const now = new Date();
  const lastSuccess = new Date(account.last_success_at);
  const diffSec = Math.floor((now.getTime() - lastSuccess.getTime()) / 1000);

  if (diffSec <= windowSec) {
    return 'Работает';
  }

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    return `${diffMin} мин назад`;
  }

  const diffHour = Math.floor(diffMin / 60);
  return `${diffHour} ч назад`;
};
