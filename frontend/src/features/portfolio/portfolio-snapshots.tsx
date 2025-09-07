import { useState, useEffect, useMemo } from 'react';
import { Button } from '@shared/ui/Button';
import { apiClient } from '@shared/lib/api';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

interface Snapshot {
  id: number;
  ts: string;
  nav_quote: string;
  quote_asset: string;
  asset_count: number;
  source: string;
  exchange_account: string | null;
  created_at: string;
}

export const PortfolioSnapshots = () => {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-fetch snapshots on component mount
  useEffect(() => {
    fetchSnapshots();
  }, []);

  const fetchSnapshots = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getPortfolioSnapshots({ limit: 100 });
      if (response.status === 'success') {
        setSnapshots((response.snapshots as Snapshot[]) || []);
      } else {
        setError(response.message || 'Failed to fetch snapshots');
      }
    } catch (err) {
      setError('Error fetching snapshots');
      console.error('Error fetching snapshots:', err);
    } finally {
      setLoading(false);
    }
  };

  const createSnapshot = async (force = false) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.createPortfolioSnapshot(force);
      if (response.status === 'success') {
        await fetchSnapshots(); // Refresh list
      } else if (response.status === 'throttled') {
        setError(
          '⏳ Throttled: Max 1 snapshot per minute. Wait 60 seconds or click "Force Create".',
        );
      } else {
        setError(response.message || 'Failed to create snapshot');
      }
    } catch (err) {
      setError('Error creating snapshot');
      console.error('Error creating snapshot:', err);
    } finally {
      setLoading(false);
    }
  };

  const deleteAllSnapshots = async () => {
    if (!confirm('Delete ALL snapshots? This cannot be undone!')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.deleteAllPortfolioSnapshots();
      if (response.status === 'success') {
        setSnapshots([]);
        alert(`Deleted ${response.deleted_count} snapshots`);
      } else {
        setError(response.message || 'Failed to delete snapshots');
      }
    } catch (err) {
      setError('Error deleting snapshots');
      console.error('Error deleting snapshots:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString();
    } catch {
      return 'Invalid Date';
    }
  };

  const formatValue = (value: string, currency: string) => {
    return `${parseFloat(value).toFixed(2)} ${currency}`;
  };

  // Данные для графика: все доступные снепшоты, ось X = numeric timestamp (time scale)
  const chartData = useMemo(() => {
    if (!snapshots.length) return [];

    const data = snapshots.map(s => {
      const ts = new Date(s.ts).getTime();
      return {
        timestamp: ts,
        nav: Number(s.nav_quote),
        time: new Date(ts).toLocaleString('ru-RU'),
        id: s.id,
      };
    });

    // Сортировка по возрастанию времени для корректного рисования линии слева направо
    data.sort((a, b) => a.timestamp - b.timestamp);
    return data;
  }, [snapshots]);

  // Простой tooltip
  const renderTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ payload: { nav: number; time: string; id: number } }>;
  }) => {
    if (!active || !payload?.[0]) return null;

    const data = payload[0].payload;
    return (
      <div className="bg-gray-800 text-white px-3 py-2 rounded shadow">
        <p className="font-semibold">${data.nav.toFixed(2)} USDT</p>
        <p className="text-sm text-gray-300">{data.time}</p>
        <p className="text-xs text-gray-400">ID: {data.id}</p>
      </div>
    );
  };

  return (
    <div
      className="card-github p-6"
      style={{ backgroundColor: 'rgb(var(--canvas-subtle))' }}
    >
      <div className="flex justify-between items-center mb-4">
        <h3
          className="text-lg font-semibold"
          style={{ color: 'rgb(var(--fg-default))' }}
        >
          Portfolio Snapshots
        </h3>
        <div className="flex gap-2">
          <Button
            onClick={fetchSnapshots}
            disabled={loading}
            size="sm"
            variant="outline"
            className="hover:bg-gray-50 hover:border-gray-400 transition-colors duration-200"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
          <Button
            onClick={() => createSnapshot(false)}
            disabled={loading}
            size="sm"
            className="bg-blue-600 text-white hover:bg-blue-700 transition-colors duration-200 border-blue-600"
          >
            Create Snapshot
          </Button>
          <Button
            onClick={() => createSnapshot(true)}
            disabled={loading}
            size="sm"
            variant="outline"
            className="border-orange-300 text-orange-600 hover:bg-orange-50 hover:border-orange-400 transition-colors duration-200"
          >
            Force Create
          </Button>
          <Button
            onClick={deleteAllSnapshots}
            disabled={loading}
            size="sm"
            variant="destructive"
            className="hover:bg-red-600 transition-colors duration-200"
          >
            Delete All
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded border border-red-300 bg-red-50 text-red-700">
          {error}
        </div>
      )}

      {/* Beautiful NAV Chart with Recharts */}
      {snapshots.length > 0 && (
        <div className="mb-6">
          <div className="flex justify-between items-center mb-3">
            <h4
              className="text-md font-medium"
              style={{ color: 'rgb(var(--fg-default))' }}
            >
              📈 NAV History
            </h4>
            <div className="text-sm text-gray-500">
              💰 Current:{' '}
              <span className="font-semibold text-green-600">
                $
                {snapshots.length > 0
                  ? parseFloat(snapshots[0].nav_quote).toFixed(0)
                  : '0'}
              </span>
            </div>
          </div>

          <div className="h-64 bg-gradient-to-b from-blue-50 to-white p-4 rounded-lg border border-blue-200">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <defs>
                  <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis
                  dataKey="timestamp"
                  type="number"
                  scale="time"
                  domain={['auto', 'auto']}
                  tickFormatter={value =>
                    new Date(value).toLocaleTimeString('ru-RU', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  }
                  tick={{ fontSize: 12, fill: '#6B7280' }}
                  axisLine={{ stroke: '#D1D5DB' }}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#6B7280' }}
                  axisLine={{ stroke: '#D1D5DB' }}
                  tickFormatter={value => `$${value.toFixed(0)}`}
                />
                <Tooltip content={renderTooltip} />
                <Area
                  type="monotone"
                  dataKey="nav"
                  stroke="#3B82F6"
                  strokeWidth={3}
                  fill="url(#navGradient)"
                  dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
                  activeDot={{
                    r: 6,
                    fill: '#1D4ED8',
                    stroke: '#fff',
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-2 text-xs text-gray-500 text-center">
            Last {Math.min(chartData.length, 12)} snapshots • Hover for details
          </div>
        </div>
      )}

      {/* Snapshots List */}
      <div>
        <h4
          className="text-md font-medium mb-3"
          style={{ color: 'rgb(var(--fg-default))' }}
        >
          Recent Snapshots ({snapshots.length})
        </h4>

        {snapshots.length === 0 ? (
          <p
            className="text-center py-8"
            style={{ color: 'rgb(var(--fg-muted))' }}
          >
            No snapshots yet. Click "Create Snapshot" to create your first one.
          </p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {snapshots.map((snapshot, index) => (
              <div
                key={snapshot.id || `snapshot-${index}`}
                className="flex justify-between items-center p-3 rounded border"
                style={{ backgroundColor: 'rgb(var(--canvas-default))' }}
              >
                <div>
                  <div
                    className="font-medium"
                    style={{ color: 'rgb(var(--fg-default))' }}
                  >
                    {formatValue(snapshot.nav_quote, snapshot.quote_asset)}
                  </div>
                  <div
                    className="text-sm"
                    style={{ color: 'rgb(var(--fg-muted))' }}
                  >
                    {snapshot.asset_count} assets • {snapshot.source}
                  </div>
                </div>
                <div
                  className="text-sm text-right"
                  style={{ color: 'rgb(var(--fg-muted))' }}
                >
                  <div>{formatDateTime(snapshot.ts)}</div>
                  <div className="text-xs">
                    {snapshot.exchange_account || 'No Account'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
