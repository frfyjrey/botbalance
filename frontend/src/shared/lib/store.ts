import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { UiState, ThemeState, AuthState } from '@shared/config/types';
import { STORAGE_KEYS } from '@shared/config/constants';
import { tokenManager } from '@shared/lib/api';

// UI Store for transient UI state
export const useUiStore = create<UiState>()(
  devtools(
    set => ({
      sidebarOpen: false,
      setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
      mobileMenuOpen: false,
      setMobileMenuOpen: (open: boolean) => set({ mobileMenuOpen: open }),
    }),
    {
      name: 'ui-store',
    },
  ),
);

// Theme Store with localStorage persistence
export const useThemeStore = create<ThemeState>()(
  devtools(
    set => ({
      theme:
        (localStorage.getItem(STORAGE_KEYS.THEME) as
          | 'light'
          | 'dark'
          | 'system') || 'system',
      setTheme: (theme: 'light' | 'dark' | 'system') => {
        localStorage.setItem(STORAGE_KEYS.THEME, theme);
        set({ theme });

        // Apply theme to document
        const root = window.document.documentElement;
        root.classList.remove('light', 'dark');

        if (theme === 'system') {
          const systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
            .matches
            ? 'dark'
            : 'light';
          root.classList.add(systemTheme);
        } else {
          root.classList.add(theme);
        }
      },
    }),
    {
      name: 'theme-store',
    },
  ),
);

// Initialize theme on load
const initializeTheme = () => {
  const { theme, setTheme } = useThemeStore.getState();
  setTheme(theme); // This will apply the theme to the document
};

// Auth Store for reactive authentication state
export const useAuthStore = create<AuthState>()(
  devtools(
    set => ({
      isAuthenticated: tokenManager.isAuthenticated(),
      setIsAuthenticated: (authenticated: boolean) =>
        set({ isAuthenticated: authenticated }),
    }),
    {
      name: 'auth-store',
    },
  ),
);

// Call initialization
if (typeof window !== 'undefined') {
  initializeTheme();

  // Listen for system theme changes
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => {
      const { theme, setTheme } = useThemeStore.getState();
      if (theme === 'system') {
        setTheme('system'); // Re-apply system theme
      }
    });

  // Listen for auth events to update auth store
  window.addEventListener('auth:login', () => {
    useAuthStore.getState().setIsAuthenticated(true);
  });

  window.addEventListener('auth:logout', () => {
    useAuthStore.getState().setIsAuthenticated(false);
  });
}
