import { useState } from 'react';
import { Button } from '@shared/ui/Button';
import { apiClient } from '@shared/lib/api';

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

  const fetchSnapshots = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getPortfolioSnapshots({ limit: 20 });
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
    } catch (e) {
      return 'Invalid Date';
    }
  };

  const formatValue = (value: string, currency: string) => {
    return `${parseFloat(value).toFixed(2)} ${currency}`;
  };

  const formatShortDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;
    } catch (e) {
      return '--';
    }
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
          >
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
          <Button
            onClick={() => createSnapshot(false)}
            disabled={loading}
            size="sm"
          >
            Create Snapshot
          </Button>
          <Button
            onClick={() => createSnapshot(true)}
            disabled={loading}
            size="sm"
            variant="outline"
          >
            Force Create
          </Button>
          <Button
            onClick={deleteAllSnapshots}
            disabled={loading}
            size="sm"
            variant="destructive"
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

      {/* Simple NAV Chart */}
      {snapshots.length > 0 && (
        <div className="mb-6">
          <h4
            className="text-md font-medium mb-3"
            style={{ color: 'rgb(var(--fg-default))' }}
          >
            NAV History
          </h4>
          <div className="h-48 bg-gradient-to-b from-blue-50 to-white p-4 rounded-lg border border-blue-200">
            <div className="h-full flex items-end justify-between gap-1">
              {snapshots
                .slice()
                .reverse()
                .slice(-12) // Last 12 snapshots
                .map((snapshot, index) => {
                  const navValue = parseFloat(snapshot.nav_quote);
                  const maxNav = Math.max(
                    ...snapshots.map(s => parseFloat(s.nav_quote)),
                  );
                  const minNav = Math.min(
                    ...snapshots.map(s => parseFloat(s.nav_quote)),
                  );
                  const range = maxNav - minNav;
                  const height = range > 0 
                    ? Math.max(((navValue - minNav) / range) * 140, 20) 
                    : 50; // Min height 20px

                  // Color based on performance vs previous
                  const isFirst = index === 0;
                  const prevValue = !isFirst ? parseFloat(snapshots.slice().reverse().slice(-12)[index - 1].nav_quote) : navValue;
                  const isUp = navValue >= prevValue;
                  const barColor = isUp ? 'from-green-400 to-green-600' : 'from-red-400 to-red-600';

                  return (
                    <div key={snapshot.id} className="flex flex-col items-center group">
                      <div
                        className={`w-8 rounded-t-lg bg-gradient-to-t ${barColor} shadow-sm hover:shadow-md transition-all cursor-pointer relative`}
                        style={{ height: `${height}px` }}
                        title={`${formatValue(snapshot.nav_quote, snapshot.quote_asset)} at ${formatDateTime(snapshot.ts)}`}
                      >
                        {/* Hover value display */}
                        <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                          ${parseFloat(snapshot.nav_quote).toFixed(0)}
                        </div>
                      </div>
                      <span className="text-xs mt-2 text-gray-500 font-mono">
                        {formatShortDate(snapshot.ts)}
                      </span>
                    </div>
                  );
                })}
            </div>
            {/* Chart legend */}
            <div className="mt-3 flex justify-between text-xs text-gray-500">
              <span>📈 NAV History (last 12 snapshots)</span>
              <span>💰 Current: ${snapshots.length > 0 ? parseFloat(snapshots[0].nav_quote).toFixed(0) : '0'}</span>
            </div>
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
            {snapshots.map(snapshot => (
              <div
                key={snapshot.id}
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
