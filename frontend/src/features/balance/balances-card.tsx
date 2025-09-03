import { useTranslation } from 'react-i18next';
import { useBalances, formatCurrency, formatBalance, getAssetDisplayName, sortBalancesByValue, getTotalValue } from '@entities/balance';
import type { Balance } from '@shared/config/types';

interface BalancesCardProps {
  className?: string;
}

export const BalancesCard = ({ className }: BalancesCardProps) => {
  const { t } = useTranslation('dashboard');
  const { data: balancesData, isLoading, isError, error } = useBalances();

  const getBalancePercentage = (balance: Balance, totalValue: number): number => {
    if (totalValue === 0) return 0;
    return (balance.usd_value / totalValue) * 100;
  };

  const getAssetIcon = (asset: string) => {
    // Simple colored circles for different assets
    const colors: Record<string, string> = {
      BTC: '#F7931A',
      ETH: '#627EEA',
      BNB: '#F3BA2F',
      USDT: '#26A17B',
      USDC: '#2775CA',
      ADA: '#0033AD',
      SOL: '#66D9EF',
    };

    const color = colors[asset] || '#6B7280';

    return (
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
        style={{ backgroundColor: color }}
      >
        {asset.substring(0, 2)}
      </div>
    );
  };

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
            {t('balances.portfolio')}
          </h3>
        </div>
        <div className="p-4">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderBottomColor: 'rgb(var(--fg-default))' }}></div>
            <span className="ml-3" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t('balances.loading')}
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    const errorMessage = error?.message || t('balances.error');
    const isNoAccounts = error && 'message' in error && 
      error.message.includes('No active exchange accounts found');

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
            {t('balances.portfolio')}
          </h3>
        </div>
        <div className="p-4">
          <div className="text-center py-8">
            <div className="mb-4">
              {isNoAccounts ? (
                <svg
                  className="w-12 h-12 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
              ) : (
                <svg
                  className="w-12 h-12 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              )}
            </div>
            <p
              className="text-base font-medium mb-2"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {isNoAccounts ? t('balances.no_accounts') : t('balances.error')}
            </p>
            <p
              className="text-sm"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {isNoAccounts 
                ? t('balances.add_exchange_account') 
                : errorMessage
              }
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!balancesData?.balances || balancesData.balances.length === 0) {
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
            {t('balances.portfolio')}
          </h3>
        </div>
        <div className="p-4">
          <div className="text-center py-8">
            <div className="mb-4">
              <svg
                className="w-12 h-12 mx-auto"
                fill="none"
                stroke="currentColor"
                style={{ color: 'rgb(var(--fg-muted))' }}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
                />
              </svg>
            </div>
            <p
              className="text-base font-medium mb-2"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {t('balances.no_balances')}
            </p>
            <p
              className="text-sm"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {t('balances.deposit_funds')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const totalValue = getTotalValue(balancesData);
  const sortedBalances = sortBalancesByValue(balancesData.balances);

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
            {t('balances.portfolio')}
          </h3>
          {balancesData.exchange_account && (
            <span
              className="px-2 py-1 rounded text-xs font-medium"
              style={{
                backgroundColor: 'rgb(var(--alert-info-bg))',
                color: 'rgb(var(--fg-default))',
              }}
            >
              {balancesData.exchange_account}
            </span>
          )}
        </div>
        <div className="mt-2">
          <div
            className="text-2xl font-bold"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {formatCurrency(totalValue)}
          </div>
          <p
            className="text-sm"
            style={{ color: 'rgb(var(--fg-muted))' }}
          >
            {t('balances.total_value')}
          </p>
        </div>
      </div>
      
      <div className="p-4">
        <div className="space-y-3">
          {sortedBalances.map((balance) => {
            const percentage = getBalancePercentage(balance, totalValue);
            return (
              <div key={balance.asset} className="flex items-center space-x-3">
                {getAssetIcon(balance.asset)}
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p
                        className="text-sm font-medium truncate"
                        style={{ color: 'rgb(var(--fg-default))' }}
                      >
                        {getAssetDisplayName(balance.asset)}
                      </p>
                      <p
                        className="text-xs truncate"
                        style={{ color: 'rgb(var(--fg-muted))' }}
                      >
                        {formatBalance(balance.balance)} {balance.asset}
                      </p>
                    </div>
                    <div className="text-right ml-4">
                      <p
                        className="text-sm font-medium"
                        style={{ color: 'rgb(var(--fg-default))' }}
                      >
                        {formatCurrency(balance.usd_value)}
                      </p>
                      <p
                        className="text-xs"
                        style={{ color: 'rgb(var(--fg-muted))' }}
                      >
                        {percentage.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                  
                  {/* Progress bar for percentage */}
                  <div className="mt-2">
                    <div
                      className="h-1 rounded-full"
                      style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
                    >
                      <div
                        className="h-1 rounded-full transition-all duration-300"
                        style={{
                          backgroundColor: 'rgb(var(--accent-emphasis))',
                          width: `${Math.min(percentage, 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {balancesData.timestamp && (
          <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgb(var(--border))' }}>
            <p
              className="text-xs text-center"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {t('balances.last_updated')}: {new Date(balancesData.timestamp).toLocaleString()}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
