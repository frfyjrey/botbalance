import React from 'react';
import { useTranslation } from 'react-i18next';

interface StaleDataBadgeProps {
  isStale: boolean;
  timeAgo?: string;
  quoteAsset?: string;
  className?: string;
}

export const StaleDataBadge: React.FC<StaleDataBadgeProps> = ({
  isStale,
  timeAgo,
  quoteAsset,
  className = '',
}) => {
  const { t } = useTranslation('common');

  if (!timeAgo) {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 text-xs ${className}`}>
      {/* Quote Asset Badge */}
      {quoteAsset && (
        <span
          className="px-2 py-1 rounded-md font-medium"
          style={{
            backgroundColor: 'rgb(var(--canvas-subtle))',
            color: 'rgb(var(--fg-default))',
          }}
        >
          {quoteAsset}
        </span>
      )}

      {/* Timestamp Badge */}
      <span
        className={`px-2 py-1 rounded-md font-mono ${
          isStale ? 'text-orange-600 dark:text-orange-400' : 'opacity-60'
        }`}
        style={{
          backgroundColor: isStale
            ? 'rgba(234, 179, 8, 0.1)'
            : 'rgb(var(--canvas-subtle))',
          color: isStale ? undefined : 'rgb(var(--fg-muted))',
        }}
        title={
          isStale
            ? t('errors.stale_data', { time: timeAgo })
            : `Updated ${timeAgo}`
        }
      >
        {isStale && '⚠️ '}
        {timeAgo}
      </span>
    </div>
  );
};
