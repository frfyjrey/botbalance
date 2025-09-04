import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@shared/ui/Button';
import { Input } from '@shared/ui/Input';
import { Label } from '@shared/ui/Label';
import {
  useStrategy,
  useCreateStrategy,
  useUpdateStrategy,
  useActivateStrategy,
  type StrategyFormData,
  type AllocationFormData,
  DEFAULT_STRATEGY_VALUES,
  SUPPORTED_ASSETS,
} from '@entities/strategy';

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
  const createStrategy = useCreateStrategy();
  const updateStrategy = useUpdateStrategy();
  const activateStrategy = useActivateStrategy();

  // Form state
  const [formData, setFormData] = useState<StrategyFormData>({
    name: DEFAULT_STRATEGY_VALUES.name,
    order_size_pct: DEFAULT_STRATEGY_VALUES.order_size_pct,
    min_delta_quote: DEFAULT_STRATEGY_VALUES.min_delta_quote,
    order_step_pct: DEFAULT_STRATEGY_VALUES.order_step_pct,
    switch_cancel_buffer_pct: DEFAULT_STRATEGY_VALUES.switch_cancel_buffer_pct,
    allocations: [],
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
        min_delta_quote: parseFloat(strategy.min_delta_quote),
        order_step_pct: parseFloat(strategy.order_step_pct),
        switch_cancel_buffer_pct: parseFloat(strategy.switch_cancel_buffer_pct),
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

    if (formData.order_size_pct <= 0 || formData.order_size_pct > 100) {
      newErrors.order_size_pct = t('common:validation.percentage_range', {
        min: 1,
        max: 100,
      });
    }

    if (formData.min_delta_quote <= 0) {
      newErrors.min_delta_quote = t('common:validation.positive_number');
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

  // Handle allocation removal
  const handleRemoveAllocation = (index: number) => {
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
      // Prepare data for API
      const strategyData = {
        name: formData.name,
        order_size_pct: formData.order_size_pct.toString(),
        min_delta_quote: formData.min_delta_quote.toString(),
        order_step_pct: formData.order_step_pct.toString(),
        switch_cancel_buffer_pct: formData.switch_cancel_buffer_pct.toString(),
        allocations: formData.allocations.map(alloc => ({
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
      await activateStrategy.mutateAsync({
        is_active: !strategyResponse.strategy.is_active,
      });
    } catch (error) {
      console.error('Failed to toggle strategy:', error);
    }
  };

  const isLoading =
    isLoadingStrategy || createStrategy.isPending || updateStrategy.isPending;
  const isExistingStrategy = !!strategyResponse?.strategy;

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

        {/* Order Size Percentage */}
        <div className="space-y-2">
          <Label htmlFor="order-size">Order Size (% of NAV)</Label>
          <Input
            id="order-size"
            type="number"
            min="1"
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

        {/* Minimum Delta */}
        <div className="space-y-2">
          <Label htmlFor="min-delta">Minimum Delta (USDT)</Label>
          <Input
            id="min-delta"
            type="number"
            min="0.01"
            step="0.01"
            value={formData.min_delta_quote}
            onChange={e =>
              handleFieldChange(
                'min_delta_quote',
                parseFloat(e.target.value) || 0,
              )
            }
            placeholder="10.00"
            disabled={isLoading}
          />
          {errors.min_delta_quote && (
            <p className="text-sm text-red-600">{errors.min_delta_quote}</p>
          )}
          <p className="text-xs" style={{ color: 'rgb(var(--fg-muted))' }}>
            Minimum change in USDT required to trigger rebalancing
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
              <span className="flex-1 text-sm">
                {allocation.target_percentage}%
              </span>
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
                {SUPPORTED_ASSETS.map(asset => (
                  <option key={asset} value={asset}>
                    {asset}
                  </option>
                ))}
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
            <Button
              type="button"
              onClick={handleToggleActive}
              className={`btn-github ${
                strategyResponse.strategy?.is_active
                  ? 'btn-github-danger'
                  : 'btn-github-secondary'
              }`}
              disabled={activateStrategy.isPending}
            >
              {activateStrategy.isPending
                ? 'Updating...'
                : strategyResponse.strategy?.is_active
                  ? 'Deactivate'
                  : 'Activate'}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
};
