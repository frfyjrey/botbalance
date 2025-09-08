import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@shared/ui/Button';
import { Input } from '@shared/ui/Input';
import { Label } from '@shared/ui/Label';
import {
  useStrategy,
  useCreateStrategy,
  useUpdateStrategy,
  usePatchStrategy,
  useDeleteStrategy,
  useStrategyConstants,
  type StrategyFormData,
  type AllocationFormData,
  DEFAULT_STRATEGY_VALUES,
} from '@entities/strategy';
import { useExchangeAccounts } from '@entities/exchange';

interface StrategyFormProps {
  onSuccess?: () => void;
  className?: string;
}

export const StrategyForm: React.FC<StrategyFormProps> = ({
  onSuccess,
  className,
}) => {
  const { t } = useTranslation(['common', 'dashboard']);

  // API hooks
  const { data: strategyResponse, isLoading: isLoadingStrategy } =
    useStrategy();
  const { data: exchangeAccounts, isLoading: isLoadingAccounts } =
    useExchangeAccounts();
  const { data: constants, isLoading: isLoadingConstants } =
    useStrategyConstants();
  const createStrategy = useCreateStrategy();
  const updateStrategy = useUpdateStrategy();
  const patchStrategy = usePatchStrategy();
  const deleteStrategy = useDeleteStrategy();

  // Form state
  const [formData, setFormData] = useState<StrategyFormData>({
    name: DEFAULT_STRATEGY_VALUES.name,
    order_size_pct: DEFAULT_STRATEGY_VALUES.order_size_pct,
    min_delta_pct: DEFAULT_STRATEGY_VALUES.min_delta_pct,
    order_step_pct: DEFAULT_STRATEGY_VALUES.order_step_pct,
    switch_cancel_buffer_pct: DEFAULT_STRATEGY_VALUES.switch_cancel_buffer_pct,
    quote_asset: DEFAULT_STRATEGY_VALUES.quote_asset,
    exchange_account: DEFAULT_STRATEGY_VALUES.exchange_account,
    auto_trade_enabled: DEFAULT_STRATEGY_VALUES.auto_trade_enabled,
    allocations: [
      // Automatically include base currency with default 20%
      {
        asset: DEFAULT_STRATEGY_VALUES.quote_asset,
        target_percentage: 20,
      },
    ],
  });

  const [newAllocation, setNewAllocation] = useState<AllocationFormData>({
    asset: '',
    target_percentage: 0,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Initialize form with existing strategy
  useEffect(() => {
    if (strategyResponse?.strategy) {
      const strategy = strategyResponse.strategy;
      setFormData({
        name: strategy.name,
        order_size_pct: parseFloat(strategy.order_size_pct),
        min_delta_pct: parseFloat(strategy.min_delta_pct || '0.1'),
        order_step_pct: parseFloat(strategy.order_step_pct),
        switch_cancel_buffer_pct: parseFloat(strategy.switch_cancel_buffer_pct),
        quote_asset: strategy.quote_asset,
        exchange_account: strategy.exchange_account,
        auto_trade_enabled: strategy.auto_trade_enabled,
        allocations: strategy.allocations.map(alloc => ({
          asset: alloc.asset,
          target_percentage: parseFloat(alloc.target_percentage),
        })),
      });
    }
  }, [strategyResponse]);

  // Validation
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = t('common:validation.required');
    }

    if (formData.order_size_pct < 0.1 || formData.order_size_pct > 100) {
      newErrors.order_size_pct = t('common:validation.percentage_range', {
        min: 0.1,
        max: 100,
      });
    }

    if (formData.min_delta_pct <= 0 || formData.min_delta_pct > 10) {
      newErrors.min_delta_pct = t('common:validation.percentage_range', {
        min: 0.01,
        max: 10.0,
      });
    }

    if (formData.order_step_pct <= 0 || formData.order_step_pct > 5) {
      newErrors.order_step_pct = t('common:validation.percentage_range', {
        min: 0.01,
        max: 5,
      });
    }

    if (
      formData.switch_cancel_buffer_pct < 0 ||
      formData.switch_cancel_buffer_pct > 1
    ) {
      newErrors.switch_cancel_buffer_pct = t(
        'common:validation.percentage_range',
        {
          min: 0.0,
          max: 1.0,
        },
      );
    }

    // Validate quote asset
    if (!formData.quote_asset) {
      newErrors.quote_asset = 'Base currency is required';
    } else if (
      constants?.constants.quote_assets &&
      !constants.constants.quote_assets.includes(formData.quote_asset)
    ) {
      newErrors.quote_asset = 'Invalid base currency';
    }

    // Validate exchange account (required for new strategies, not when editing)
    if (!isExistingStrategy && !formData.exchange_account) {
      newErrors.exchange_account = 'Exchange account is required';
    }

    // Check if there are active accounts when creating new strategy
    if (!isExistingStrategy && !hasActiveAccounts) {
      newErrors.exchange_account =
        'No active exchange accounts available. Please connect an exchange account first.';
    }

    if (formData.allocations.length === 0) {
      newErrors.allocations = 'At least one asset allocation is required';
    }

    // Validate allocations sum to 100%
    const totalPercentage = formData.allocations.reduce(
      (sum, alloc) => sum + alloc.target_percentage,
      0,
    );

    if (Math.abs(totalPercentage - 100) > 0.1) {
      newErrors.total_allocation = `Allocations must sum to 100%. Current total: ${totalPercentage.toFixed(2)}%`;
    }

    // Check for duplicate assets
    const assets = formData.allocations.map(alloc => alloc.asset);
    const uniqueAssets = new Set(assets);
    if (assets.length !== uniqueAssets.size) {
      newErrors.duplicate_assets =
        'Duplicate assets found. Each asset can only appear once.';
    }

    // Validate base currency allocation (minimum 10%)
    if (formData.quote_asset) {
      const baseCurrencyAllocation = formData.allocations.find(
        alloc =>
          alloc.asset.toUpperCase() === formData.quote_asset.toUpperCase(),
      );

      if (!baseCurrencyAllocation) {
        newErrors.base_currency_missing = `${formData.quote_asset} (base currency) must be included in allocations for cash management.`;
      } else if (baseCurrencyAllocation.target_percentage < 10) {
        newErrors.base_currency_minimum = `${formData.quote_asset} (base currency) must have at least 10% allocation for cash management.`;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form field changes
  const handleFieldChange = (
    field: keyof StrategyFormData,
    value: StrategyFormData[keyof StrategyFormData],
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear field error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  // Handle quote asset change - clear all allocations except new base currency
  const handleQuoteAssetChange = (newQuoteAsset: string) => {
    if (!newQuoteAsset) return;

    setFormData(prev => {
      // Clear all allocations and add only the new base currency with 20%
      const updatedAllocations = [
        {
          asset: newQuoteAsset.toUpperCase(),
          target_percentage: 20,
        },
      ];

      return {
        ...prev,
        quote_asset: newQuoteAsset,
        allocations: updatedAllocations,
      };
    });

    // Clear field error
    if (errors.quote_asset) {
      setErrors(prev => ({ ...prev, quote_asset: '' }));
    }
  };

  // Handle allocation addition
  const handleAddAllocation = () => {
    if (!newAllocation.asset || newAllocation.target_percentage <= 0) {
      return;
    }

    // Check if asset already exists
    if (
      formData.allocations.some(alloc => alloc.asset === newAllocation.asset)
    ) {
      setErrors(prev => ({ ...prev, new_allocation: 'Asset already exists' }));
      return;
    }

    setFormData(prev => ({
      ...prev,
      allocations: [...prev.allocations, { ...newAllocation }],
    }));

    setNewAllocation({ asset: '', target_percentage: 0 });
    setErrors(prev => ({ ...prev, new_allocation: '' }));
  };

  // Handle allocation percentage change without immediate validation
  const handleAllocationPercentageChange = (
    index: number,
    newPercentage: number,
  ) => {
    // Simply update the percentage without immediate validation
    // Validation will happen on form submit
    setFormData(prev => ({
      ...prev,
      allocations: prev.allocations.map((alloc, i) =>
        i === index ? { ...alloc, target_percentage: newPercentage } : alloc,
      ),
    }));
  };

  // Handle allocation removal
  const handleRemoveAllocation = (index: number) => {
    const allocationToRemove = formData.allocations[index];

    // Prevent removal of base currency
    if (
      allocationToRemove &&
      formData.quote_asset &&
      allocationToRemove.asset.toUpperCase() ===
        formData.quote_asset.toUpperCase()
    ) {
      alert(
        `Cannot remove ${formData.quote_asset} - it's the base currency for cash management. Change the base currency first if needed.`,
      );
      return;
    }

    setFormData(prev => ({
      ...prev,
      allocations: prev.allocations.filter((_, i) => i !== index),
    }));
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      // Ensure base currency is always included in allocations
      const allocationsToSend = [...formData.allocations];
      const hasBaseCurrency = allocationsToSend.some(
        alloc =>
          alloc.asset.toUpperCase() === formData.quote_asset.toUpperCase(),
      );

      if (!hasBaseCurrency) {
        // Add base currency with minimum 10% if somehow missing
        allocationsToSend.unshift({
          asset: formData.quote_asset.toUpperCase(),
          target_percentage: Math.max(
            10,
            100 -
              allocationsToSend.reduce(
                (sum, a) => sum + a.target_percentage,
                0,
              ),
          ),
        });
      }

      // Prepare data for API
      const strategyData = {
        name: formData.name,
        order_size_pct: formData.order_size_pct.toString(),
        min_delta_pct: formData.min_delta_pct.toString(),
        order_step_pct: formData.order_step_pct.toString(),
        switch_cancel_buffer_pct: formData.switch_cancel_buffer_pct.toString(),
        quote_asset: formData.quote_asset,
        exchange_account: formData.exchange_account,
        auto_trade_enabled: formData.auto_trade_enabled,
        allocations: allocationsToSend.map(alloc => ({
          asset: alloc.asset.toUpperCase(),
          target_percentage: alloc.target_percentage.toString(),
        })),
      };

      if (strategyResponse?.strategy) {
        // Update existing strategy
        await updateStrategy.mutateAsync(strategyData);
      } else {
        // Create new strategy
        await createStrategy.mutateAsync(strategyData);
      }

      // Clear new allocation field after successful creation
      setNewAllocation({ asset: '', target_percentage: 0 });
      setErrors({});

      onSuccess?.();
    } catch (error) {
      console.error('Failed to save strategy:', error);
      setErrors(prev => ({
        ...prev,
        submit: 'Failed to save strategy. Please try again.',
      }));
    }
  };

  // Handle strategy activation
  const handleToggleActive = async () => {
    if (!strategyResponse?.strategy) return;

    try {
      await patchStrategy.mutateAsync({
        is_active: !strategyResponse.strategy.is_active,
      });
    } catch (error) {
      console.error('Failed to toggle strategy:', error);
    }
  };

  // Handle strategy deletion
  const handleDeleteStrategy = async () => {
    if (!strategyResponse?.strategy) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete the strategy "${strategyResponse.strategy.name}"? This action cannot be undone.`,
    );

    if (!confirmed) return;

    try {
      await deleteStrategy.mutateAsync();
      // Strategy will be removed from cache automatically by the hook
    } catch (error) {
      console.error('Failed to delete strategy:', error);
    }
  };

  const isLoading =
    isLoadingStrategy ||
    isLoadingAccounts ||
    isLoadingConstants ||
    createStrategy.isPending ||
    updateStrategy.isPending ||
    patchStrategy.isPending ||
    deleteStrategy.isPending;
  const isExistingStrategy = !!strategyResponse?.strategy;

  // Filter active exchange accounts
  const activeAccounts = exchangeAccounts?.filter(acc => acc.is_active) || [];
  const hasActiveAccounts = activeAccounts.length > 0;

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
          {isExistingStrategy ? 'Edit Strategy' : 'Create Strategy'}
        </h3>
        <p className="text-sm mt-1" style={{ color: 'rgb(var(--fg-muted))' }}>
          Configure your portfolio target allocations and rebalancing settings
        </p>

        {/* Strategy Info - only show for existing strategies */}
        {isExistingStrategy && strategyResponse?.strategy && (
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span style={{ color: 'rgb(var(--fg-muted))' }}>Status:</span>
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${
                  strategyResponse.strategy.is_active
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {strategyResponse.strategy.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span style={{ color: 'rgb(var(--fg-muted))' }}>Auto Trade:</span>
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${
                  strategyResponse.strategy.auto_trade_enabled
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {strategyResponse.strategy.auto_trade_enabled
                  ? 'Enabled'
                  : 'Disabled'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span style={{ color: 'rgb(var(--fg-muted))' }}>Base Asset:</span>
              <span
                className="font-mono font-medium"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                {strategyResponse.strategy.quote_asset}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span style={{ color: 'rgb(var(--fg-muted))' }}>
                Exchange Account ID:
              </span>
              <span
                className="font-mono"
                style={{ color: 'rgb(var(--fg-default))' }}
              >
                {strategyResponse.strategy.exchange_account}
              </span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* Strategy Name */}
        <div className="space-y-2">
          <Label htmlFor="strategy-name">Strategy Name</Label>
          <Input
            id="strategy-name"
            type="text"
            value={formData.name}
            onChange={e => handleFieldChange('name', e.target.value)}
            placeholder="My Strategy"
            disabled={isLoading}
          />
          {errors.name && <p className="text-sm text-red-600">{errors.name}</p>}
        </div>

        {/* Exchange Account Selection (only for new strategies) */}
        {!isExistingStrategy && (
          <div className="space-y-2">
            <Label htmlFor="exchange-account">Exchange Account *</Label>
            {!hasActiveAccounts ? (
              <div className="p-3 rounded border-2 border-dashed border-orange-300 bg-orange-50">
                <p className="text-sm text-orange-700 mb-2">
                  No active exchange accounts found.
                </p>
                <p className="text-xs text-orange-600">
                  Please connect at least one exchange account before creating a
                  strategy.
                </p>
              </div>
            ) : (
              <select
                id="exchange-account"
                value={formData.exchange_account || ''}
                onChange={e =>
                  handleFieldChange(
                    'exchange_account',
                    parseInt(e.target.value) || null,
                  )
                }
                className="w-full px-3 py-2 border rounded-md text-sm"
                style={{
                  borderColor: 'rgb(var(--border))',
                  backgroundColor: 'rgb(var(--canvas-default))',
                  color: 'rgb(var(--fg-default))',
                }}
                disabled={isLoading}
                required
              >
                <option value="">Select exchange account...</option>
                {activeAccounts.map(account => (
                  <option key={account.id} value={account.id}>
                    {account.name} ({account.exchange.toUpperCase()} -{' '}
                    {account.account_type})
                  </option>
                ))}
              </select>
            )}
            {errors.exchange_account && (
              <p className="text-sm text-red-600">{errors.exchange_account}</p>
            )}
          </div>
        )}

        {/* Base Currency Selection (only for new strategies) */}
        {!isExistingStrategy && (
          <div className="space-y-2">
            <Label htmlFor="quote-asset">Base Currency *</Label>
            <select
              id="quote-asset"
              value={formData.quote_asset}
              onChange={e => handleQuoteAssetChange(e.target.value)}
              className="w-full px-3 py-2 border rounded-md text-sm"
              style={{
                borderColor: 'rgb(var(--border))',
                backgroundColor: 'rgb(var(--canvas-default))',
                color: 'rgb(var(--fg-default))',
              }}
              disabled={isLoading}
              required
            >
              {constants?.constants.quote_assets.map(asset => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              )) || <option value="">Loading...</option>}
            </select>
            <p className="text-xs text-gray-500">
              This currency will be automatically included in your allocations
              for cash management.
            </p>
            {errors.quote_asset && (
              <p className="text-sm text-red-600">{errors.quote_asset}</p>
            )}
          </div>
        )}

        {/* Order Size Percentage */}
        <div className="space-y-2">
          <Label htmlFor="order-size">Order Size (% of NAV)</Label>
          <Input
            id="order-size"
            type="number"
            min="0.1"
            max="100"
            step="0.1"
            value={formData.order_size_pct}
            onChange={e =>
              handleFieldChange(
                'order_size_pct',
                parseFloat(e.target.value) || 0,
              )
            }
            placeholder="10.0"
            disabled={isLoading}
          />
          {errors.order_size_pct && (
            <p className="text-sm text-red-600">{errors.order_size_pct}</p>
          )}
          <p className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            Maximum order size as percentage of total portfolio value
          </p>
        </div>

        {/* Minimum Delta Percentage */}
        <div className="space-y-2">
          <Label htmlFor="min-delta-pct">Minimum Delta (%)</Label>
          <Input
            id="min-delta-pct"
            type="number"
            min="0.01"
            max="10.00"
            step="0.01"
            value={formData.min_delta_pct}
            onChange={e =>
              handleFieldChange(
                'min_delta_pct',
                parseFloat(e.target.value) || 0,
              )
            }
            placeholder="0.10"
            disabled={isLoading}
          />
          {errors.min_delta_pct && (
            <p className="text-sm text-red-600">{errors.min_delta_pct}</p>
          )}
          <p className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            Minimum percentage change of target value (0.1% = 999 → 1001 USDT)
          </p>
        </div>

        {/* Order Step Percentage */}
        <div className="space-y-2">
          <Label htmlFor="order-step">Order Step (%)</Label>
          <Input
            id="order-step"
            type="number"
            min="0.01"
            max="5.00"
            step="0.01"
            value={formData.order_step_pct}
            onChange={e =>
              handleFieldChange(
                'order_step_pct',
                parseFloat(e.target.value) || 0,
              )
            }
            placeholder="0.40"
            disabled={isLoading}
          />
          {errors.order_step_pct && (
            <p className="text-sm text-red-600">{errors.order_step_pct}</p>
          )}
          <p className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            Price step for limit orders (0.40% = buy 0.4% below market, sell
            0.4% above market)
          </p>
        </div>

        {/* Switch Cancel Buffer Percentage */}
        <div className="space-y-2">
          <Label htmlFor="switch-cancel-buffer">
            Cancel buffer (% of price)
          </Label>
          <Input
            id="switch-cancel-buffer"
            type="number"
            min="0.00"
            max="1.00"
            step="0.05"
            value={formData.switch_cancel_buffer_pct}
            onChange={e =>
              handleFieldChange(
                'switch_cancel_buffer_pct',
                parseFloat(e.target.value) || 0,
              )
            }
            placeholder="0.15"
            disabled={isLoading}
          />
          {errors.switch_cancel_buffer_pct && (
            <p className="text-sm text-red-600">
              {errors.switch_cancel_buffer_pct}
            </p>
          )}
          <p className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            Cancel on side change only if market moved by X% from order price
          </p>
        </div>

        {/* Auto Trade Toggle */}
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="auto-trade-enabled"
              checked={formData.auto_trade_enabled}
              onChange={e =>
                handleFieldChange('auto_trade_enabled', e.target.checked)
              }
              className="w-4 h-4 rounded border"
              style={{
                borderColor: 'rgb(var(--border))',
                backgroundColor: 'rgb(var(--canvas-default))',
              }}
              disabled={isLoading}
            />
            <Label htmlFor="auto-trade-enabled" className="font-medium">
              Enable Auto Trading
            </Label>
          </div>
          <p className="text-xs ml-7" style={{ color: 'rgb(var(--fg-muted))' }}>
            When enabled, the strategy will automatically execute rebalancing
            orders every 30 seconds. Requires ENABLE_AUTO_TRADE=true in
            environment settings.
          </p>
          {formData.auto_trade_enabled && (
            <div className="ml-7 p-2 rounded border-l-4 border-orange-400 bg-orange-50">
              <p className="text-xs text-orange-700">
                ⚠️ <strong>Warning:</strong> Auto-trading will place real orders
                on the exchange. Make sure your strategy parameters are correct
                and test thoroughly.
              </p>
            </div>
          )}
        </div>

        {/* Asset Allocations */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Asset Allocations</Label>
            <span className="text-sm" style={{ color: 'rgb(var(--fg-muted))' }}>
              Total:{' '}
              {formData.allocations
                .reduce((sum, alloc) => sum + alloc.target_percentage, 0)
                .toFixed(2)}
              %
            </span>
          </div>

          {/* Existing allocations */}
          {formData.allocations.map((allocation, index) => (
            <div
              key={index}
              className="flex items-center gap-3 p-3 rounded"
              style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
            >
              <span className="font-mono text-sm min-w-16">
                {allocation.asset}
              </span>
              <div className="flex-1">
                <input
                  type="number"
                  min="0.01"
                  max="100"
                  step="0.01"
                  value={allocation.target_percentage || ''}
                  onChange={e =>
                    handleAllocationPercentageChange(
                      index,
                      parseFloat(e.target.value) || 0,
                    )
                  }
                  className="w-20 px-2 py-1 border rounded text-sm"
                  style={{
                    borderColor: 'rgb(var(--border))',
                    backgroundColor: 'rgb(var(--canvas-default))',
                    color: 'rgb(var(--fg-default))',
                  }}
                />
                <span className="text-sm ml-1">%</span>
              </div>
              <Button
                type="button"
                onClick={() => handleRemoveAllocation(index)}
                className="btn-github btn-github-danger text-sm px-2 py-1"
                disabled={isLoading}
              >
                ✕
              </Button>
            </div>
          ))}

          {/* Add new allocation */}
          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-2">
              <Label htmlFor="new-asset">Asset</Label>
              <select
                id="new-asset"
                value={newAllocation.asset}
                onChange={e =>
                  setNewAllocation(prev => ({ ...prev, asset: e.target.value }))
                }
                className="w-full px-3 py-2 border rounded-md bg-white text-sm"
                style={{
                  borderColor: 'rgb(var(--border))',
                  backgroundColor: 'rgb(var(--canvas-default))',
                  color: 'rgb(var(--fg-default))',
                }}
                disabled={isLoading}
              >
                <option value="">Select asset...</option>
                {constants?.constants.allocation_assets.map(asset => (
                  <option key={asset} value={asset}>
                    {asset}
                  </option>
                )) || null}
              </select>
            </div>

            <div className="flex-1 space-y-2">
              <Label htmlFor="new-percentage">Percentage</Label>
              <Input
                id="new-percentage"
                type="number"
                max="100"
                step="0.01"
                value={newAllocation.target_percentage || ''}
                onChange={e =>
                  setNewAllocation(prev => ({
                    ...prev,
                    target_percentage: parseFloat(e.target.value) || 0,
                  }))
                }
                placeholder="0.00"
                disabled={isLoading}
              />
            </div>

            <Button
              type="button"
              onClick={handleAddAllocation}
              className="btn-github btn-github-secondary"
              disabled={
                isLoading ||
                !newAllocation.asset ||
                newAllocation.target_percentage <= 0
              }
            >
              Add
            </Button>
          </div>

          {errors.new_allocation && (
            <p className="text-sm text-red-600">{errors.new_allocation}</p>
          )}

          {errors.allocations && (
            <p className="text-sm text-red-600">{errors.allocations}</p>
          )}

          {errors.total_allocation && (
            <p className="text-sm text-red-600">{errors.total_allocation}</p>
          )}

          {errors.duplicate_assets && (
            <p className="text-sm text-red-600">{errors.duplicate_assets}</p>
          )}

          {errors.base_currency_missing && (
            <p className="text-sm text-red-600">
              {errors.base_currency_missing}
            </p>
          )}

          {errors.base_currency_minimum && (
            <p className="text-sm text-red-600">
              {errors.base_currency_minimum}
            </p>
          )}
        </div>

        {/* Submit Error */}
        {errors.submit && (
          <div
            className="p-3 rounded"
            style={{ backgroundColor: 'rgb(254 226 226)' }}
          >
            <p className="text-sm text-red-600">{errors.submit}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div
          className="flex items-center gap-3 pt-4 border-t"
          style={{ borderTopColor: 'rgb(var(--border))' }}
        >
          <Button
            type="submit"
            className="btn-github btn-github-primary"
            disabled={isLoading}
          >
            {isLoading
              ? 'Saving...'
              : isExistingStrategy
                ? 'Update Strategy'
                : 'Create Strategy'}
          </Button>

          {isExistingStrategy && (
            <>
              <Button
                type="button"
                onClick={handleToggleActive}
                className={`btn-github ${
                  strategyResponse.strategy?.is_active
                    ? 'btn-github-danger'
                    : 'btn-github-secondary'
                }`}
                disabled={patchStrategy.isPending}
              >
                {patchStrategy.isPending
                  ? 'Updating...'
                  : strategyResponse.strategy?.is_active
                    ? 'Deactivate'
                    : 'Activate'}
              </Button>

              <Button
                type="button"
                onClick={handleDeleteStrategy}
                className="btn-github btn-github-danger"
                disabled={deleteStrategy.isPending}
              >
                {deleteStrategy.isPending ? 'Deleting...' : 'Delete Strategy'}
              </Button>
            </>
          )}
        </div>
      </form>
    </div>
  );
};
