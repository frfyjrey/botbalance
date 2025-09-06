import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@shared/ui/Button';
import { formatNumberEnUS } from '@shared/lib/utils';
import { usePortfolioSummary, type PortfolioAsset } from '@entities/portfolio';
import {
  useBalances,
  getAssetDisplayName,
  getTotalValue,
  sortBalancesByValue,
  getBalancePercentage,
} from '@entities/balance';

interface PortfolioAssetsCardProps {
  className?: string;
  maxItems?: number;
}

const formatBalance = (balance: string | number, symbol: string) => {
  const num = typeof balance === 'number' ? balance : parseFloat(balance);
  if (num === 0) return `0 ${symbol}`;
  if (num < 0.001 && symbol !== 'USDT') return `<0.001 ${symbol}`;
  const fraction = symbol === 'USDT' ? 2 : 8;
  return `${formatNumberEnUS(num, { maximumFractionDigits: fraction })} ${symbol}`;
};

const formatValue = (value: string | number) => {
  const num = typeof value === 'number' ? value : parseFloat(value);
  return `$${formatNumberEnUS(num, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatPrice = (price: string | number | null | undefined) => {
  if (!price) return 'N/A';
  const num = typeof price === 'number' ? price : parseFloat(price);
  if (num < 0.01) return `$${num.toFixed(6)}`;
  return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const getPriceSourceColor = (source: string) => {
  switch (source) {
    case 'cached':
      return 'bg-green-100 text-green-800';
    case 'fresh':
      return 'bg-blue-100 text-blue-800';
    case 'stablecoin':
      return 'bg-gray-100 text-gray-800';
    case 'mock':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const getAssetIcon = (asset: string) => {
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

export const PortfolioAssetsCard: React.FC<PortfolioAssetsCardProps> = ({
  className,
  maxItems = 10,
}) => {
  const { t } = useTranslation('dashboard');
  const { data: response } = usePortfolioSummary();
  const { data: balancesData, isLoading, isError } = useBalances();
  const [showAll, setShowAll] = React.useState(false);

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
            {t('portfolio.new_portfolio', 'Новый Портфель')}
          </h3>
        </div>
        <div className="p-4">
          <div className="flex items-center justify-center py-8">
            <div
              className="animate-spin rounded-full h-8 w-8 border-b-2"
              style={{ borderBottomColor: 'rgb(var(--fg-default))' }}
            ></div>
            <span className="ml-3" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t('balances.loading')}
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (
    isError ||
    !balancesData ||
    !balancesData.balances ||
    balancesData.balances.length === 0
  ) {
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
            {t('portfolio.new_portfolio', 'Новый Портфель')}
          </h3>
        </div>
        <div className="p-6">
          <div className="text-center py-8">
            <div className="mb-4">
              <span className="text-4xl">📋</span>
            </div>
            <p
              className="text-base font-medium mb-2"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {t('balances.no_balances')}
            </p>
            <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t('balances.deposit_funds')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const portfolioMap: Record<string, PortfolioAsset> =
    response && response.status === 'success' && response.portfolio
      ? Object.fromEntries(response.portfolio.assets.map(a => [a.symbol, a]))
      : {};

  const totalValue = getTotalValue(balancesData);
  const sortedBalances = sortBalancesByValue(balancesData.balances ?? []);
  const totalAssets = sortedBalances.length;
  const visibleBalances = showAll
    ? sortedBalances
    : sortedBalances.slice(0, maxItems);

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
            {t('portfolio.new_portfolio', 'Новый Портфель')}
          </h3>
          <div className="flex items-center gap-3">
            {totalAssets > maxItems && (
              <>
                <span
                  className="text-xs"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  {showAll
                    ? t('portfolio.showing_all', 'Показаны все {{total}}', {
                        total: totalAssets,
                      })
                    : t(
                        'portfolio.showing_assets',
                        'Показано {{shown}} из {{total}}',
                        {
                          shown: maxItems,
                          total: totalAssets,
                        },
                      )}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAll(prev => !prev)}
                >
                  {showAll
                    ? t('portfolio.show_less', 'Скрыть')
                    : t('portfolio.show_all', 'Показать все')}
                </Button>
              </>
            )}
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
        </div>
        <div className="mt-2">
          <div
            className="text-2xl font-bold"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {formatValue(totalValue)}
          </div>
          <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
            {t('balances.total_value')}
          </p>
        </div>
      </div>

      <div className="p-0">
        <div className="space-y-0">
          {/* Header */}
          <div
            className="flex items-center py-3 px-4 text-xs font-medium uppercase tracking-wider border-b"
            style={{
              color: 'rgb(var(--fg-muted))',
              borderBottomColor: 'rgb(var(--border))',
            }}
          >
            <div className="w-8">{t('portfolio.rank_header', '#')}</div>
            <div className="flex-1 mx-4">
              {t('portfolio.asset_header', 'Asset')}
            </div>
            <div className="flex-shrink-0 text-right mr-4">
              {t('portfolio.price_header', 'Price')}
            </div>
            <div className="flex-shrink-0 text-right w-24">
              {t('portfolio.value_header', 'Value')}
            </div>
          </div>

          {/* Rows */}
          {visibleBalances.map((item, index: number) => {
            const info = portfolioMap[item.asset];
            return (
              <div
                key={item.asset}
                className="flex items-center py-3 px-4 border-b last:border-b-0"
                style={{ borderBottomColor: 'rgb(var(--border))' }}
              >
                {/* Rank */}
                <div className="flex-shrink-0 w-8 text-center">
                  <span
                    className="text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-muted))' }}
                  >
                    #{index + 1}
                  </span>
                </div>

                {/* Asset Info */}
                <div className="flex-1 min-w-0 mx-4">
                  <div className="flex items-center gap-3">
                    {/* Icon */}
                    {getAssetIcon(item.asset)}
                    <div className="flex items-center gap-2 min-w-0">
                      <h4
                        className="font-semibold truncate"
                        style={{ color: 'rgb(var(--fg-default))' }}
                      >
                        {getAssetDisplayName(item.asset)}
                      </h4>
                      {info?.price_source && (
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${getPriceSourceColor(info.price_source)}`}
                        >
                          {info.price_source}
                        </span>
                      )}
                    </div>
                  </div>
                  <p
                    className="text-sm truncate"
                    style={{ color: 'rgb(var(--fg-muted))' }}
                  >
                    {formatBalance(item.balance, item.asset)}
                  </p>
                </div>

                {/* Price */}
                <div className="flex-shrink-0 text-right mr-4">
                  <div
                    className="text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    {formatPrice(info?.price_usd)}
                  </div>
                </div>

                {/* Value */}
                <div className="flex-shrink-0 text-right w-24">
                  <div
                    className="text-sm font-semibold"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    {formatValue(item.usd_value)}
                  </div>
                  <div
                    className="text-xs"
                    style={{ color: 'rgb(var(--fg-muted))' }}
                  >
                    {getBalancePercentage(item, totalValue).toFixed(1)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
