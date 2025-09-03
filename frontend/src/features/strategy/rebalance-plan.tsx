import React from 'react';

import { Button } from '@shared/ui/Button';
import {
  useRebalancePlan,
  useRefreshRebalancePlan,
  type RebalanceAction,
  ACTION_COLORS,
  ACTION_LABELS,
} from '@entities/strategy';

interface RebalancePlanProps {
  className?: string;
}

interface ActionRowProps {
  action: RebalanceAction;
  quoteCurrency: string;
}

const ActionRow: React.FC<ActionRowProps> = ({ action }) => {
  const actionColor = ACTION_COLORS[action.action];
  const actionLabel = ACTION_LABELS[action.action];

  return (
    <tr
      className="border-b"
      style={{ borderBottomColor: 'rgb(var(--border))' }}
    >
      <td className="py-3 px-2">
        <span className="font-mono text-sm font-medium">{action.asset}</span>
      </td>

      <td className="py-3 px-2">
        <div
          className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
          style={{
            backgroundColor: `${actionColor}20`,
            color: actionColor,
          }}
        >
          {actionLabel}
        </div>
      </td>

      <td className="py-3 px-2 text-sm">
        <div className="text-right">
          <div>{parseFloat(action.current_percentage).toFixed(2)}%</div>
          <div className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            ${parseFloat(action.current_value).toLocaleString()}
          </div>
        </div>
      </td>

      <td className="py-3 px-2 text-sm">
        <div className="text-right">
          <div>{parseFloat(action.target_percentage).toFixed(2)}%</div>
          <div className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            ${parseFloat(action.target_value).toLocaleString()}
          </div>
        </div>
      </td>

      <td className="py-3 px-2 text-sm text-right">
        <div
          className={`font-medium ${
            parseFloat(action.delta_value) > 0
              ? 'text-green-600'
              : parseFloat(action.delta_value) < 0
                ? 'text-red-600'
                : 'text-gray-500'
          }`}
        >
          {parseFloat(action.delta_value) >= 0 ? '+' : ''}$
          {parseFloat(action.delta_value).toLocaleString()}
        </div>
      </td>

      <td className="py-3 px-2 text-sm text-right">
        {action.order_amount &&
        action.order_volume &&
        action.order_price &&
        action.market_price ? (
          <div>
            <div className="font-medium">
              ${parseFloat(action.order_amount).toLocaleString()}
            </div>
            <div
              className="text-xs mt-1"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {parseFloat(action.order_volume).toFixed(
                action.asset === 'USDT' ? 2 : 8,
              )}{' '}
              {action.asset}
            </div>
            <div className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
              @ ${parseFloat(action.order_price).toFixed(2)}
            </div>
            <div
              className="text-xs"
              style={{ color: 'rgb(var(--color-fg-subtle))' }}
            >
              Market: ${parseFloat(action.market_price).toFixed(2)}
            </div>
          </div>
        ) : action.action === 'hold' ? (
          <div className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            No action needed
          </div>
        ) : null}
      </td>
    </tr>
  );
};

