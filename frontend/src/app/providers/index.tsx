import type { ReactNode } from 'react';
import { QueryProvider } from './query-provider';
import { I18nProvider } from './i18n-provider';

interface AppProvidersProps {
  children: ReactNode;
}

export const AppProviders = ({ children }: AppProvidersProps) => {
  return (
    <I18nProvider>
      <QueryProvider>
        {children}
      </QueryProvider>
    </I18nProvider>
  );
};
