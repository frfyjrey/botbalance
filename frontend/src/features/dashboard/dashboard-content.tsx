import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Button } from '@shared/ui/Button';
import { useUserProfile } from '@entities/user';
import { useExchangeAccounts } from '@entities/exchange';
import { useHasStrategy } from '@entities/strategy';
import {
  usePortfolioData,
  useRefreshPortfolioState,
} from '@entities/portfolio';
import { AppHeader } from '@widgets/layout';
import {
  AssetAllocationChart,
  PortfolioAssetsCard,
  PortfolioSnapshots,
} from '@features/portfolio';

// Простой компонент для onboarding шагов
const OnboardingStep = ({
  title,
  description,
  buttonText,
  onClick,
}: {
  title: string;
  description: string;
  buttonText: string;
  onClick: () => void;
}) => (
  <div className="card-github">
    <div
      className="p-4 border-b"
      style={{ borderBottomColor: 'rgb(var(--border))' }}
    >
      <h3
        className="text-base font-semibold"
        style={{ color: 'rgb(var(--fg-default))' }}
      >
        {title}
      </h3>
    </div>
    <div className="p-6">
      <div className="text-center py-8">
        <div className="mb-4">
          <span className="text-4xl">🚀</span>
        </div>
        <p
          className="text-base font-medium mb-2"
          style={{ color: 'rgb(var(--fg-default))' }}
        >
          {title}
        </p>
        <p className="text-sm mb-6" style={{ color: 'rgb(var(--fg-muted))' }}>
          {description}
        </p>
        <Button
          onClick={onClick}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md"
        >
          {buttonText}
        </Button>
      </div>
    </div>
  </div>
);

export const DashboardContent = () => {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const { isLoading: userLoading } = useUserProfile();

  // Onboarding hooks
  const { data: exchangeAccounts, isLoading: exchangesLoading } =
    useExchangeAccounts();
  const hasStrategy = useHasStrategy();
  const { data: portfolioData, isLoading: portfolioLoading } =
    usePortfolioData();
  const refreshPortfolioState = useRefreshPortfolioState();

  // Loading state
  if (userLoading || exchangesLoading || portfolioLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>{t('loading_dashboard')}</p>
        </div>
      </div>
    );
  }

  // Onboarding gating
  const hasExchangeAccount = exchangeAccounts && exchangeAccounts.length > 0;
  const hasPortfolioState = portfolioData && portfolioData.status === 'success';

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: 'rgb(var(--canvas-default))' }}
    >
      <AppHeader />

      <main className="max-w-7xl mx-auto py-4 sm:py-6 lg:py-8 px-3 sm:px-4 lg:px-8">
        {/* Шаг 1: Нет коннектора */}
        {!hasExchangeAccount && (
          <OnboardingStep
            title="Подключите биржу"
            description="Подключите биржу, чтобы продолжить настройку торгового бота"
            buttonText="Connect Exchange"
            onClick={() => navigate('/exchanges')}
          />
        )}

        {/* Шаг 2: Есть коннектор, но нет активной стратегии */}
        {hasExchangeAccount && !hasStrategy && (
          <OnboardingStep
            title="Создайте стратегию"
            description="Создайте стратегию (после сохранения она остается на паузе)"
            buttonText="Create Strategy"
            onClick={() => navigate('/strategy')}
          />
        )}

        {/* Шаг 3: Есть стратегия, но нет Portfolio State */}
        {hasExchangeAccount && hasStrategy && !hasPortfolioState && (
          <OnboardingStep
            title="Создайте первый снимок портфеля"
            description="Создайте первый снимок портфеля для начала работы"
            buttonText="Create Portfolio State"
            onClick={() => refreshPortfolioState.mutate({})}
          />
        )}

        {/* Обычный dashboard - когда все готово */}
        {hasExchangeAccount && hasStrategy && hasPortfolioState && (
          <div className="space-y-4 sm:space-y-6">
            {/* Portfolio Details */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
              <AssetAllocationChart />
              <PortfolioAssetsCard maxItems={10} />
            </div>

            {/* Portfolio Snapshots */}
            <PortfolioSnapshots />

            {/* Trading Strategy */}
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
        )}
      </main>
    </div>
  );
};
