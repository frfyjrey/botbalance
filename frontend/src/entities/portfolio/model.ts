/**
 * Portfolio domain models for Step 2: Portfolio Snapshot
 */

export interface PortfolioAsset {
  symbol: string;
  balance: string;
  price_usd: string | null;
  value_usd: string;
  percentage: string;
  price_source: string;
}

export interface PortfolioCacheStats {
  cache_backend: string;
  default_ttl: number;
  stale_threshold: number;
  supported_quotes: string[];
}

export interface PortfolioSummary {
  total_nav: string;
  assets: PortfolioAsset[];
  quote_currency: string;
  timestamp: string;
  exchange_account: string;
  price_cache_stats: PortfolioCacheStats;
}

export interface PortfolioSummaryResponse {
  status: string;
  portfolio?: PortfolioSummary;
  message?: string;
  error_code?: string;
  exchange_account?: {
    id: number;
    name: string;
    exchange: string;
    account_type: string;
    testnet: boolean;
    is_active: boolean;
  };
  exchange_status?: {
    is_available: boolean;
    last_successful_fetch?: string;
    using_fallback_data: boolean;
    fallback_age_minutes?: number;
    next_retry_in_seconds?: number;
    circuit_breaker_status?: {
      exchange: string;
      account_type: string;
      testnet: boolean;
      is_available: boolean;
      circuit_breaker: {
        exchange_key: string;
        is_open: boolean;
        failure_count: number;
        failure_threshold: number;
        last_failure_time: number;
        time_until_retry_seconds: number;
      };
    };
  };
}

/**
 * Check if exchange is unavailable and we're using fallback data
 */
export const isUsingFallbackData = (
  response: PortfolioSummaryResponse | undefined,
): boolean => {
  return response?.exchange_status?.using_fallback_data === true;
};

/**
 * Get user-friendly exchange status message
 */
export const getExchangeStatusMessage = (
  response: PortfolioSummaryResponse | undefined,
): string | null => {
  if (isUsingFallbackData(response)) {
    const ageMinutes = response?.exchange_status?.fallback_age_minutes || 0;
    const ageText =
      ageMinutes < 60
        ? `${ageMinutes} мин назад`
        : `${Math.floor(ageMinutes / 60)} ч ${ageMinutes % 60} мин назад`;

    // Get retry timing from circuit breaker if available
    const retrySeconds = response?.exchange_status?.next_retry_in_seconds;
    const retryText =
      retrySeconds && retrySeconds > 0
        ? ` Повтор через ${Math.floor(retrySeconds / 60)} мин.`
        : ' Повтор через несколько минут.';

    // Get exchange info if available
    const exchangeInfo = response?.exchange_status?.circuit_breaker_status;
    const exchangeText = exchangeInfo
      ? `${exchangeInfo.exchange.toUpperCase()}${exchangeInfo.testnet ? ' testnet' : ''}`
      : 'Биржа';

    return `⚠️ ${exchangeText} временно недоступна. Показаны данные от ${ageText}.${retryText}`;
  }
  return null;
};
