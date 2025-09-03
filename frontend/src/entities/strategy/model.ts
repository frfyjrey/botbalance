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
  min_delta_quote: string;
  order_step_pct: string;
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

export interface RebalancePlanResponse {
  status: string;
  plan?: RebalancePlan;
  message?: string;
  error_code?: string;
}

// Request types for API
export interface StrategyCreateRequest {
  name?: string;
  order_size_pct?: string;
  min_delta_quote?: string;
  order_step_pct?: string;
  allocations: Omit<StrategyAllocation, 'id' | 'created_at' | 'updated_at'>[];
}

export interface StrategyUpdateRequest {
  name?: string;
  order_size_pct?: string;
  min_delta_quote?: string;
  order_step_pct?: string;
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
  min_delta_quote: number;
  order_step_pct: number;
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
  min_delta_quote: 10.0,
  order_step_pct: 0.4,
} as const;

export const SUPPORTED_ASSETS = [
  'BTC',
  'ETH',
  'BNB',
  'ADA',
  'SOL',
  'USDT',
  'USDC',
] as const;

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
