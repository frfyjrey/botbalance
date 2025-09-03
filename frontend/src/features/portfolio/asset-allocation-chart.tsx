import React from 'react';
import { useTranslation } from 'react-i18next';

// Using GitHub-style card design like BalancesCard
import { usePortfolioSummary, type PortfolioAsset } from '@entities/portfolio';

interface AssetAllocationChartProps {
  className?: string;
}

// Simple pie chart colors (GitHub-style)
const CHART_COLORS = [
  '#1f77b4', // Blue
  '#ff7f0e', // Orange
  '#2ca02c', // Green
  '#d62728', // Red
  '#9467bd', // Purple
  '#8c564b', // Brown
  '#e377c2', // Pink
  '#7f7f7f', // Gray
  '#bcbd22', // Olive
  '#17becf', // Cyan
];

interface PieSliceProps {
  asset: PortfolioAsset;
  startAngle: number;
  endAngle: number;
  color: string;
  radius: number;
  centerX: number;
  centerY: number;
}

const PieSlice: React.FC<PieSliceProps> = ({
  asset,
  startAngle,
  endAngle,
  color,
  radius,
  centerX,
  centerY,
}) => {
  const startAngleRad = (startAngle * Math.PI) / 180;
  const endAngleRad = (endAngle * Math.PI) / 180;

  const x1 = centerX + radius * Math.cos(startAngleRad);
  const y1 = centerY + radius * Math.sin(startAngleRad);
  const x2 = centerX + radius * Math.cos(endAngleRad);
  const y2 = centerY + radius * Math.sin(endAngleRad);

  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

  const pathData = [
    `M ${centerX} ${centerY}`,
    `L ${x1} ${y1}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
    'Z',
  ].join(' ');

  return (
    <g>
      <path
        d={pathData}
        fill={color}
        stroke="white"
        strokeWidth="2"
        className="transition-opacity hover:opacity-80"
      />
      {/* Label for larger slices */}
      {parseFloat(asset.percentage) >= 5 && (
        <text
          x={
            centerX + radius * 0.7 * Math.cos((startAngleRad + endAngleRad) / 2)
          }
          y={
            centerY + radius * 0.7 * Math.sin((startAngleRad + endAngleRad) / 2)
          }
          textAnchor="middle"
          dominantBaseline="middle"
          className="text-xs font-medium fill-white"
          style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.3)' }}
        >
          {asset.symbol}
        </text>
      )}
    </g>
  );
};

export const AssetAllocationChart: React.FC<AssetAllocationChartProps> = ({
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
            {t('portfolio.allocation_title', 'Asset Allocation')}
          </h3>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-center py-8">
            <div
              className="animate-spin rounded-full h-8 w-8 border-b-2"
              style={{ borderBottomColor: 'rgb(var(--fg-default))' }}
            ></div>
            <span className="ml-3" style={{ color: 'rgb(var(--fg-muted))' }}>
              Loading chart...
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
            {t('portfolio.allocation_title', 'Asset Allocation')}
          </h3>
        </div>
        <div className="p-6">
          <div className="text-center py-12">
            <div className="mb-4">
              <span className="text-4xl">📊</span>
            </div>
            <p
              className="text-base font-medium mb-2"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {t('portfolio.chart_unavailable', 'Chart Unavailable')}
            </p>
            <p className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              {t(
                'portfolio.chart_error_desc',
                'Unable to display asset allocation',
              )}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const assets = response.portfolio.assets;

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
            {t('portfolio.allocation_title', 'Asset Allocation')}
          </h3>
        </div>
        <div className="p-6">
          <div className="text-center py-12">
            <div className="mb-4">
              <span className="text-4xl">📊</span>
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

  const centerX = 120;
  const centerY = 120;
  const radius = 100;
  let currentAngle = -90; // Start from top

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
          {t('portfolio.allocation_title', 'Asset Allocation')}
        </h3>
      </div>
      <div className="p-6">
        <div className="flex flex-col lg:flex-row items-center gap-8">
          {/* Pie Chart */}
          <div className="flex-shrink-0">
            <svg width="240" height="240" viewBox="0 0 240 240">
              {assets.map((asset, index) => {
                const percentage = parseFloat(asset.percentage);
                const sliceAngle = (percentage / 100) * 360;
                const startAngle = currentAngle;
                const endAngle = currentAngle + sliceAngle;

                const slice = (
                  <PieSlice
                    key={asset.symbol}
                    asset={asset}
                    startAngle={startAngle}
                    endAngle={endAngle}
                    color={CHART_COLORS[index % CHART_COLORS.length]}
                    radius={radius}
                    centerX={centerX}
                    centerY={centerY}
                  />
                );

                currentAngle += sliceAngle;
                return slice;
              })}
            </svg>
          </div>

          {/* Legend */}
          <div className="flex-1 min-w-0">
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {assets.map((asset, index) => (
                <div key={asset.symbol} className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded-sm flex-shrink-0"
                    style={{
                      backgroundColor:
                        CHART_COLORS[index % CHART_COLORS.length],
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span
                        className="font-medium truncate"
                        style={{ color: 'rgb(var(--fg-default))' }}
                      >
                        {asset.symbol}
                      </span>
                      <span
                        className="text-sm font-medium ml-2"
                        style={{ color: 'rgb(var(--fg-default))' }}
                      >
                        {parseFloat(asset.percentage).toFixed(1)}%
                      </span>
                    </div>
                    <div
                      className="flex items-center justify-between text-sm"
                      style={{ color: 'rgb(var(--fg-muted))' }}
                    >
                      <span className="truncate">
                        {parseFloat(asset.balance).toLocaleString()}{' '}
                        {asset.symbol}
                      </span>
                      <span className="ml-2">
                        $
                        {parseFloat(asset.value_usd).toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
