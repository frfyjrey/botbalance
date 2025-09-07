import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@shared/ui/Button';
import type { ErrorHandlingResult } from '@shared/lib/portfolio-errors';

interface PortfolioErrorDisplayProps {
  errorDetails: ErrorHandlingResult;
  onRefresh?: () => void;
  isRefreshLoading?: boolean;
  className?: string;
}

export const PortfolioErrorDisplay: React.FC<PortfolioErrorDisplayProps> = ({
  errorDetails,
  onRefresh,
  isRefreshLoading = false,
  className = '',
}) => {
  const { t } = useTranslation('common');

  if (!errorDetails.isError) {
    return null;
  }

  const getErrorMessage = () => {
    switch (errorDetails.errorType) {
      case 'NO_STATE':
        return t('errors.portfolio.no_state');
      case 'NO_ACTIVE_STRATEGY':
        return t('errors.portfolio.no_active_strategy');
      case 'ERROR_PRICING':
        const assets = errorDetails.missingPrices?.join(', ') || '';
        return t('errors.portfolio.pricing_error', { assets });
      case 'TOO_MANY_REQUESTS':
        return t('errors.portfolio.rate_limit');
      default:
        return errorDetails.errorMessage || t('error');
    }
  };

  const getActionButton = () => {
    if (!errorDetails.showRefreshButton || !onRefresh) {
      return null;
    }

    if (errorDetails.errorType === 'TOO_MANY_REQUESTS') {
      return (
        <p className="mt-2 text-sm opacity-70">
          {t('errors.portfolio.rate_limit')}
        </p>
      );
    }

    return (
      <Button
        onClick={onRefresh}
        disabled={isRefreshLoading}
        className="mt-3 btn-github btn-github-primary text-sm"
      >
        {isRefreshLoading ? t('loading') : t('refresh')}
      </Button>
    );
  };

  const getIcon = () => {
    switch (errorDetails.errorType) {
      case 'NO_STATE':
        return '📊';
      case 'NO_ACTIVE_STRATEGY':
        return '🎯';
      case 'ERROR_PRICING':
        return '💰';
      case 'TOO_MANY_REQUESTS':
        return '⏱️';
      default:
        return '❌';
    }
  };

  return (
    <div className={`card-github ${className}`}>
      <div className="p-6 text-center">
        <div className="text-4xl mb-3">{getIcon()}</div>
        <h3 
          className="text-base font-medium mb-2"
          style={{ color: 'rgb(var(--fg-default))' }}
        >
          {t('error')}
        </h3>
        <p 
          className="text-sm mb-4 opacity-80"
          style={{ color: 'rgb(var(--fg-muted))' }}
        >
          {getErrorMessage()}
        </p>
        
        {errorDetails.errorType === 'ERROR_PRICING' && errorDetails.missingPrices && (
          <div className="mb-4">
            <div className="text-xs font-mono bg-gray-100 dark:bg-gray-800 p-2 rounded text-left">
              {errorDetails.missingPrices.join(', ')}
            </div>
          </div>
        )}
        
        {getActionButton()}
        
        {errorDetails.errorType === 'NO_ACTIVE_STRATEGY' && (
          <p className="mt-3 text-xs opacity-60">
            Please configure your trading strategy first
          </p>
        )}
      </div>
    </div>
  );
};
