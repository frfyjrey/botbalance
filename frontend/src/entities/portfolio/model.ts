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
}
