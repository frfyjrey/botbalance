import React from 'react';
import { useTranslation } from 'react-i18next';

// Using GitHub-style card design like BalancesCard
import { usePortfolioSummary } from '@entities/portfolio';

interface PortfolioSummaryCardProps {
  className?: string;
}

export const PortfolioSummaryCard: React.FC<PortfolioSummaryCardProps> = ({
  className,
}) => {
  const { t } = useTranslation('dashboard');
  const { data: response, isLoading, error } = usePortfolioSummary();

  if (isLoading) {
    return (
      <div className={`card-github ${className}`}>
        <div
          className="p-4 border-b"
          style={{ borderBottomColor: 'rgb(var(--border))' }}
        >
          <h3
            className="text-base font-semibold"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {t('portfolio.title', 'Portfolio Summary')}
          </h3>
        </div>
        <div className="p-4">
          <div className="flex items-center justify-center py-8">
            <div
              className="animate-spin rounded-full h-8 w-8 border-b-2"
              style={{ borderBottomColor: 'rgb(var(--fg-default))' }}
            ></div>
            <span className="ml-3" style={{ color: 'rgb(var(--fg-muted))' }}>
              Loading portfolio...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (
    error ||
    !response ||
    response.status !== 'success' ||
    !response.portfolio
  ) {
    const isNoAccounts = error && 'status' in error && error.status === 404;

    return (
      <div className={`card-github ${className}`}>
        <div
          className="p-4 border-b"
          style={{ borderBottomColor: 'rgb(var(--border))' }}
        >
          <h3
            className="text-base font-semibold"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {t('portfolio.title', 'Portfolio Summary')}
          </h3>
        </div>
        <div className="p-6">
          <div className="text-center py-8">
            <div className="mb-4">
              <span className="text-4xl">{isNoAccounts ? '📊' : '⚠️'}</span>
            </div>
            <p
              className="text-base font-medium mb-2"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {isNoAccounts
                ? t('portfolio.no_accounts_title', 'No Exchange Accounts')
                : t('portfolio.error_title', 'Portfolio Unavailable')}
            </p>
            <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              {isNoAccounts
                ? t(
                    'portfolio.no_accounts_desc',
                    'Add an exchange account to see your portfolio',
                  )
                : t(
                    'portfolio.error_desc',
                    'Unable to load portfolio data. Please try again later.',
                  )}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const portfolio = response.portfolio;

  return (
    <div className={`card-github ${className}`}>
      <div
        className="p-4 border-b"
        style={{ borderBottomColor: 'rgb(var(--border))' }}
      >
        <div className="flex items-center justify-between">
          <h3
            className="text-base font-semibold"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {t('portfolio.title', 'Portfolio Summary')}
          </h3>
          <span
            className="text-xs px-2 py-1 rounded"
            style={{
              backgroundColor: 'rgb(var(--color-neutral-muted))',
              color: 'rgb(var(--fg-muted))',
            }}
          >
            {portfolio.exchange_account}
          </span>
        </div>
      </div>
      <div className="p-6">
        {/* Total NAV */}
        <div className="mb-6">
          <div className="flex items-baseline gap-2 mb-1">
            <span
              className="text-3xl font-bold"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              $
              {parseFloat(portfolio.total_nav).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span
              className="text-sm font-medium"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {portfolio.quote_currency}
            </span>
          </div>
          <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
            {t('portfolio.nav_label', 'Total Net Asset Value')}
          </p>
        </div>

        {/* Assets Count */}
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: 'rgb(var(--fg-muted))' }}>
            {t('portfolio.assets_count', '{{count}} assets', {
              count: portfolio.assets.length,
            })}
          </span>
          <span style={{ color: 'rgb(var(--fg-muted))' }}>
            {new Date(portfolio.timestamp).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
};
