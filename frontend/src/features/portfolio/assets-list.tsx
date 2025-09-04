import React from 'react';
import { formatCurrencyUSD, formatNumberEnUS } from '@shared/lib/utils';
import { useTranslation } from 'react-i18next';

// Using GitHub-style card design like BalancesCard
import { usePortfolioSummary, type PortfolioAsset } from '@entities/portfolio';

interface AssetsListProps {
  className?: string;
  maxItems?: number;
}

interface AssetRowProps {
  asset: PortfolioAsset;
  rank: number;
}

const AssetRow: React.FC<AssetRowProps> = ({ asset, rank }) => {
  const formatBalance = (balance: string, symbol: string) => {
    const num = parseFloat(balance);
    if (num === 0) return `0 ${symbol}`;
    if (num < 0.001 && symbol !== 'USDT') return `<0.001 ${symbol}`;
    const fraction = symbol === 'USDT' ? 2 : 8;
    return `${formatNumberEnUS(num, { maximumFractionDigits: fraction })} ${symbol}`;
  };

  const formatValue = (value: string) => {
    const num = parseFloat(value);
    return `$${formatCurrencyUSD(num)}`;
  };

  const formatPrice = (price: string | null) => {
    if (!price) return 'N/A';
    const num = parseFloat(price);
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

  return (
    <div
      className="flex items-center py-3 px-4 border-b last:border-b-0"
      style={{ borderBottomColor: 'rgb(var(--border))' }}
    >
      {/* Rank */}
      <div className="flex-shrink-0 w-8 text-center">
        <span
          className="text-sm font-medium"
          style={{ color: 'rgb(var(--fg-muted))' }}
        >
          #{rank}
        </span>
      </div>

      {/* Asset Info */}
      <div className="flex-1 min-w-0 mx-4">
        <div className="flex items-center gap-2">
          <h4
            className="font-semibold"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {asset.symbol}
          </h4>
          <span
            className={`px-2 py-0.5 text-xs rounded-full ${getPriceSourceColor(asset.price_source)}`}
          >
            {asset.price_source}
          </span>
        </div>
        <p
          className="text-sm truncate"
          style={{ color: 'rgb(var(--fg-muted))' }}
        >
          {formatBalance(asset.balance, asset.symbol)}
        </p>
      </div>

      {/* Price */}
      <div className="flex-shrink-0 text-right mr-4">
        <div
          className="text-sm font-medium"
          style={{ color: 'rgb(var(--fg-default))' }}
        >
          {formatPrice(asset.price_usd)}
        </div>
      </div>

      {/* Value & Percentage */}
      <div className="flex-shrink-0 text-right w-24">
        <div
          className="text-sm font-semibold"
          style={{ color: 'rgb(var(--fg-default))' }}
        >
          {formatValue(asset.value_usd)}
        </div>
        <div className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
          {parseFloat(asset.percentage).toFixed(1)}%
        </div>
      </div>
    </div>
  );
};

export const AssetsList: React.FC<AssetsListProps> = ({
  className,
  maxItems = 10,
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
            {t('portfolio.assets_title', 'Portfolio Assets')}
          </h3>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-center py-8">
            <div
              className="animate-spin rounded-full h-8 w-8 border-b-2"
              style={{ borderBottomColor: 'rgb(var(--fg-default))' }}
            ></div>
            <span className="ml-3" style={{ color: 'rgb(var(--fg-muted))' }}>
              Loading assets...
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
            {t('portfolio.assets_title', 'Portfolio Assets')}
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
              {t('portfolio.assets_unavailable', 'Assets Unavailable')}
            </p>
            <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t('portfolio.assets_error_desc', 'Unable to load asset details')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const assets = response.portfolio.assets.slice(0, maxItems);
  const totalAssets = response.portfolio.assets.length;

  if (assets.length === 0) {
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
            {t('portfolio.assets_title', 'Portfolio Assets')}
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
              {t('portfolio.no_assets', 'No Assets')}
            </p>
            <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t(
                'portfolio.no_assets_desc',
                'Your portfolio is currently empty',
              )}
            </p>
          </div>
        </div>
      </div>
    );
  }

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
            {t('portfolio.assets_title', 'Portfolio Assets')}
          </h3>
          {totalAssets > maxItems && (
            <span className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t('portfolio.showing_assets', 'Showing {{shown}} of {{total}}', {
                shown: maxItems,
                total: totalAssets,
              })}
            </span>
          )}
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
            <div className="w-8"></div>
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

          {/* Asset Rows */}
          {assets.map((asset, index) => (
            <AssetRow key={asset.symbol} asset={asset} rank={index + 1} />
          ))}
        </div>
      </div>
    </div>
  );
};
