import type { Balance, BalancesResponse } from '@shared/config/types';

/**
 * Balance utility functions
 */

export const formatCurrency = (value: number, currency = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

export const formatBalance = (balance: number, decimals = 8): string => {
  // Show more decimals for small balances, fewer for large ones
  const displayDecimals =
    balance < 1 ? Math.min(decimals, 8) : Math.min(decimals, 4);

  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: displayDecimals,
  }).format(balance);
};

export const getAssetDisplayName = (asset: string): string => {
  // Map common asset symbols to display names
  const assetNames: Record<string, string> = {
    BTC: 'Bitcoin',
    ETH: 'Ethereum',
    BNB: 'BNB',
    USDT: 'Tether USD',
    USDC: 'USD Coin',
    ADA: 'Cardano',
    SOL: 'Solana',
  };

  return assetNames[asset] || asset;
};

export const sortBalancesByValue = (balances: Balance[]): Balance[] => {
  return [...balances].sort((a, b) => b.usd_value - a.usd_value);
};

export const getBalancePercentage = (
  balance: Balance,
  totalValue: number,
): number => {
  if (totalValue === 0) return 0;
  return (balance.usd_value / totalValue) * 100;
};

export const hasBalances = (
  response: BalancesResponse | undefined,
): boolean => {
  return !!(response?.balances && response.balances.length > 0);
};

export const getTotalValue = (
  response: BalancesResponse | undefined,
): number => {
  return response?.total_usd_value || 0;
};

export const getBalancesCount = (
  response: BalancesResponse | undefined,
): number => {
  return response?.balances?.length || 0;
};

/**
 * Check if the API response indicates fallback data was used due to external API issues
 */
export const isFallbackData = (
  response: BalancesResponse | undefined,
): boolean => {
  return response?.details?.fallback_attempted === true;
};

/**
 * Get user-friendly message explaining data freshness status
 */
export const getDataFreshnessMessage = (
  response: BalancesResponse | undefined,
): string | null => {
  if (isFallbackData(response)) {
    return '⚠️ Данные могут быть неактуальными из-за временных проблем с внешними сервисами';
  }
  return null;
};
