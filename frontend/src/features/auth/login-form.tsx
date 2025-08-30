import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@shared/ui/Button';
import { Input } from '@shared/ui/Input';
import { Label } from '@shared/ui/Label';
// Removed Card components - using GitHub-style design directly
import { useLogin } from '@entities/user';
import { cn } from '@shared/lib/utils';
import type { LoginRequest } from '@shared/config/types';

interface LoginFormProps {
  onSuccess?: () => void;
  className?: string;
}

export const LoginForm = ({ onSuccess, className }: LoginFormProps) => {
  const { t } = useTranslation('auth');
  const [formData, setFormData] = useState<LoginRequest>({
    username: '',
    password: '',
  });

  const login = useLogin();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await login.mutateAsync(formData);
      if (response.status === 'success') {
        onSuccess?.();
      }
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const isLoading = login.isPending;

  return (
    <div
      className={cn('flex items-center justify-center min-h-screen', className)}
      style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
    >
      <div className="w-full max-w-sm">
        {/* GitHub-style logo/title area */}
        <div className="text-center mb-6">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
            style={{ backgroundColor: 'rgb(var(--fg-default))' }}
          >
            <span
              className="text-2xl font-bold"
              style={{ color: 'rgb(var(--fg-onEmphasis))' }}
            >
              B
            </span>
          </div>
          <h1
            className="text-2xl font-normal"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            {t('login.title')}
          </h1>
        </div>

        {/* GitHub-style form card */}
        <div className="card-github p-6">
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              {login.error && (
                <div
                  className="px-3 py-2 rounded-md text-sm border"
                  style={{
                    backgroundColor: 'rgb(var(--alert-error-bg))',
                    borderColor: 'rgb(var(--alert-error-border))',
                    color: 'rgb(var(--fg-default))',
                  }}
                >
                  {login.error &&
                  typeof login.error === 'object' &&
                  'message' in login.error
                    ? (login.error as { message: string }).message
                    : t('authentication_failed')}
                </div>
              )}

              <div className="space-y-1">
                <Label
                  htmlFor="username"
                  className="block text-sm font-medium"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  {t('login.username')}
                </Label>
                <Input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  placeholder={t('login.username_placeholder')}
                  className="input-github"
                />
              </div>

              <div className="space-y-1">
                <Label
                  htmlFor="password"
                  className="block text-sm font-medium"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  {t('login.password')}
                </Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  placeholder={t('login.password_placeholder')}
                  className="input-github"
                />
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="btn-github btn-github-primary w-full py-2.5 mt-4"
              >
                {isLoading ? t('login.signing_in') : t('login.sign_in')}
              </Button>
            </div>
          </form>

          {/* Demo credentials */}
          <div
            className="mt-6 pt-4"
            style={{ borderTop: '1px solid rgb(var(--border))' }}
          >
            <div
              className="text-xs text-center space-y-1"
              style={{ color: 'rgb(var(--fg-muted))' }}
            >
              <p className="font-medium">{t('login.demo_credentials')}</p>
              <div
                className="p-2 rounded text-left font-mono"
                style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
              >
                <div>
                  <strong>{t('login.demo_username')}</strong> {t('login.admin')}
                </div>
                <div>
                  <strong>{t('login.demo_password')}</strong>{' '}
                  {t('login.admin123')}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
