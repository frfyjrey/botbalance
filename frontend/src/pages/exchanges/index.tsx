import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AppHeader } from '@widgets/layout/app-header';
import { useNavigate } from 'react-router-dom';
import { QUERY_KEYS, ROUTES } from '@shared/config/constants';
import { Button } from '@shared/ui/Button';
import type {
  ExchangeAccount,
  ExchangeAccountCreateRequest,
} from '@entities/exchange';
import {
  exchangeApi,
  EXCHANGE_CHOICES,
  ACCOUNT_TYPE_CHOICES,
  getHealthStatusColor,
  getHealthStatusText,
} from '@entities/exchange';

const ExchangesPage = () => {
  const { t } = useTranslation(['common']);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState<ExchangeAccount | null>(
    null,
  );
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Fetch exchange accounts
  const accountsQuery = useQuery({
    queryKey: [QUERY_KEYS.EXCHANGE_ACCOUNTS],
    queryFn: () => exchangeApi.getAll(),
    refetchInterval: 30000,
  });

  // Create account mutation
  const createMutation = useMutation({
    mutationFn: (data: ExchangeAccountCreateRequest) => {
      console.log('createMutation called with:', data);
      return exchangeApi.create(data);
    },
    onSuccess: result => {
      console.log('createMutation success:', result);
      qc.invalidateQueries({ queryKey: [QUERY_KEYS.EXCHANGE_ACCOUNTS] });
      setShowForm(false);
      resetForm();
    },
    onError: error => {
      console.error('createMutation error:', error);
    },
  });

  // Update account mutation
  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: Partial<ExchangeAccountCreateRequest>;
    }) => exchangeApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [QUERY_KEYS.EXCHANGE_ACCOUNTS] });
      setShowForm(false);
      setEditingAccount(null);
      resetForm();
    },
  });

  // Delete account mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      setDeletingId(id);
      try {
        return await exchangeApi.delete(id);
      } finally {
        setDeletingId(null);
      }
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: [QUERY_KEYS.EXCHANGE_ACCOUNTS] }),
  });

  // Health check mutation
  const checkMutation = useMutation({
    mutationFn: async (id: number) => {
      setCheckingId(id);
      try {
        return await exchangeApi.check(id);
      } finally {
        setCheckingId(null);
      }
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: [QUERY_KEYS.EXCHANGE_ACCOUNTS] }),
  });

  // Form state
  const [formData, setFormData] = useState<ExchangeAccountCreateRequest>({
    exchange: 'binance',
    account_type: 'spot',
    name: '',
    api_key: '',
    api_secret: '',
    passphrase: '',
    testnet: true,
    is_active: true,
  });

  const resetForm = () => {
    setFormData({
      exchange: 'binance',
      account_type: 'spot',
      name: '',
      api_key: '',
      api_secret: '',
      passphrase: '',
      testnet: true,
      is_active: true,
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('handleSubmit called with formData:', formData);

    if (editingAccount) {
      console.log('Updating account:', editingAccount.id);
      updateMutation.mutate({
        id: editingAccount.id,
        data: formData,
      });
    } else {
      console.log('Creating new account');
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (account: ExchangeAccount) => {
    setEditingAccount(account);
    setFormData({
      exchange: account.exchange,
      account_type: account.account_type,
      name: account.name,
      api_key: account.api_key,
      api_secret: '', // Don't pre-fill secret for security
      passphrase: '', // Don't pre-fill passphrase for security
      testnet: account.testnet,
      is_active: account.is_active,
    });
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingAccount(null);
    resetForm();
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader />
      <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 sm:py-6">
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h2 className="text-lg sm:text-xl font-semibold">
            {t('common:exchanges')}
          </h2>
          <div className="flex gap-2">
            {!showForm && (
              <Button
                onClick={() => setShowForm(true)}
                className="btn-github btn-github-primary text-xs sm:text-sm px-3 py-1.5"
              >
                {t('common:add')} Exchange
              </Button>
            )}
            <Button
              onClick={() => navigate(ROUTES.DASHBOARD)}
              className="btn-github btn-github-secondary text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5"
            >
              {t('common:back')}
            </Button>
          </div>
        </div>

        {/* Add/Edit Form */}
        {showForm && (
          <div className="rounded-lg border p-4 mb-6 bg-card">
            <h3 className="text-md font-medium mb-4">
              {editingAccount
                ? 'Edit Exchange Account'
                : 'Add New Exchange Account'}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Exchange
                  </label>
                  <select
                    value={formData.exchange}
                    onChange={e =>
                      setFormData(prev => ({
                        ...prev,
                        exchange: e.target.value as 'binance' | 'okx',
                      }))
                    }
                    className="w-full border rounded px-3 py-2 text-sm bg-transparent"
                    required
                  >
                    {EXCHANGE_CHOICES.map(choice => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Account Type
                  </label>
                  <select
                    value={formData.account_type}
                    onChange={e =>
                      setFormData(prev => ({
                        ...prev,
                        account_type: e.target.value as
                          | 'spot'
                          | 'earn'
                          | 'futures',
                      }))
                    }
                    className="w-full border rounded px-3 py-2 text-sm bg-transparent"
                    required
                  >
                    {ACCOUNT_TYPE_CHOICES.map(choice => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e =>
                    setFormData(prev => ({ ...prev, name: e.target.value }))
                  }
                  className="w-full border rounded px-3 py-2 text-sm bg-transparent"
                  placeholder="My Binance Testnet"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  API Key
                </label>
                <input
                  type="text"
                  value={formData.api_key}
                  onChange={e =>
                    setFormData(prev => ({ ...prev, api_key: e.target.value }))
                  }
                  className="w-full border rounded px-3 py-2 text-sm bg-transparent font-mono"
                  placeholder="Your API Key"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  API Secret
                </label>
                <input
                  type="password"
                  value={formData.api_secret}
                  onChange={e =>
                    setFormData(prev => ({
                      ...prev,
                      api_secret: e.target.value,
                    }))
                  }
                  className="w-full border rounded px-3 py-2 text-sm bg-transparent font-mono"
                  placeholder={
                    editingAccount
                      ? 'Leave empty to keep current secret'
                      : 'Your API Secret'
                  }
                  required={!editingAccount}
                />
              </div>

              {/* Passphrase field - show only for OKX */}
              {formData.exchange === 'okx' && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Passphrase <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    value={formData.passphrase || ''}
                    onChange={e =>
                      setFormData(prev => ({
                        ...prev,
                        passphrase: e.target.value,
                      }))
                    }
                    className="w-full border rounded px-3 py-2 text-sm bg-transparent font-mono"
                    placeholder={
                      editingAccount
                        ? 'Leave empty to keep current passphrase'
                        : 'Your OKX Passphrase'
                    }
                    required={!editingAccount}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Required for OKX exchange. Create this in your OKX API
                    settings.
                  </p>
                </div>
              )}

              <div className="flex items-center space-x-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.testnet}
                    onChange={e =>
                      setFormData(prev => ({
                        ...prev,
                        testnet: e.target.checked,
                      }))
                    }
                    className="mr-2"
                  />
                  <span className="text-sm">Testnet</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={e =>
                      setFormData(prev => ({
                        ...prev,
                        is_active: e.target.checked,
                      }))
                    }
                    className="mr-2"
                  />
                  <span className="text-sm">Active</span>
                </label>
              </div>

              {/* Error display */}
              {(createMutation.error || updateMutation.error) && (
                <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                  Error:{' '}
                  {(createMutation.error as Error)?.message ||
                    (updateMutation.error as Error)?.message ||
                    'Something went wrong'}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  type="submit"
                  disabled={
                    createMutation.isPending || updateMutation.isPending
                  }
                  className="btn-github btn-github-primary text-sm"
                >
                  {createMutation.isPending || updateMutation.isPending
                    ? `${editingAccount ? 'Updating' : 'Creating'}...`
                    : editingAccount
                      ? 'Update'
                      : 'Create'}
                </Button>
                <Button
                  type="button"
                  onClick={handleCancel}
                  className="btn-github btn-github-secondary text-sm"
                >
                  Cancel
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Error display for loading accounts */}
        {accountsQuery.error && (
          <div className="rounded-md bg-red-50 border border-red-200 p-4 mb-4 text-sm text-red-700">
            Error loading accounts:{' '}
            {(accountsQuery.error as Error)?.message ||
              'Failed to load exchange accounts'}
          </div>
        )}

        {/* Accounts List */}
        <div className="rounded-lg border overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/20">
              <tr>
                <th className="text-left p-4 font-medium">Name</th>
                <th className="text-left p-4 font-medium">Exchange</th>
                <th className="text-left p-4 font-medium">Type</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Health</th>
                <th className="text-left p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {accountsQuery.data?.map(account => (
                <tr key={account.id} className="border-b hover:bg-muted/10">
                  <td className="p-4">
                    <div>
                      <div className="font-medium">{account.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {account.testnet && '🧪 Testnet'}
                      </div>
                    </div>
                  </td>
                  <td className="p-4 capitalize">{account.exchange}</td>
                  <td className="p-4 capitalize">{account.account_type}</td>
                  <td className="p-4">
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                        account.is_active
                          ? 'bg-green-50 text-green-700 border border-green-200'
                          : 'bg-gray-50 text-gray-700 border border-gray-200'
                      }`}
                    >
                      {account.is_active ? 'Активен' : 'Неактивен'}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          getHealthStatusColor(account, 60).includes('green')
                            ? 'bg-green-500'
                            : getHealthStatusColor(account, 60).includes('red')
                              ? 'bg-red-500'
                              : 'bg-gray-400'
                        }`}
                      />
                      <span
                        className={`text-xs ${getHealthStatusColor(account, 60)}`}
                        title={`last_success_at: ${account.last_success_at}, last_latency_ms: ${account.last_latency_ms}`}
                      >
                        {getHealthStatusText(account, 60)}
                      </span>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <Button
                        onClick={() => checkMutation.mutate(account.id)}
                        disabled={checkingId === account.id}
                        className="btn-github btn-github-invisible text-xs px-2 py-1"
                        title="Быстрая проверка соединения"
                      >
                        {checkingId === account.id ? 'Checking...' : 'Check'}
                      </Button>
                      <Button
                        onClick={() => handleEdit(account)}
                        className="btn-github btn-github-invisible text-xs px-2 py-1"
                      >
                        Edit
                      </Button>
                      <Button
                        onClick={() => deleteMutation.mutate(account.id)}
                        disabled={deletingId === account.id}
                        className="btn-github btn-github-invisible text-xs px-2 py-1 text-red-600 hover:text-red-700"
                      >
                        {deletingId === account.id ? 'Deleting...' : 'Delete'}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {!accountsQuery.data?.length && !accountsQuery.isLoading && (
                <tr>
                  <td
                    className="p-8 text-center text-muted-foreground"
                    colSpan={6}
                  >
                    No exchange accounts found. Add your first exchange account
                    to get started.
                  </td>
                </tr>
              )}
              {accountsQuery.isLoading && (
                <tr>
                  <td
                    className="p-8 text-center text-muted-foreground"
                    colSpan={6}
                  >
                    Loading...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};

export default ExchangesPage;
