import { Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

import { AppHeader } from '@widgets/layout';
import { StrategyForm, RebalancePlan } from '@features/strategy';

const ErrorFallback = ({
  error,
  resetErrorBoundary,
}: {
  error: Error;
  resetErrorBoundary: () => void;
}) => {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-red-600 mb-2">
          Something went wrong
        </h2>
        <p className="text-gray-600 mb-4">
          {error?.message || 'Failed to load'}
        </p>
        <button
          onClick={resetErrorBoundary}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Try again
        </button>
      </div>
    </div>
  );
};

const LoadingFallback = () => {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p>Loading...</p>
      </div>
    </div>
  );
};

const StrategyPage = () => {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <div
        className="min-h-screen"
        style={{ backgroundColor: 'rgb(var(--canvas-default))' }}
      >
        <AppHeader />

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-4 sm:py-6 lg:py-8 px-3 sm:px-4 lg:px-8">
          {/* Strategy Form and Plan */}
          <div className="space-y-6 sm:space-y-8">
            <Suspense fallback={<LoadingFallback />}>
              <StrategyForm />
            </Suspense>

            <Suspense fallback={<LoadingFallback />}>
              <RebalancePlan />
            </Suspense>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
};

export default StrategyPage;
