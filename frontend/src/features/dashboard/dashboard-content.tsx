import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Button } from '@shared/ui/Button';
import { useUserProfile } from '@entities/user';
import { AppHeader } from '@widgets/layout';
import { BalancesCard } from '@features/balance';
import {
  PortfolioSummaryCard,
  AssetAllocationChart,
  PortfolioAssetsCard,
  PortfolioSnapshots,
} from '@features/portfolio';
import { ExchangeStatusIndicator } from '@features/dashboard';
import { AssetsList } from '@features/portfolio/assets-list';

export const DashboardContent = () => {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const { isLoading: userLoading } = useUserProfile();

  if (userLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>{t('loading_dashboard')}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: 'rgb(var(--canvas-default))' }}
    >
      <AppHeader />

      {/* Main Content - Simple user dashboard */}
      <main className="max-w-7xl mx-auto py-4 sm:py-6 lg:py-8 px-3 sm:px-4 lg:px-8">
        <div className="space-y-4 sm:space-y-6">
          {/* Exchange Status - Circuit Breaker Info */}
          <ExchangeStatusIndicator />

          {/* Portfolio Overview - Step 2 Complete */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            <PortfolioSummaryCard />
            <BalancesCard />
          </div>

          {/* Portfolio Details */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
            <AssetAllocationChart />
            <div className="space-y-4">
              <PortfolioAssetsCard maxItems={10} />
              <AssetsList maxItems={10} />
            </div>
          </div>

          {/* Portfolio Snapshots - Step 2 */}
          <PortfolioSnapshots />

          {/* Step 3 - Trading Strategy */}
          <div className="card-github">
            <div
              className="p-4 border-b"
              style={{ borderBottomColor: 'rgb(var(--border))' }}
            >
              <div className="flex items-center justify-between">
                <h3
                  className="text-base font-semibold"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  Стратегии торговли
                </h3>
                <Button
                  onClick={() => navigate('/strategy')}
                  className="btn-github btn-github-primary text-sm"
                >
                  Настроить
                </Button>
              </div>
            </div>
            <div className="p-4">
              <div className="text-center py-6">
                <div className="mb-4">
                  <svg
                    className="w-12 h-12 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    style={{ color: 'rgb(var(--fg-default))' }}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </div>
                <p
                  className="text-base font-medium mb-2"
                  style={{ color: 'rgb(var(--fg-default))' }}
                >
                  Автоматический ребалансинг
                </p>
                <p
                  className="text-sm"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  Настройте целевые аллокации активов и получите план
                  ребалансировки портфеля
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
