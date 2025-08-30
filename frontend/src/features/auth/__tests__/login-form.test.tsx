import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoginForm } from '../login-form';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock API
vi.mock('@shared/lib/api', () => ({
  apiClient: {
    login: vi.fn(),
  },
  tokenManager: {
    isAuthenticated: vi.fn(() => false),
    getAccessToken: vi.fn(() => null),
    setTokens: vi.fn(),
    clearTokens: vi.fn(),
  },
}));

describe('LoginForm', () => {
  const createWrapper = () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  it('renders login form', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    expect(screen.getByText('login.title')).toBeInTheDocument();
    expect(screen.getByLabelText('login.username')).toBeInTheDocument();
    expect(screen.getByLabelText('login.password')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'login.sign_in' }),
    ).toBeInTheDocument();
  });

  it('allows user to input credentials', async () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    const usernameInput = screen.getByLabelText(
      'login.username',
    ) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(
      'login.password',
    ) as HTMLInputElement;

    fireEvent.change(usernameInput, { target: { value: 'admin' } });
    fireEvent.change(passwordInput, { target: { value: 'password' } });

    expect(usernameInput.value).toBe('admin');
    expect(passwordInput.value).toBe('password');
  });

  it('shows demo credentials', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    expect(screen.getByText('login.demo_credentials')).toBeInTheDocument();
    expect(screen.getByText('login.admin')).toBeInTheDocument();
    expect(screen.getByText('login.admin123')).toBeInTheDocument();
  });
});
