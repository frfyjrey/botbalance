import { Card, CardContent, CardHeader, CardTitle } from '@shared/ui/Card';
import { usePortfolioData } from '@entities/portfolio';
import { Badge } from '@shared/ui/badge';
import clsx from 'clsx';

// SVG Icon Components
const CheckCircle = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

const AlertTriangle = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.502 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"
    />
  </svg>
);

const Clock = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

const AlertCircle = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

export function ExchangeStatusIndicator() {
  const { data: portfolioData, isLoading, error } = usePortfolioData();

  if (isLoading) {
    return (
      <Card className="border-gray-200">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <div className="animate-pulse w-4 h-4 bg-gray-300 rounded-full" />
            <span className="text-sm text-gray-500">
              Проверяем статус биржи...
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const exchangeStatus = portfolioData?.exchange_status;
  const circuitBreaker =
    exchangeStatus?.circuit_breaker_status?.circuit_breaker;

  // Determine status
  let status: 'healthy' | 'degraded' | 'down' | 'error' = 'healthy';
  let statusText = 'Работает';
  let bgColor = 'bg-green-50';
  let borderColor = 'border-green-200';
  let Icon = CheckCircle;

  if (error) {
    status = 'error';
    statusText = 'Ошибка';
    bgColor = 'bg-red-50';
    borderColor = 'border-red-200';
    Icon = AlertCircle;
  } else if (
    exchangeStatus?.using_fallback_data ||
    !exchangeStatus?.is_available
  ) {
    // If using fallback data OR exchange marked as unavailable = problems
    if (circuitBreaker?.is_open) {
      status = 'down';
      statusText = 'Недоступна';
      bgColor = 'bg-red-50';
      borderColor = 'border-red-200';
      Icon = AlertTriangle;
    } else {
      status = 'degraded';
      statusText = 'Проблемы';
      bgColor = 'bg-amber-50';
      borderColor = 'border-amber-200';
      Icon = Clock;
    }
  }

  // Get exchange info from exchange_account (primary) or circuit_breaker_status (fallback)
  const exchangeAccount = portfolioData?.exchange_account;
  const circuitBreakerInfo = exchangeStatus?.circuit_breaker_status;

  const exchangeName = exchangeAccount
    ? `${exchangeAccount.exchange.toUpperCase()}${exchangeAccount.testnet ? ' testnet' : ' mainnet'}`
    : circuitBreakerInfo
      ? `${circuitBreakerInfo.exchange.toUpperCase()}${circuitBreakerInfo.testnet ? ' testnet' : ' mainnet'}`
      : 'Биржа (неизвестна)';

  // Show account name and type
  const accountName = exchangeAccount?.name || 'Неизвестный аккаунт';
  const accountType =
    exchangeAccount?.account_type || circuitBreakerInfo?.account_type || '';
  const accountDetails = accountType ? `(${accountType})` : '';

  return (
    <Card className={clsx('transition-all duration-200', borderColor, bgColor)}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-sm font-medium">
          <span className="text-gray-700">Статус биржи</span>
          <Badge
            variant="outline"
            className={clsx(
              'px-2 py-1',
              status === 'healthy' &&
                'border-green-200 text-green-700 bg-green-50',
              status === 'degraded' &&
                'border-amber-200 text-amber-700 bg-amber-50',
              status === 'down' && 'border-red-200 text-red-700 bg-red-50',
              status === 'error' && 'border-red-200 text-red-700 bg-red-50',
            )}
          >
            <Icon className="w-3 h-3 mr-1" />
            {statusText}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-0 space-y-3">
        {/* Exchange Name */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Подключение:</span>
            <span className="text-sm font-medium text-gray-900">
              {accountName}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Биржа:</span>
            <span className="text-xs text-gray-700">
              {exchangeName} {accountDetails}
            </span>
          </div>
        </div>

        {/* Circuit Breaker Info */}
        {circuitBreaker && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Неудачных попыток:</span>
              <span
                className={clsx(
                  'text-sm font-medium',
                  circuitBreaker.failure_count >=
                    circuitBreaker.failure_threshold
                    ? 'text-red-600'
                    : 'text-gray-900',
                )}
              >
                {Math.min(
                  circuitBreaker.failure_count,
                  circuitBreaker.failure_threshold,
                )}
                /{circuitBreaker.failure_threshold}
              </span>
            </div>

            {circuitBreaker.is_open && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Повтор через:</span>
                <span className="text-sm font-medium text-amber-600">
                  {Math.floor(circuitBreaker.time_until_retry_seconds / 60)} мин
                </span>
              </div>
            )}
          </>
        )}

        {/* Fallback Data Info */}
        {exchangeStatus?.using_fallback_data &&
          exchangeStatus.fallback_age_minutes && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Возраст данных:</span>
              <span className="text-sm font-medium text-amber-600">
                {exchangeStatus.fallback_age_minutes < 60
                  ? `${exchangeStatus.fallback_age_minutes} мин`
                  : `${Math.floor(exchangeStatus.fallback_age_minutes / 60)} ч ${exchangeStatus.fallback_age_minutes % 60} мин`}
              </span>
            </div>
          )}

        {/* Status Message */}
        {status !== 'healthy' && (
          <div
            className={clsx(
              'text-xs p-2 rounded',
              status === 'down' && 'bg-red-100 text-red-700',
              status === 'degraded' && 'bg-amber-100 text-amber-700',
              status === 'error' && 'bg-red-100 text-red-700',
            )}
          >
            {status === 'down' &&
              `🔴 Circuit breaker активен. Система временно не обращается к ${exchangeName} для снижения нагрузки.`}
            {status === 'degraded' &&
              `🟡 Обнаружены проблемы с ${exchangeName}. Показаны последние доступные данные.`}
            {status === 'error' && '🔴 Ошибка получения статуса биржи.'}
          </div>
        )}

        {/* Healthy Status */}
        {status === 'healthy' && (
          <div className="text-xs p-2 rounded bg-green-100 text-green-700">
            ✅ Все системы работают нормально
          </div>
        )}
      </CardContent>
    </Card>
  );
}
