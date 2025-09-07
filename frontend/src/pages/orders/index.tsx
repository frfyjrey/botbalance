import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AppHeader } from '@widgets/layout/app-header';
import { useNavigate } from 'react-router-dom';
import { QUERY_KEYS, ROUTES } from '@shared/config/constants';
import { apiClient } from '@shared/lib/api';
import { Button } from '@shared/ui/Button';
import { formatZeroAware } from '@shared/lib/utils';

const OrdersPage = () => {
  const { t } = useTranslation(['common']);
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = useState<string>('');
  const [symbolFilter, setSymbolFilter] = useState<string>('');
  const [sideFilter, setSideFilter] = useState<string>('');
  const [exchangeFilter, setExchangeFilter] = useState<string>('');

  const qc = useQueryClient();

  const ordersQuery = useQuery({
    queryKey: [
      QUERY_KEYS.ORDERS,
      statusFilter,
      symbolFilter,
      sideFilter,
      exchangeFilter,
    ],
    queryFn: () =>
      apiClient.getOrders({
        limit: 50,
        status: statusFilter || undefined,
        symbol: symbolFilter || undefined,
        side: sideFilter || undefined,
        exchange: exchangeFilter || undefined,
      }),
    refetchInterval: 30000,
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
            className="btn-github btn-github-secondary text-xs sm:text-sm"
          >
            {t('common:refresh')}
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
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {ordersQuery.data?.orders?.map(o => (
                <tr key={o.id} className="border-b hover:bg-muted/30">
                  <td className="p-2">{o.id}</td>
                  <td className="p-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 capitalize">
                      {o.exchange}
                    </span>
                  </td>
                  <td className="p-2">{o.symbol}</td>
                  <td className="p-2 uppercase">{o.side}</td>
                  <td className="p-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${
                        o.status === 'open'
                          ? 'bg-blue-50 text-blue-700 border-blue-200'
                          : o.status === 'filled'
                            ? 'bg-green-50 text-green-700 border-green-200'
                            : o.status === 'cancelled'
                              ? 'bg-zinc-100 text-zinc-700 border-zinc-300'
                              : o.status === 'submitted'
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : o.status === 'rejected' ||
                                    o.status === 'failed'
                                  ? 'bg-red-50 text-red-700 border-red-200'
                                  : 'bg-gray-50 text-gray-700 border-gray-200'
                      }`}
                    >
                      {o.status}
                    </span>
                  </td>
                  <td className="p-2 text-right">{o.limit_price}</td>
                  <td className="p-2 text-right">{o.quote_amount}</td>
                  <td className="p-2 text-right">
                    {formatZeroAware(o.filled_amount)}
                  </td>
                  <td className="p-2 text-right">
                    {formatZeroAware(o.fill_percentage)}
                  </td>
                  <td className="p-2">
                    {o.is_active ? (
                      <Button
                        disabled={cancelingIds.has(o.id)}
                        onClick={() => cancelMutation.mutate(o.id)}
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
              ))}
              {!ordersQuery.data?.orders?.length && (
                <tr>
                  <td
                    className="p-4 text-center text-muted-foreground"
                    colSpan={10}
                  >
                    {ordersQuery.isLoading ? 'Loading…' : 'No orders'}
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
