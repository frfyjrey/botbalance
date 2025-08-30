/**
 * Main Application Component
 * 
 * Features:
 * - FSD-lite Architecture
 * - React Router with protected routes
 * - TanStack Query for server state
 * - Zustand for client state
 * - i18n internationalization
 * - Tailwind CSS + shadcn/ui components
 */

import { AppProviders } from './providers';
import { AppRouterProvider } from './providers/router-provider';

function App() {
  return (
    <AppProviders>
      <AppRouterProvider />
    </AppProviders>
  );
}

export default App;
