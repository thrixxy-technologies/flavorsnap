import { useState, useEffect, useCallback } from 'react';
import {
  blockchainManager,
  WalletInfo,
  TokenInfo,
  VestingSchedule,
  TransactionResult,
  DataSource,
  ChainTransactionRow,
  BlockchainUserError,
  BackendHealthResult,
  describeLocalFallbackReason,
  pickWorstLocalFallback,
  LocalFallbackReason,
} from '@/lib/blockchain';

function summarizeTxResult(label: string, result: TransactionResult): string {
  if (!result.success) {
    return `${label} failed: ${result.error || 'Unknown error'}`;
  }
  const sync = result.backendSyncError
    ? ` (saved on device; server sync: ${result.backendSyncError})`
    : '';
  return `${label} submitted. Tx: ${result.txHash || 'n/a'}${sync}`;
}

export function BlockchainWallet() {
  const [freighterReady, setFreighterReady] = useState<boolean | null>(null);
  const [walletInfo, setWalletInfo] = useState<WalletInfo | null>(null);
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [vestingSchedules, setVestingSchedules] = useState<VestingSchedule[]>([]);
  const [transactionHistory, setTransactionHistory] = useState<ChainTransactionRow[]>([]);
  const [tokenSource, setTokenSource] = useState<DataSource | null>(null);
  const [vestingSource, setVestingSource] = useState<DataSource | null>(null);
  const [txSource, setTxSource] = useState<DataSource | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealthResult | null>(null);
  const [healthChecking, setHealthChecking] = useState(false);
  const [vestingFallbackMeta, setVestingFallbackMeta] = useState<{ reason?: LocalFallbackReason; detail?: string }>({});
  const [txFallbackMeta, setTxFallbackMeta] = useState<{ reason?: LocalFallbackReason; detail?: string }>({});

  const refreshBackendHealth = useCallback(async () => {
    setHealthChecking(true);
    try {
      const h = await blockchainManager.getBackendHealth();
      setBackendHealth(h);
    } finally {
      setHealthChecking(false);
    }
  }, []);

  const loadTokenInfo = useCallback(async (publicKey: string) => {
    try {
      const info = await blockchainManager.getTokenInfo(publicKey);
      setTokenInfo(info);
      setTokenSource(info?.dataSource ?? null);
    } catch (err) {
      console.error('Failed to load token info:', err);
      setError(err instanceof Error ? err.message : 'Failed to load token info');
    }
  }, []);

  const loadVestingSchedules = useCallback(async (publicKey: string) => {
    try {
      const { schedules, dataSource, localFallbackReason, localFallbackDetail } =
        await blockchainManager.getVestingSchedules(publicKey);
      setVestingSchedules(schedules);
      setVestingSource(dataSource);
      setVestingFallbackMeta(
        dataSource === 'backend' ? {} : { reason: localFallbackReason, detail: localFallbackDetail },
      );
    } catch (err) {
      console.error('Failed to load vesting schedules:', err);
      setVestingSchedules([]);
      setVestingSource('local');
      setVestingFallbackMeta({ reason: 'server_error', detail: err instanceof Error ? err.message : undefined });
    }
  }, []);

  const loadTransactionHistory = useCallback(async (publicKey: string) => {
    try {
      const { transactions, dataSource, localFallbackReason, localFallbackDetail } =
        await blockchainManager.getTransactionHistory(publicKey, 10);
      setTransactionHistory(transactions);
      setTxSource(dataSource);
      setTxFallbackMeta(
        dataSource === 'backend' ? {} : { reason: localFallbackReason, detail: localFallbackDetail },
      );
    } catch (err) {
      console.error('Failed to load transaction history:', err);
      setTransactionHistory([]);
      setTxSource('local');
      setTxFallbackMeta({ reason: 'server_error', detail: err instanceof Error ? err.message : undefined });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await blockchainManager.isFreighterBridgeAvailable();
      if (!cancelled) setFreighterReady(ok);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadWalletInfo = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setInfoMessage(null);

      const bridgeOk = await blockchainManager.isFreighterBridgeAvailable();
      setFreighterReady(bridgeOk);
      if (!bridgeOk) {
        setWalletInfo(null);
        setError('Freighter is not available. Install the browser extension to use the wallet.');
        return;
      }

      const info = await blockchainManager.getWalletInfo();
      setWalletInfo(info);

      if (info.isConnected && info.publicKey) {
        await Promise.all([
          loadTokenInfo(info.publicKey),
          loadVestingSchedules(info.publicKey),
          loadTransactionHistory(info.publicKey),
        ]);
      } else {
        setTokenInfo(null);
        setVestingSchedules([]);
        setTransactionHistory([]);
        setTokenSource(null);
        setVestingSource(null);
        setTxSource(null);
        setVestingFallbackMeta({});
        setTxFallbackMeta({});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load wallet info');
    } finally {
      setLoading(false);
    }
  }, [loadTokenInfo, loadVestingSchedules, loadTransactionHistory]);

  useEffect(() => {
    if (freighterReady !== true) return;
    void loadWalletInfo();
  }, [freighterReady, loadWalletInfo]);

  useEffect(() => {
    if (freighterReady !== true) return;
    void refreshBackendHealth();
  }, [freighterReady, refreshBackendHealth]);

  const handleConnect = async () => {
    try {
      setLoading(true);
      setError(null);
      setInfoMessage(null);
      await blockchainManager.connectWallet();
      await loadWalletInfo();
      setInfoMessage('Wallet connected successfully.');
    } catch (err) {
      if (err instanceof BlockchainUserError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to connect wallet');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      setLoading(true);
      setError(null);
      setInfoMessage(null);

      await blockchainManager.disconnectWallet();
      setTokenInfo(null);
      setVestingSchedules([]);
      setTransactionHistory([]);
      setTokenSource(null);
      setVestingSource(null);
      setTxSource(null);
      setVestingFallbackMeta({});
      setTxFallbackMeta({});
      const info = await blockchainManager.getWalletInfo();
      setWalletInfo(info);
      setInfoMessage('Disconnected from this session. You can revoke site access from the Freighter extension if needed.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect wallet');
    } finally {
      setLoading(false);
    }
  };

  const runTxAction = async (label: string, fn: () => Promise<TransactionResult>) => {
    setActionLoading(label);
    setError(null);
    setInfoMessage(null);
    try {
      const result = await fn();
      const msg = summarizeTxResult(label, result);
      if (result.success) {
        setInfoMessage(msg);
        if (result.backendSyncError) {
          setError(`Server sync issue: ${result.backendSyncError}`);
        }
        const live = await blockchainManager.getWalletInfo();
        if (live.publicKey) {
          await loadTokenInfo(live.publicKey);
          await loadTransactionHistory(live.publicKey);
        }
      } else {
        setError(msg);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : `${label} failed`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMint = () => {
    const recipient = (document.getElementById('mint-recipient') as HTMLInputElement)?.value ?? '';
    const amount = (document.getElementById('mint-amount') as HTMLInputElement)?.value ?? '';
    runTxAction('Mint', () => blockchainManager.mintTokens(recipient, amount));
  };

  const handleTransfer = () => {
    const recipient = (document.getElementById('transfer-recipient') as HTMLInputElement)?.value ?? '';
    const amount = (document.getElementById('transfer-amount') as HTMLInputElement)?.value ?? '';
    runTxAction('Transfer', () => blockchainManager.transferTokens(recipient, amount));
  };

  const handleRelease = (scheduleId: number) => {
    runTxAction('Release vesting', () => blockchainManager.releaseVestedFunds(scheduleId));
  };

  if (freighterReady === null) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-4xl mx-auto animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4" />
        <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded w-2/3" />
      </div>
    );
  }

  if (!freighterReady) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center dark:bg-yellow-950/30 dark:border-yellow-800">
        <div className="mb-4">
          <svg className="w-12 h-12 mx-auto text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01M9 9h6m-6 0H6a2 2 0 00-2 2v6a2 2 0 006-2-2h2a2 2 0 00-2-2V9a2 2 0 002-2 2z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-yellow-800 mb-2 dark:text-yellow-200">Wallet Not Available</h3>
        <p className="text-yellow-700 mb-4 dark:text-yellow-100/90">
          Install the Freighter browser extension so this app can connect to your Stellar wallet and talk to FlavorSnap
          blockchain APIs.
        </p>
        <a
          href="https://freighter.app"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block bg-yellow-600 hover:bg-yellow-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          Install Freighter
        </a>
      </div>
    );
  }

  const showLocalDataBanner =
    walletInfo?.isConnected &&
    (tokenSource === 'local' || vestingSource === 'local' || txSource === 'local');

  const worstPreview = pickWorstLocalFallback([
    { reason: tokenInfo?.localFallbackReason, detail: tokenInfo?.localFallbackDetail },
    vestingFallbackMeta,
    txFallbackMeta,
  ]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          API base:{' '}
          <span className="font-mono text-xs text-gray-900 dark:text-gray-200">{blockchainManager.getBackendBaseUrl()}</span>
        </p>
        <div className="flex items-center gap-2">
          {healthChecking ? (
            <span className="text-xs text-gray-500">Checking /health…</span>
          ) : backendHealth ? (
            <span
              className={`text-xs font-medium px-2 py-1 rounded ${
                backendHealth.reachable
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
                  : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'
              }`}
            >
              {backendHealth.reachable
                ? `API up${backendHealth.httpStatus != null ? ` (${backendHealth.httpStatus})` : ''}`
                : `API unreachable${backendHealth.message ? `: ${backendHealth.message}` : ''}`}
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => void refreshBackendHealth()}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          >
            Refresh status
          </button>
        </div>
      </div>

      {infoMessage && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-4 dark:bg-emerald-950/30 dark:border-emerald-800">
          <p className="text-emerald-900 dark:text-emerald-100 text-sm font-medium">{infoMessage}</p>
        </div>
      )}

      {showLocalDataBanner && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4 dark:bg-amber-950/30 dark:border-amber-800">
          <p className="text-amber-900 dark:text-amber-100 text-sm font-medium mb-1">
            Offline preview — blockchain REST data is not loaded from the server
          </p>
          <p className="text-amber-900 dark:text-amber-100 text-sm">
            {worstPreview
              ? describeLocalFallbackReason(worstPreview.reason, worstPreview.detail)
              : 'Configure NEXT_PUBLIC_BLOCKCHAIN_BACKEND_URL if the API is not at the default host, and implement /api/blockchain/token-info, /vesting, and /transactions on the backend.'}
          </p>
          {backendHealth?.reachable && worstPreview?.reason === 'routes_missing' ? (
            <p className="text-amber-800 dark:text-amber-200/90 text-xs mt-2">
              /health responded OK, so your process is running — only the blockchain routes need to be wired up.
            </p>
          ) : null}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 dark:bg-red-950/30 dark:border-red-800">
          <div className="flex">
            <svg className="w-5 h-5 text-red-400 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M9 9h6m-6 0H6a2 2 0 00-2 2v6a2 2 0 006-2-2h2a2 2 0 00-2-2V9a2 2 0 002-2 2z"
              />
            </svg>
            <p className="text-red-800 dark:text-red-200 font-medium text-sm">{error}</p>
          </div>
        </div>
      )}

      <div className="border-b border-gray-200 dark:border-gray-700 pb-4 mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Blockchain Wallet</h2>

        {walletInfo && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${walletInfo.isConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {walletInfo.isConnected ? 'Connected' : 'Disconnected'}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Network: {walletInfo.network}</p>
                <p className="text-sm font-mono text-gray-600 dark:text-gray-300 break-all">
                  {walletInfo.publicKey || '—'}
                </p>
              </div>
            </div>

            <div className="flex space-x-2">
              {!walletInfo.isConnected ? (
                <button
                  type="button"
                  onClick={handleConnect}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {loading ? 'Connecting...' : 'Connect Wallet'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleDisconnect}
                  disabled={loading}
                  className="bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {loading ? 'Disconnecting...' : 'Disconnect'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {tokenInfo && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {tokenInfo.name} ({tokenInfo.symbol})
            </h3>
            {tokenSource && (
              <span
                className={`text-xs font-medium px-2 py-1 rounded ${
                  tokenSource === 'backend'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
                }`}
              >
                {tokenSource === 'backend' ? 'API' : 'Local preview'}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Balance</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{tokenInfo.balance}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Supply</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{tokenInfo.totalSupply}</p>
            </div>
          </div>
        </div>
      )}

      {walletInfo?.isConnected && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white">Mint Tokens</h4>
              <div className="flex flex-wrap gap-2">
                <input
                  type="text"
                  placeholder="Recipient address"
                  className="flex-1 min-w-[140px] px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  id="mint-recipient"
                />
                <input
                  type="text"
                  placeholder="Amount"
                  className="w-24 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  id="mint-amount"
                />
                <button
                  type="button"
                  onClick={handleMint}
                  disabled={!!actionLoading || loading}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {actionLoading === 'Mint' ? 'Minting...' : 'Mint'}
                </button>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white">Transfer Tokens</h4>
              <div className="flex flex-wrap gap-2">
                <input
                  type="text"
                  placeholder="Recipient address"
                  className="flex-1 min-w-[140px] px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  id="transfer-recipient"
                />
                <input
                  type="text"
                  placeholder="Amount"
                  className="w-24 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  id="transfer-amount"
                />
                <button
                  type="button"
                  onClick={handleTransfer}
                  disabled={!!actionLoading || loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {actionLoading === 'Transfer' ? 'Transferring...' : 'Transfer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {walletInfo?.isConnected && vestingSchedules.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Vesting Schedules</h3>
            {vestingSource && (
              <span
                className={`text-xs font-medium px-2 py-1 rounded ${
                  vestingSource === 'backend'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
                }`}
              >
                {vestingSource === 'backend' ? 'API' : 'Local preview'}
              </span>
            )}
          </div>
          <div className="space-y-4">
            {vestingSchedules.map((schedule) => (
              <div key={schedule.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-white">Schedule #{schedule.id}</h4>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Start {new Date(schedule.startTime * 1000).toLocaleDateString()}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600 dark:text-gray-400">Recipient</p>
                    <p className="font-mono break-all">{schedule.recipient}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 dark:text-gray-400">Total Amount</p>
                    <p className="font-mono">{schedule.totalAmount}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 dark:text-gray-400">Duration</p>
                    <p>{schedule.duration / 86400} days</p>
                  </div>
                  <div>
                    <p className="text-gray-600 dark:text-gray-400">Cliff</p>
                    <p>{schedule.cliff / 86400} days</p>
                  </div>
                </div>
                <div className="mt-4">
                  <div className="flex justify-between items-center mb-2">
                    <div>
                      <p className="text-gray-600 dark:text-gray-400">Released</p>
                      <p className="font-mono">{schedule.releasedAmount}</p>
                    </div>
                    <div>
                      <p className="text-gray-600 dark:text-gray-400">Remaining</p>
                      <p className="font-mono">{schedule.remainingAmount}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRelease(schedule.id)}
                    disabled={!!actionLoading || loading}
                    className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                  >
                    {actionLoading === 'Release vesting' ? 'Releasing...' : 'Release Vested Funds'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {walletInfo?.isConnected && transactionHistory.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Transaction History</h3>
            {txSource && (
              <span
                className={`text-xs font-medium px-2 py-1 rounded ${
                  txSource === 'backend'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
                }`}
              >
                {txSource === 'backend' ? 'API' : 'Local preview'}
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Hash
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    From
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    To
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {transactionHistory.map((tx, index) => (
                  <tr key={`${tx.hash}-${index}`} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-white">
                      {tx.hash}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">{tx.type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-white">
                      {tx.from}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-white">
                      {tx.to}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-white">
                      {tx.amount}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {new Date(tx.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          tx.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {tx.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
