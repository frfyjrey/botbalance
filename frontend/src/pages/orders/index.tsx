import { useState, memo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AppHeader } from '@widgets/layout/app-header';
import { useNavigate } from 'react-router-dom';
import {
  QUERY_KEYS,
  QUERY_KEY_FACTORIES,
  ROUTES,
} from '@shared/config/constants';
import { apiClient } from '@shared/lib/api';
import { Button } from '@shared/ui/Button';
import { formatZeroAware } from '@shared/lib/utils';

// Типы для ордера
type Order = {
  id: number;
  exchange_order_id: string | null;
  client_order_id: string | null;
  exchange: string;
  symbol: string;
  side: 'buy' | 'sell';
  status: string;
  limit_price: string;
  quote_amount: string;
  filled_amount: string;
  fill_percentage: string;
  fee_amount: string;
  fee_asset: string | null;
  created_at: string;
  submitted_at: string | null;
  filled_at: string | null;
  updated_at: string;
  error_message: string | null;
  strategy_name: string | null;
  execution_id: number | null;
  is_active: boolean;
};

// Вспомогательная функция для стилизации статуса
const getStatusClassNames = (status: string): string => {
  const baseClasses =
    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border';

  switch (status) {
    case 'open':
      return `${baseClasses} bg-blue-50 text-blue-700 border-blue-200`;
    case 'filled':
      return `${baseClasses} bg-green-50 text-green-700 border-green-200`;
    case 'cancelled':
      return `${baseClasses} bg-zinc-100 text-zinc-700 border-zinc-300`;
    case 'submitted':
      return `${baseClasses} bg-amber-50 text-amber-700 border-amber-200`;
    case 'rejected':
    case 'failed':
      return `${baseClasses} bg-red-50 text-red-700 border-red-200`;
    default:
      return `${baseClasses} bg-gray-50 text-gray-700 border-gray-200`;
  }
};

// Форматирование даты
const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '—';
  }
};

// Форматирование процента исполнения (округление до целых)
const formatFillPercentage = (percentage: string): string => {
  const num = parseFloat(percentage);
  if (isNaN(num)) return '0';
  return Math.round(num).toString();
};

// Мемоизированный компонент строки таблицы
const OrderRow = memo<{
  order: Order;
  cancelingIds: Set<number>;
  onCancel: (id: number) => void;
  t: (key: string) => string;
}>(({ order: o, cancelingIds, onCancel, t }) => {
  return (
    <tr key={o.id} className="border-b hover:bg-muted/30">
      <td className="p-2 text-sm">{o.id}</td>
      <td className="p-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 capitalize">
          {o.exchange}
        </span>
      </td>
      <td className="p-2 font-mono text-sm">{o.symbol}</td>
      <td className="p-2 uppercase text-sm font-semibold">
        <span className={o.side === 'buy' ? 'text-green-600' : 'text-red-600'}>
          {o.side}
        </span>
      </td>
      <td className="p-2">
        <span className={getStatusClassNames(o.status)}>{o.status}</span>
      </td>
      <td className="p-2 text-right text-sm font-mono">{o.limit_price}</td>
      <td className="p-2 text-right text-sm font-mono">{o.quote_amount}</td>
      <td className="p-2 text-right text-sm font-mono">
        {formatZeroAware(o.filled_amount)}
      </td>
      <td className="p-2 text-right text-sm font-semibold">
        {formatFillPercentage(o.fill_percentage)}%
      </td>
      {/* Новые поля */}
      <td className="p-2 text-right text-sm">
        {o.fee_amount && o.fee_amount !== '0'
          ? `${formatZeroAware(o.fee_amount)} ${o.fee_asset || ''}`.trim()
          : '—'}
      </td>
      <td className="p-2 text-xs text-muted-foreground">
        <div>{formatDate(o.created_at)}</div>
        {o.filled_at && (
          <div className="text-green-600 font-medium mt-0.5">
            ✓ {formatDate(o.filled_at)}
          </div>
        )}
      </td>
      <td className="p-2 text-xs">
        {o.strategy_name ? (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
            {o.strategy_name}
          </span>
        ) : (
          '—'
        )}
      </td>
      <td className="p-2">
        {o.error_message ? (
          <span className="text-red-600 text-xs" title={o.error_message}>
            ⚠️ Error
          </span>
        ) : o.is_active ? (
          <Button
            disabled={cancelingIds.has(o.id)}
            onClick={() => onCancel(o.id)}
            className="btn-github btn-github-invisible text-xs"
          >
            {cancelingIds.has(o.id)
              ? `${t('common:cancel')}…`
              : t('common:cancel')}
          </Button>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        )}
      </td>
    </tr>
  );
});

OrderRow.displayName = 'OrderRow';