export const RebalancePlan: React.FC<RebalancePlanProps> = ({ className }) => {
  const { data: response, isLoading, error, refetch } = useRebalancePlan();
  const refreshPlan = useRefreshRebalancePlan();

  const handleRefresh = async () => {
    try {
      await refreshPlan.mutateAsync();
    } catch (error) {
      console.error('Failed to refresh rebalance plan:', error);
    }
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
            Rebalance Plan
          </h3>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-center py-8">
            <div
              className="animate-spin rounded-full h-8 w-8 border-b-2"
              style={{ borderBottomColor: 'rgb(var(--fg-default))' }}
            ></div>
            <span className="ml-3" style={{ color: 'rgb(var(--fg-muted))' }}>
              Calculating rebalance plan...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !response || response.status !== 'success' || !response.plan) {
    const isNoStrategy = error && 'status' in error && error.status === 404;
    const isInvalidStrategy =
      error && 'status' in error && error.status === 400;

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
            Rebalance Plan
          </h3>
        </div>
        <div className="p-6">
          <div className="text-center py-8">
            <div className="mb-4">
              <span className="text-4xl">
                {isNoStrategy ? '📋' : isInvalidStrategy ? '⚠️' : '💥'}
              </span>
            </div>
            <p
              className="text-base font-medium mb-2"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {isNoStrategy
                ? 'No Strategy Found'
                : isInvalidStrategy
                  ? 'Invalid Strategy'
                  : 'Calculation Failed'}
            </p>
            <p
              className="text-sm mb-4"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {isNoStrategy
                ? 'Create a trading strategy first to see rebalance recommendations'
                : isInvalidStrategy
                  ? 'Your strategy allocations must sum to 100% to calculate a rebalance plan'
                  : 'Unable to calculate rebalance plan. Please try again.'}
            </p>
            <Button
              onClick={() => refetch()}
              className="btn-github btn-github-secondary"
            >
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const plan = response.plan;

  return (
    <div className={`card-github ${className}`}>
      <div
        className="p-4 border-b"
        style={{ borderBottomColor: 'rgb(var(--border))' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3
              className="text-base font-semibold"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              Rebalance Plan
            </h3>
            <p
              className="text-sm mt-1"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              {plan.strategy_name} • Portfolio NAV: $
              {parseFloat(plan.portfolio_nav).toLocaleString()}
            </p>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={refreshPlan.isPending}
            className="btn-github btn-github-secondary text-sm"
          >
            {refreshPlan.isPending ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      <div className="p-6">
        {/* Summary Stats */}
        <div className="mb-6 grid grid-cols-3 gap-4">
          <div
            className="text-center p-3 rounded"
            style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
          >
            <div
              className="text-2xl font-bold"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              {plan.orders_needed}
            </div>
            <div className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              Orders Needed
            </div>
          </div>

          <div
            className="text-center p-3 rounded"
            style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
          >
            <div
              className="text-2xl font-bold"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              ${parseFloat(plan.total_delta).toLocaleString()}
            </div>
            <div className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              Total Delta
            </div>
          </div>

          <div
            className="text-center p-3 rounded"
            style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
          >
            <div
              className={`text-2xl font-bold ${
                plan.rebalance_needed ? 'text-orange-600' : 'text-green-600'
              }`}
            >
              {plan.rebalance_needed ? 'YES' : 'NO'}
            </div>
            <div className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              Rebalance Needed
            </div>
          </div>
        </div>

        {/* Actions Table */}
        {plan.actions.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr
                  className="border-b"
                  style={{ borderBottomColor: 'rgb(var(--border))' }}
                >
                  <th
                    className="text-left py-3 px-2 text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Asset
                  </th>
                  <th
                    className="text-left py-3 px-2 text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Action
                  </th>
                  <th
                    className="text-right py-3 px-2 text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Current
                  </th>
                  <th
                    className="text-right py-3 px-2 text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Target
                  </th>
                  <th
                    className="text-right py-3 px-2 text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Delta
                  </th>
                  <th
                    className="text-right py-3 px-2 text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Order Details
                  </th>
                </tr>
              </thead>
              <tbody>
                {plan.actions.map((action, index) => (
                  <ActionRow
                    key={`${action.asset}-${index}`}
                    action={action}
                    quoteCurrency={plan.quote_currency}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Coming Soon - Execute Button */}
        {plan.rebalance_needed && (
          <div
            className="mt-6 pt-6 border-t"
            style={{ borderTopColor: 'rgb(var(--border))' }}
          >
            <div
              className="p-4 rounded"
              style={{ backgroundColor: 'rgb(var(--color-attention-subtle))' }}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl">💡</span>
                <div>
                  <p
                    className="text-sm font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    Ready to Execute
                  </p>
                  <p
                    className="text-sm mt-1"
                    style={{ color: 'rgb(var(--fg-muted))' }}
                  >
                    {plan.orders_needed} orders will be placed to rebalance your
                    portfolio. Manual execution will be available in Step 4.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* No Action Needed */}
        {!plan.rebalance_needed && (
          <div className="mt-6">
            <div
              className="p-4 rounded text-center"
              style={{ backgroundColor: 'rgb(var(--color-success-subtle))' }}
            >
              <span className="text-2xl mb-2 block">✅</span>
              <p
                className="text-sm font-medium"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                Portfolio is well balanced
              </p>
              <p
                className="text-sm mt-1"
                style={{ color: 'rgb(var(--fg-muted))' }}
              >
                No rebalancing needed at this time
              </p>
            </div>
          </div>
        )}

        {/* Metadata */}
        <div
          className="mt-4 pt-4 border-t"
          style={{ borderTopColor: 'rgb(var(--border))' }}
        >
          <div
            className="flex justify-between text-xs"
            style={{ color: 'rgb(var(--fg-muted))' }}
          >
            <span>Exchange: {plan.exchange_account}</span>
            <span>
              Calculated: {new Date(plan.calculated_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
