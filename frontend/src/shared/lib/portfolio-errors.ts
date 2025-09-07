/**
 * Portfolio error handling utilities
 */

export interface PortfolioError {
  status?: number;
  response?: {
    data?: {
      error_code?: string;
      errors?: {
        missing_prices?: string[];
      };
      message?: string;
    };
  };
  message?: string;
}

export interface ErrorHandlingResult {
  isError: boolean;
  errorType?: 'NO_STATE' | 'NO_ACTIVE_STRATEGY' | 'ERROR_PRICING' | 'TOO_MANY_REQUESTS' | 'UNKNOWN';
  errorMessage?: string;
  missingPrices?: string[];
  showRefreshButton?: boolean;
}

/**
 * Parse portfolio error and return structured error info
 */
export const parsePortfolioError = (error: unknown): ErrorHandlingResult => {
  if (!error) {
    return { isError: false };
  }

  const portfolioError = error as PortfolioError;

  // Check for HTTP status codes
  const status = portfolioError.status || portfolioError.response?.status;
  const errorCode = portfolioError.response?.data?.error_code;
  const message = portfolioError.response?.data?.message || portfolioError.message;

  // 404 NO_STATE - no portfolio state exists
  if (status === 404 || errorCode === 'ERROR_NO_STATE') {
    return {
      isError: true,
      errorType: 'NO_STATE',
      showRefreshButton: true,
    };
  }

  // 409 NO_ACTIVE_STRATEGY - no active strategy for connector  
  if (status === 409 || errorCode === 'NO_ACTIVE_STRATEGY') {
    return {
      isError: true,
      errorType: 'NO_ACTIVE_STRATEGY',
      showRefreshButton: false, // Need to configure strategy first
    };
  }

  // 422 ERROR_PRICING - unable to get prices
  if (status === 422 || errorCode === 'ERROR_PRICING') {
    const missingPrices = portfolioError.response?.data?.errors?.missing_prices || [];
    return {
      isError: true,
      errorType: 'ERROR_PRICING',
      missingPrices,
      showRefreshButton: true,
    };
  }

  // 429 TOO_MANY_REQUESTS - rate limited
  if (status === 429 || errorCode === 'TOO_MANY_REQUESTS') {
    return {
      isError: true,
      errorType: 'TOO_MANY_REQUESTS',
      showRefreshButton: false, // Wait before retry
    };
  }

  // Unknown error
  return {
    isError: true,
    errorType: 'UNKNOWN',
    errorMessage: message,
    showRefreshButton: true,
  };
};

/**
 * Format time ago for stale data warning
 */
export const formatTimeAgo = (timestamp: string): string => {
  try {
    // Ensure timestamp has Z for UTC
    const ts = timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`;
    const date = new Date(ts);
    
    // Check if date is invalid
    if (isNaN(date.getTime())) {
      return 'unknown';
    }
    
    const diff = Date.now() - date.getTime();
    const seconds = Math.floor(diff / 1000);

    if (seconds < 60) {
      return `${seconds}s ago`;
    }

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
      return `${minutes}m ago`;
    }

    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
      return `${hours}h ago`;
    }

    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return 'unknown';
  }
};

/**
 * Check if data is stale (older than 5 minutes)
 */
export const isDataStale = (timestamp: string, staleThresholdMinutes = 5): boolean => {
  try {
    const ts = timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`;
    const date = new Date(ts);
    
    // Check if date is invalid
    if (isNaN(date.getTime())) {
      return true; // Consider invalid timestamps as stale
    }
    
    const diff = Date.now() - date.getTime();
    const minutes = diff / (1000 * 60);
    return minutes > staleThresholdMinutes;
  } catch {
    return true; // Consider invalid timestamps as stale
  }
};
