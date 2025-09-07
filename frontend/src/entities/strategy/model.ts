/**
 * Strategy domain models for Step 3: Target Allocation
 */

export interface StrategyAllocation {
  id?: number;
  asset: string;
  target_percentage: string;
  created_at?: string;
  updated_at?: string;
}

export interface Strategy {
  id: number;
  name: string;
  order_size_pct: string;
  min_delta_pct: string;
  order_step_pct: string;
  switch_cancel_buffer_pct: string;
  quote_asset: string;
  exchange_account: number;
  is_active: boolean;
  allocations: StrategyAllocation[];
  total_allocation: string;
  is_allocation_valid: boolean;
  created_at: string;
  updated_at: string;
  last_rebalanced_at: string | null;
}

export interface RebalanceAction {
  asset: string;
  action: 'buy' | 'sell' | 'hold';
  current_percentage: string;
  target_percentage: string;
  current_value: string;
  target_value: string;
  delta_value: string;
  order_amount: string | null;
  order_volume: string | null;
  order_price: string | null;
  market_price: string | null;
  normalized_order_volume?: string | null;
  normalized_order_price?: string | null;
  order_amount_normalized?: string | null;
}

export interface RebalancePlan {
  strategy_id: number;
  strategy_name: string;
  portfolio_nav: string;
  quote_currency: string;
  actions: RebalanceAction[];
  total_delta: string;
  orders_needed: number;
  rebalance_needed: boolean;
  calculated_at: string;
  exchange_account: string;
}

// API Response types
export interface StrategyResponse {
  status: string;
  strategy?: Strategy;
  message?: string;
  error_code?: string;
  errors?: Record<string, string[]>;
}

export interface StrategyDeleteResponse {
  status: 'success' | 'error';
  message: string;
  error_code?: string;
}

export interface StrategyConstantsResponse {
  status: 'success';
  constants: {
    quote_assets: string[];
    allocation_assets: string[];
  };
}

export interface RebalancePlanResponse {
  status: string;
  plan?: RebalancePlan;
  message?: string;
  error_code?: string;
}

export interface RebalanceExecuteRequest {
  force_refresh_prices?: boolean;
}

export interface RebalanceOrder {
  id: number;
  exchange_order_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  status: string;
  limit_price: string;
  quote_amount: string;
  created_at: string;
}

export interface RebalanceExecuteResponse {
  status: 'success' | 'error';
  message: string;
  execution_id?: number;
  orders_created?: number;
  total_delta?: string;
  nav?: string;
  orders?: RebalanceOrder[];
  error_code?: string;
}

// Request types for API
export interface StrategyCreateRequest {
  name?: string;
  order_size_pct?: string;
  min_delta_pct?: string;
  order_step_pct?: string;
  switch_cancel_buffer_pct?: string;
  quote_asset?: string;
  exchange_account?: number | null;
  allocations: Omit<StrategyAllocation, 'id' | 'created_at' | 'updated_at'>[];
}

export interface StrategyUpdateRequest {
  name?: string;
  order_size_pct?: string;
  min_delta_pct?: string;
  order_step_pct?: string;
  switch_cancel_buffer_pct?: string;
  quote_asset?: string;
  exchange_account?: number | null;
  is_active?: boolean;
  allocations?: Omit<StrategyAllocation, 'id' | 'created_at' | 'updated_at'>[];
}

export interface StrategyActivateRequest {
  is_active: boolean;
}

// Form types for components
export interface StrategyFormData {
  name: string;
  order_size_pct: number;
  min_delta_pct: number;
  order_step_pct: number;
  switch_cancel_buffer_pct: number;
  quote_asset: string;
  exchange_account: number | null;
  allocations: {
    asset: string;
    target_percentage: number;
  }[];
}

export interface AllocationFormData {
  asset: string;
  target_percentage: number;
}

// Validation types
export interface StrategyValidation {
  missing_assets: string[];
  extra_assets: string[];
  warnings: string[];
}

export interface StrategyValidationResponse {
  status: string;
  validation?: StrategyValidation;
  strategy_valid?: boolean;
  portfolio_nav?: string;
  current_assets?: string[];
  message?: string;
  error_code?: string;
}

// Utility types
export type ActionType = RebalanceAction['action'];
export type StrategyStatus = 'active' | 'inactive';

// Constants
export const DEFAULT_STRATEGY_VALUES = {
  name: 'My Strategy',
  order_size_pct: 10.0,
  min_delta_pct: 0.1,
  order_step_pct: 0.4,
  switch_cancel_buffer_pct: 0.15,
  quote_asset: 'USDT',
  exchange_account: null,
} as const;

// Note: Asset constants are now loaded from the backend via useStrategyConstants()
// This ensures the frontend and backend stay in sync and prevents security bypasses

export const ACTION_COLORS = {
  buy: '#10b981', // green-500
  sell: '#ef4444', // red-500
  hold: '#6b7280', // gray-500
} as const;

export const ACTION_LABELS = {
  buy: 'Buy',
  sell: 'Sell',
  hold: 'Hold',
} as const;
