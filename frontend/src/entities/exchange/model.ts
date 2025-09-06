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