const OrdersPage = () => {
  const { t } = useTranslation(['common']);
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = useState<string>('');
  const [symbolFilter, setSymbolFilter] = useState<string>('');
  const [sideFilter, setSideFilter] = useState<string>('');
  const [exchangeFilter, setExchangeFilter] = useState<string>('');

  const qc = useQueryClient();

  const ordersQuery = useQuery({
    queryKey: QUERY_KEY_FACTORIES.orders({
      status: statusFilter,
      symbol: symbolFilter,
      side: sideFilter,
      exchange: exchangeFilter,
    }),
    queryFn: () =>
      apiClient.getOrders({
        limit: 50,
        status: statusFilter || undefined,
        symbol: symbolFilter || undefined,
        side: sideFilter || undefined,
        exchange: exchangeFilter || undefined,
      }),
    refetchInterval: 5000, // Обновление каждые 5 секунд вместо 30
    refetchOnWindowFocus: true, // Обновлять при возврате к вкладке
  });

  const [cancelingIds, setCancelingIds] = useState<Set<number>>(new Set());

  const cancelMutation = useMutation({
    mutationFn: async (orderId: number) => {
      setCancelingIds(prev => new Set(prev).add(orderId));
      try {
        return await apiClient.cancelOrder(orderId);
      } finally {
        setCancelingIds(prev => {
          const next = new Set(prev);
          next.delete(orderId);
          return next;
        });
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEYS.ORDERS] }),
    onError: (error: unknown) => {
      // Handle specific error codes from backend
      const apiError = error as {
        errors?: { error_code?: string };
        error_code?: string;
        message?: string;
      };
      const errorCode = apiError?.errors?.error_code || apiError?.error_code;
      const message = apiError?.message || 'Failed to cancel order';

      if (errorCode === 'EXCHANGE_ACCOUNT_MISMATCH') {
        alert(
          `Order cancellation failed: ${message}\n\nPlease make sure you have an active account for the exchange where this order was placed.`,
        );
      } else if (errorCode === 'FEATURE_NOT_SUPPORTED') {
        alert(
          `Order cancellation failed: ${message}\n\nThis exchange does not support order cancellation through the API.`,
        );
      } else if (errorCode === 'ORDER_NOT_FOUND') {
        alert('Order not found. It may have been already cancelled or filled.');
      } else {
        alert(`Order cancellation failed: ${message}`);
      }
    },
  });

  // Мемоизированный callback для отмены ордеров
  const handleCancelOrder = useCallback(
    (orderId: number) => {
      cancelMutation.mutate(orderId);
    },
    [cancelMutation],
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader />
      <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 sm:py-6">
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h2 className="text-lg sm:text-xl font-semibold">
            {t('common:orders')}
          </h2>
          <Button
            onClick={() => navigate(ROUTES.DASHBOARD)}
            className="btn-github btn-github-secondary text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5"
          >
            {t('common:back')}
          </Button>
        </div>
        {/* Filters */}
        <div className="rounded-lg border p-3 sm:p-4 mb-4 grid grid-cols-1 sm:grid-cols-5 gap-3">
          <input
            className="w-full border rounded px-2 py-1 text-sm bg-transparent"
            placeholder={t('common:symbol')}
            value={symbolFilter}
            onChange={e => setSymbolFilter(e.target.value.toUpperCase())}
          />
          <select
            className="w-full border rounded px-2 py-1 text-sm bg-transparent"
            value={sideFilter}
            onChange={e => setSideFilter(e.target.value)}
          >
            <option value="">{t('common:side')}</option>
            <option value="buy">BUY</option>
            <option value="sell">SELL</option>
          </select>
          <select
            className="w-full border rounded px-2 py-1 text-sm bg-transparent"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="">{t('common:status')}</option>
            <option value="pending">pending</option>
            <option value="submitted">submitted</option>
            <option value="open">open</option>
            <option value="filled">filled</option>
            <option value="cancelled">cancelled</option>
            <option value="rejected">rejected</option>
            <option value="failed">failed</option>
          </select>
          <select
            className="w-full border rounded px-2 py-1 text-sm bg-transparent"
            value={exchangeFilter}
            onChange={e => setExchangeFilter(e.target.value)}
          >
            <option value="">Exchange</option>
            <option value="binance">Binance</option>
            <option value="okx">OKX</option>
          </select>
          <Button
            onClick={() => ordersQuery.refetch()}
            disabled={ordersQuery.isRefetching}
            className="btn-github btn-github-secondary text-xs sm:text-sm flex items-center gap-1.5"
          >
            {ordersQuery.isRefetching ? (
              <svg
                className="animate-spin h-3 w-3"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              <svg
                className="h-3 w-3"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            )}
            {ordersQuery.isRefetching ? 'Обновление...' : t('common:refresh')}
          </Button>
        </div>

        {/* Table */}
        <div className="rounded-lg border overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">ID</th>
                <th className="text-left p-2">Exchange</th>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Side</th>
                <th className="text-left p-2">Status</th>
                <th className="text-right p-2">Limit</th>
                <th className="text-right p-2">Quote</th>
                <th className="text-right p-2">Filled</th>
                <th className="text-right p-2">Fill %</th>
                <th className="text-right p-2">Fee</th>
                <th className="text-left p-2">Created/Filled</th>
                <th className="text-left p-2">Strategy</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {ordersQuery.data?.orders?.map(order => (
                <OrderRow
                  key={order.id}
                  order={order}
                  cancelingIds={cancelingIds}
                  onCancel={handleCancelOrder}
                  t={t}
                />
              ))}
              {ordersQuery.isError && (
                <tr>
                  <td className="p-4 text-center text-red-600" colSpan={13}>
                    Ошибка загрузки ордеров.
                    <button
                      onClick={() => ordersQuery.refetch()}
                      className="ml-2 text-blue-600 hover:underline"
                    >
                      Попробовать снова
                    </button>
                  </td>
                </tr>
              )}
              {!ordersQuery.isError && !ordersQuery.data?.orders?.length && (
                <tr>
                  <td
                    className="p-4 text-center text-muted-foreground"
                    colSpan={13}
                  >
                    {ordersQuery.isLoading
                      ? 'Загрузка ордеров...'
                      : 'Нет ордеров'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};

export default OrdersPage;
