/**
 * Global application types
 */

// API Response types
export interface ApiResponse<T = unknown> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  errors?: Record<string, string[]>;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  date_joined: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  status: 'success' | 'error';
  message: string;
  user?: User;
  tokens?: {
    access: string;
    refresh: string;
  };
  errors?: Record<string, string[]>;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  database: {
    status: string;
    connection: boolean;
  };
  redis: {
    status: string;
    connection: boolean;
  };
  celery: {
    status: string;
    workers: number;
    message?: string;
    active_workers?: string[];
  };
}

export interface VersionResponse {
  name: string;
  version: string;
  description: string;
  docs: string;
  health: string;
  environment: string;
  timestamp: string;
}

export interface TaskResponse {
  status: 'success' | 'error';
  message: string;
  task_id?: string;
  task_url?: string;
}

export interface TaskStatusResponse {
  status: 'success' | 'error';
  task?: {
    task_id: string;
    state: string;
    result: unknown;
    info: unknown;
    traceback: string | null;
    successful: boolean | null;
    ready: boolean;
    progress?: {
      current: number;
      total: number;
      percentage: number;
      status: string;
    };
  };
}

export interface ApiError {
  message: string;
  status?: number;
  errors?: Record<string, string[]>;
}

// UI State types
export interface AppState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
}

export interface ThemeState {
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export interface UiState {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
}

export interface AuthState {
  isAuthenticated: boolean;
  setIsAuthenticated: (authenticated: boolean) => void;
}

// Form types
export type FormErrors<T = Record<string, unknown>> = {
  [K in keyof T]?: string[];
};

export interface FormState<T = Record<string, unknown>> {
  data: T;
  errors: FormErrors<T>;
  isSubmitting: boolean;
  isValid: boolean;
}

// Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequireOnly<T, K extends keyof T> = Pick<T, K> &
  Partial<Omit<T, K>>;
export type Prettify<T> = { [K in keyof T]: T[K] } & {};

// Component prop types
export interface BaseProps {
  className?: string;
  children?: React.ReactNode;
}

export interface WithLoading {
  loading?: boolean;
}

export interface WithError {
  error?: string | null;
}

export interface WithDisabled {
  disabled?: boolean;
}
