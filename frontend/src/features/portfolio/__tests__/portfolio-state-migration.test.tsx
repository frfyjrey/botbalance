/**
 * Tests for Stage C: Frontend migration to PortfolioState API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from '@shared/lib/i18n';

import {
  parsePortfolioError,
  formatTimeAgo,
  isDataStale,
} from '@shared/lib/portfolio-errors';
import { PortfolioErrorDisplay } from '../portfolio-error-display';
import { StaleDataBadge } from '../stale-data-badge';

// Mock constants with needed exports
vi.mock('@shared/config/constants', async importOriginal => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    FEATURE_FLAGS: {
      STATE_API: true,
    },
    QUERY_KEYS: {
      ...(actual.QUERY_KEYS as Record<string, string>),
      PORTFOLIO_STATE: 'portfolio-state',
    },
  };
});

describe('Stage C: PortfolioState Migration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>{component}</I18nextProvider>
      </QueryClientProvider>,
    );
  };

  describe('parsePortfolioError', () => {
    it('should parse NO_STATE error (404)', () => {
      const error = { status: 404 };
      const result = parsePortfolioError(error);

      expect(result.isError).toBe(true);
      expect(result.errorType).toBe('NO_STATE');
      expect(result.showRefreshButton).toBe(true);
    });

    it('should parse NO_ACTIVE_STRATEGY error (409)', () => {
      const error = {
        response: {
          status: 409,
          data: { error_code: 'NO_ACTIVE_STRATEGY' },
        },
      };
      const result = parsePortfolioError(error);

      expect(result.isError).toBe(true);
      expect(result.errorType).toBe('NO_ACTIVE_STRATEGY');
      expect(result.showRefreshButton).toBe(false);
    });

    it('should parse ERROR_PRICING error (422) with missing prices', () => {
      const error = {
        response: {
          status: 422,
          data: {
            error_code: 'ERROR_PRICING',
            errors: { missing_prices: ['BTCUSDT', 'ETHUSDT'] },
          },
        },
      };
      const result = parsePortfolioError(error);

      expect(result.isError).toBe(true);
      expect(result.errorType).toBe('ERROR_PRICING');
      expect(result.missingPrices).toEqual(['BTCUSDT', 'ETHUSDT']);
      expect(result.showRefreshButton).toBe(true);
    });

    it('should parse TOO_MANY_REQUESTS error (429)', () => {
      const error = {
        response: {
          status: 429,
          data: { error_code: 'TOO_MANY_REQUESTS' },
        },
      };
      const result = parsePortfolioError(error);

      expect(result.isError).toBe(true);
      expect(result.errorType).toBe('TOO_MANY_REQUESTS');
      expect(result.showRefreshButton).toBe(false);
    });

    it('should handle unknown errors', () => {
      const error = { message: 'Something went wrong' };
      const result = parsePortfolioError(error);

      expect(result.isError).toBe(true);
      expect(result.errorType).toBe('UNKNOWN');
      expect(result.errorMessage).toBe('Something went wrong');
      expect(result.showRefreshButton).toBe(true);
    });

    it('should return no error for null/undefined', () => {
      const result = parsePortfolioError(null);
      expect(result.isError).toBe(false);
    });
  });

  describe('formatTimeAgo', () => {
    it('should format seconds correctly', () => {
      const now = new Date();
      const timestamp = new Date(now.getTime() - 30 * 1000).toISOString();
      const result = formatTimeAgo(timestamp);
      expect(result).toBe('30s ago');
    });

    it('should format minutes correctly', () => {
      const now = new Date();
      const timestamp = new Date(now.getTime() - 5 * 60 * 1000).toISOString();
      const result = formatTimeAgo(timestamp);
      expect(result).toBe('5m ago');
    });

    it('should format hours correctly', () => {
      const now = new Date();
      const timestamp = new Date(
        now.getTime() - 2 * 60 * 60 * 1000,
      ).toISOString();
      const result = formatTimeAgo(timestamp);
      expect(result).toBe('2h ago');
    });

    it('should format days correctly', () => {
      const now = new Date();
      const timestamp = new Date(
        now.getTime() - 3 * 24 * 60 * 60 * 1000,
      ).toISOString();
      const result = formatTimeAgo(timestamp);
      expect(result).toBe('3d ago');
    });

    it('should handle timestamps without Z suffix', () => {
      const now = new Date();
      const timestamp = new Date(now.getTime() - 30 * 1000)
        .toISOString()
        .slice(0, -1);
      const result = formatTimeAgo(timestamp);
      expect(result).toBe('30s ago');
    });

    it('should handle invalid timestamps', () => {
      const result = formatTimeAgo('invalid');
      expect(result).toBe('unknown');
    });
  });

  describe('isDataStale', () => {
    it('should detect stale data (>5 minutes)', () => {
      const now = new Date();
      const timestamp = new Date(now.getTime() - 10 * 60 * 1000).toISOString();
      expect(isDataStale(timestamp)).toBe(true);
    });

    it('should detect fresh data (<5 minutes)', () => {
      const now = new Date();
      const timestamp = new Date(now.getTime() - 2 * 60 * 1000).toISOString();
      expect(isDataStale(timestamp)).toBe(false);
    });

    it('should handle custom threshold', () => {
      const now = new Date();
      const timestamp = new Date(now.getTime() - 3 * 60 * 1000).toISOString();
      expect(isDataStale(timestamp, 2)).toBe(true); // 3 min > 2 min threshold
      expect(isDataStale(timestamp, 5)).toBe(false); // 3 min < 5 min threshold
    });

    it('should handle invalid timestamps as stale', () => {
      expect(isDataStale('invalid')).toBe(true);
    });
  });

  describe('PortfolioErrorDisplay Component', () => {
    it('should render NO_STATE error with refresh button', () => {
      const errorDetails = {
        isError: true,
        errorType: 'NO_STATE' as const,
        showRefreshButton: true,
      };
      const onRefresh = vi.fn();

      renderWithProviders(
        <PortfolioErrorDisplay
          errorDetails={errorDetails}
          onRefresh={onRefresh}
        />,
      );

      expect(screen.getByText(/нет данных портфеля/i)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /обновить/i }),
      ).toBeInTheDocument();
    });

    it('should render ERROR_PRICING error with missing prices', () => {
      const errorDetails = {
        isError: true,
        errorType: 'ERROR_PRICING' as const,
        missingPrices: ['BTCUSDT', 'ETHUSDT'],
        showRefreshButton: true,
      };

      renderWithProviders(
        <PortfolioErrorDisplay errorDetails={errorDetails} />,
      );

      expect(screen.getByText(/не удалось получить цены/i)).toBeInTheDocument();
      expect(screen.getByText('BTCUSDT, ETHUSDT')).toBeInTheDocument();
    });

    it('should render NO_ACTIVE_STRATEGY error without refresh button', () => {
      const errorDetails = {
        isError: true,
        errorType: 'NO_ACTIVE_STRATEGY' as const,
        showRefreshButton: false,
      };

      renderWithProviders(
        <PortfolioErrorDisplay errorDetails={errorDetails} />,
      );

      expect(screen.getByText(/нет активной стратегии/i)).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /обновить/i }),
      ).not.toBeInTheDocument();
    });

    it('should render TOO_MANY_REQUESTS error', () => {
      const errorDetails = {
        isError: true,
        errorType: 'TOO_MANY_REQUESTS' as const,
        showRefreshButton: false,
      };

      renderWithProviders(
        <PortfolioErrorDisplay errorDetails={errorDetails} />,
      );

      expect(screen.getByText(/слишком частые запросы/i)).toBeInTheDocument();
    });

    it('should not render when no error', () => {
      const errorDetails = { isError: false };

      const { container } = renderWithProviders(
        <PortfolioErrorDisplay errorDetails={errorDetails} />,
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('StaleDataBadge Component', () => {
    it('should render stale badge with warning', () => {
      renderWithProviders(
        <StaleDataBadge isStale={true} timeAgo="10m ago" quoteAsset="USDT" />,
      );

      expect(screen.getByText('USDT')).toBeInTheDocument();
      expect(screen.getByText('⚠️ 10m ago')).toBeInTheDocument();
    });

    it('should render fresh badge without warning', () => {
      renderWithProviders(
        <StaleDataBadge isStale={false} timeAgo="2m ago" quoteAsset="USDT" />,
      );

      expect(screen.getByText('USDT')).toBeInTheDocument();
      expect(screen.getByText('2m ago')).toBeInTheDocument();
      expect(screen.queryByText('⚠️')).not.toBeInTheDocument();
    });

    it('should not render without timeAgo', () => {
      const { container } = renderWithProviders(
        <StaleDataBadge isStale={false} />,
      );

      expect(container.firstChild).toBeNull();
    });
  });
});
