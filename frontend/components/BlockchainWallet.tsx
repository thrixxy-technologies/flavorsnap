import { useState, useEffect } from 'react';
import { blockchainManager, WalletInfo, TokenInfo, VestingSchedule, TransactionResult } from '@/lib/blockchain';

export function BlockchainWallet() {
  const [walletInfo, setWalletInfo] = useState<WalletInfo | null>(null);
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [vestingSchedules, setVestingSchedules] = useState<VestingSchedule[]>([]);
  const [transactionHistory, setTransactionHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWalletInfo();
  }, []);

  const loadWalletInfo = async () => {
    try {
      setLoading(true);
      setError(null);

      // Check if wallet is available
      if (!blockchainManager.isWalletAvailable()) {
        setError('Wallet not available. Please install Freighter extension.');
        return;
      }

      const info = await blockchainManager.getWalletInfo();
      setWalletInfo(info);

      if (info.isConnected) {
        await loadTokenInfo();
        await loadVestingSchedules();
        await loadTransactionHistory();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load wallet info');
    } finally {
      setLoading(false);
    }
  };

  const loadTokenInfo = async () => {
    try {
      const info = await blockchainManager.getTokenInfo();
      setTokenInfo(info);
    } catch (err) {
      console.error('Failed to load token info:', err);
    }
  };

  const loadVestingSchedules = async () => {
    try {
      if (walletInfo?.publicKey) {
        const schedules = await blockchainManager.getVestingSchedules(walletInfo.publicKey);
        setVestingSchedules(schedules);
      }
    } catch (err) {
      console.error('Failed to load vesting schedules:', err);
    }
  };

  const loadTransactionHistory = async () => {
    try {
      if (walletInfo?.publicKey) {
        const history = await blockchainManager.getTransactionHistory(walletInfo.publicKey);
        setTransactionHistory(history);
      }
    } catch (err) {
      console.error('Failed to load transaction history:', err);
    }
  };

  const handleConnect = async () => {
    try {
      setLoading(true);
      setError(null);
      
      await blockchainManager.connectWallet();
      await loadWalletInfo();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect wallet');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      setLoading(true);
      setError(null);
      
      await blockchainManager.disconnectWallet();
      setWalletInfo(null);
      setTokenInfo(null);
      setVestingSchedules([]);
      setTransactionHistory([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect wallet');
    } finally {
      setLoading(false);
    }
  };

  if (!blockchainManager.isWalletAvailable()) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <div className="mb-4">
          <svg className="w-12 h-12 mx-auto text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M9 9h6m-6 0H6a2 2 0 00-2 2v6a2 2 0 006-2-2h2a2 2 0 00-2-2V9a2 2 0 002-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-yellow-800 mb-2">Wallet Not Available</h3>
        <p className="text-yellow-700 mb-4">
          Please install Freighter browser extension to connect your wallet and interact with the blockchain features.
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

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4 mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Blockchain Wallet</h2>
        
        {walletInfo && (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${
                walletInfo.isConnected ? 'bg-green-500' : 'bg-gray-400'
              }`} />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {walletInfo.isConnected ? 'Connected' : 'Disconnected'}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Network: {walletInfo.network}
                </p>
                <p className="text-sm font-mono text-gray-600 dark:text-gray-300">
                  {walletInfo.publicKey}
                </p>
              </div>
            </div>
            
            <div className="flex space-x-2">
              {!walletInfo.isConnected ? (
                <button
                  onClick={handleConnect}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {loading ? 'Connecting...' : 'Connect Wallet'}
                </button>
              ) : (
                <button
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

      {/* Token Info */}
      {tokenInfo && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {tokenInfo.name} ({tokenInfo.symbol})
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Balance</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {tokenInfo.balance}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Supply</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {tokenInfo.totalSupply}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      {walletInfo?.isConnected && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white">Mint Tokens</h4>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Recipient address"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  id="mint-recipient"
                />
                <input
                  type="text"
                  placeholder="Amount"
                  className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  id="mint-amount"
                />
                <button
                  onClick={() => {
                    const recipient = (document.getElementById('mint-recipient') as HTMLInputElement).value;
                    const amount = (document.getElementById('mint-amount') as HTMLInputElement).value;
                    blockchainManager.mintTokens(recipient, amount);
                  }}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {loading ? 'Minting...' : 'Mint'}
                </button>
              </div>
            </div>
            
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white">Transfer Tokens</h4>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Recipient address"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  id="transfer-recipient"
                />
                <input
                  type="text"
                  placeholder="Amount"
                  className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  id="transfer-amount"
                />
                <button
                  onClick={() => {
                    const recipient = (document.getElementById('transfer-recipient') as HTMLInputElement).value;
                    const amount = (document.getElementById('transfer-amount') as HTMLInputElement).value;
                    blockchainManager.transferTokens(recipient, amount);
                  }}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  {loading ? 'Transferring...' : 'Transfer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Vesting Schedules */}
      {vestingSchedules.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Vesting Schedules</h3>
          <div className="space-y-4">
            {vestingSchedules.map((schedule) => (
              <div key={schedule.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-white">Schedule #{schedule.id}</h4>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {new Date(schedule.startTime * 1000).toLocaleDateString()}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600 dark:text-gray-400">Recipient</p>
                    <p className="font-mono">{schedule.recipient}</p>
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
                    onClick={() => blockchainManager.releaseVestedFunds(schedule.id)}
                    disabled={loading}
                    className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
                  >
                    {loading ? 'Releasing...' : 'Release Vested Funds'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transaction History */}
      {transactionHistory.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Transaction History</h3>
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
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-white">
                      {tx.hash}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {tx.type}
                    </td>
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
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        tx.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
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

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M9 9h6m-6 0H6a2 2 0 00-2 2v6a2 2 0 006-2-2h2a2 2 0 00-2-2V9a2 2 0 002-2 2z" />
            </svg>
            <p className="text-red-800 font-medium">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
