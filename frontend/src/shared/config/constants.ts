/**
 * Application constants
 */

// API Configuration
export const API_BASE =
  import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Storage Keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'boilerplate_access_token',
  REFRESH_TOKEN: 'boilerplate_refresh_token',
  LANGUAGE: 'boilerplate_language',
  THEME: 'boilerplate_theme',
} as const;

// Application Routes
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  STRATEGY: '/strategy',
  ADMIN_DASHBOARD: '/admin-dashboard',
  PROFILE: '/profile',
  TASKS: '/tasks',
} as const;

// API Endpoints
export const API_ENDPOINTS = {
  // Auth
  LOGIN: '/api/auth/login/',
  PROFILE: '/api/auth/profile/',

  // System
  HEALTH: '/api/health/',
  VERSION: '/api/version/',

  // Tasks
  TASKS_ECHO: '/api/tasks/echo/',
  TASKS_HEARTBEAT: '/api/tasks/heartbeat/',
  TASKS_STATUS: '/api/tasks/status/',
} as const;

// Query Keys for TanStack Query
export const QUERY_KEYS = {
  USER: 'user',
  HEALTH: 'health',
  VERSION: 'version',
  TASKS: 'tasks',
  TASK_STATUS: 'task-status',
  BALANCES: 'balances',
  PORTFOLIO_SUMMARY: 'portfolio-summary',
  STRATEGY: 'strategy',
  REBALANCE_PLAN: 'rebalance-plan',
} as const;

// Theme
export const THEME = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
} as const;

// Languages
export const LANGUAGES = {
  EN: 'en',
  RU: 'ru',
} as const;

// Task States
export const TASK_STATES = {
  PENDING: 'PENDING',
  STARTED: 'STARTED',
  SUCCESS: 'SUCCESS',
  FAILURE: 'FAILURE',
  RETRY: 'RETRY',
  REVOKED: 'REVOKED',
} as const;

// HTTP Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
} as const;

// Environment
export const ENV = {
  DEVELOPMENT: 'development',
  PRODUCTION: 'production',
  TEST: 'test',
} as const;

export const IS_DEV = import.meta.env.DEV;
export const IS_PROD = import.meta.env.PROD;
