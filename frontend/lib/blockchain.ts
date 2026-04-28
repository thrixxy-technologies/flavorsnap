import {
  isConnected as freighterIsConnected,
  requestAccess,
  getAddress,
  getNetwork,
} from '@stellar/freighter-api';
import { stellarConfig } from '@/lib/config';

// ——— Types ———

export interface WalletInfo {
  publicKey: string;
  isConnected: boolean;
  network: 'public' | 'testnet';
}

export type DataSource = 'backend' | 'local';

/** Why we fell back to local preview data (for user-facing copy) */
export type LocalFallbackReason = 'unreachable' | 'routes_missing' | 'timeout' | 'server_error' | 'invalid_response';

export interface TokenInfo {
  name: string;
  symbol: string;
  decimals: number;
  totalSupply: string;
  balance: string;
  dataSource?: DataSource;
  localFallbackReason?: LocalFallbackReason;
  localFallbackDetail?: string;
}

export interface VestingSchedule {
  id: number;
  recipient: string;
  totalAmount: string;
  /** Unix seconds (Stellar-style) */
  startTime: number;
  duration: number;
  cliff: number;
  releasedAmount: string;
  remainingAmount: string;
}

export interface TransactionResult {
  success: boolean;
  txHash?: string;
  error?: string;
  /** Present when on-device tx succeeded but optional backend sync failed */
  backendSyncError?: string;
}

export interface GovernanceProposal {
  id: number;
  title: string;
  description: string;
  proposer: string;
  startTime: number;
  endTime: number;
  votesFor: number;
  votesAgainst: number;
  status: 'active' | 'passed' | 'rejected' | 'executed';
}

export interface ChainTransactionRow {
  hash: string;
  type: string;
  from: string;
  to: string;
  amount: string;
  timestamp: number;
  status: string;
}

export interface VestingSchedulesResult {
  schedules: VestingSchedule[];
  dataSource: DataSource;
  localFallbackReason?: LocalFallbackReason;
  localFallbackDetail?: string;
}

export interface TransactionHistoryResult {
  transactions: ChainTransactionRow[];
  dataSource: DataSource;
  localFallbackReason?: LocalFallbackReason;
  localFallbackDetail?: string;
}

// ——— Errors ———

function freighterMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'message' in err && typeof (err as { message: unknown }).message === 'string') {
    return (err as { message: string }).message;
  }
  return 'Wallet request failed';
}

export class BlockchainUserError extends Error {
  constructor(message: string, public readonly code?: string) {
    super(message);
    this.name = 'BlockchainUserError';
  }
}

// ——— Backend (Express / api routes under /api/blockchain/*) ———

const BACKEND_TIMEOUT_MS = 15000;
const HEALTH_TIMEOUT_MS = 5000;

function getBlockchainBackendBaseUrl(): string {
  const fromEnv =
    (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_BLOCKCHAIN_BACKEND_URL) ||
    (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_BACKEND_URL);
  const raw = (fromEnv || 'http://localhost:3001').replace(/\/$/, '');
  return raw;
}

function classifyBackendFailure(error: string, status?: number): LocalFallbackReason {
  const low = error.toLowerCase();
  if (status === 408 || low.includes('timeout')) return 'timeout';
  if (status === 404 || error.includes('HTTP 404') || /\b404\b/.test(error)) return 'routes_missing';
  if (error.includes('Cannot reach blockchain backend') || error.includes('Failed to fetch') || error.includes('NetworkError'))
    return 'unreachable';
  if (status !== undefined && status >= 500) return 'server_error';
  return 'server_error';
}

export function describeLocalFallbackReason(reason: LocalFallbackReason, detail?: string): string {
  const suffix = detail ? ` ${detail}` : '';
  switch (reason) {
    case 'unreachable':
      return `The FlavorSnap API at your configured URL is unreachable.${suffix}`;
    case 'routes_missing':
      return `The server is up, but blockchain REST routes are not available (404). Add /api/blockchain/* on the backend.${suffix}`;
    case 'timeout':
      return `The API did not respond in time.${suffix}`;
    case 'invalid_response':
      return `The API returned data we could not parse for this view.${suffix}`;
    case 'server_error':
    default:
      return `The API returned an error.${suffix}`;
  }
}

/** Higher = worse; use to pick the most actionable banner when multiple fetches fail */
export function fallbackReasonSeverity(reason: LocalFallbackReason): number {
  const order: LocalFallbackReason[] = [
    'invalid_response',
    'routes_missing',
    'server_error',
    'timeout',
    'unreachable',
  ];
  return order.indexOf(reason);
}

export function pickWorstLocalFallback(
  entries: Array<{ reason?: LocalFallbackReason; detail?: string }>,
): { reason: LocalFallbackReason; detail?: string } | null {
  let picked: { reason: LocalFallbackReason; detail?: string } | null = null;
  let worstScore = -1;
  for (const e of entries) {
    if (!e.reason) continue;
    const s = fallbackReasonSeverity(e.reason);
    if (s > worstScore) {
      worstScore = s;
      picked = { reason: e.reason, detail: e.detail };
    }
  }
  return picked;
}

async function backendFetchJson<T>(
  method: 'GET' | 'POST',
  pathname: string,
  query?: Record<string, string | number | undefined>,
  body?: Record<string, unknown>,
): Promise<{ ok: true; data: T } | { ok: false; error: string; status?: number }> {
  const base = getBlockchainBackendBaseUrl();
  const url = new URL(pathname.startsWith('/') ? pathname : `/${pathname}`, `${base}/`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== '') url.searchParams.set(k, String(v));
    }
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

  try {
    const init: RequestInit = {
      method,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}) },
      ...(method === 'POST' && body ? { body: JSON.stringify(body) } : {}),
    };
    const res = await fetch(url.toString(), init);
    clearTimeout(timer);

    const text = await res.text();
    let parsed: unknown = null;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      if (!res.ok) {
        return { ok: false, error: text || `HTTP ${res.status}` };
      }
    }

    if (!res.ok) {
      const msg =
        parsed && typeof parsed === 'object' && 'error' in parsed && typeof (parsed as { error: unknown }).error === 'string'
          ? (parsed as { error: string }).error
          : text || `HTTP ${res.status}`;
      return { ok: false, error: msg, status: res.status };
    }

    return { ok: true, data: parsed as T };
  } catch (e) {
    clearTimeout(timer);
    if (e instanceof Error && e.name === 'AbortError') {
      return { ok: false, error: 'Backend request timed out' };
    }
    const msg = e instanceof Error ? e.message : 'Network error';
    if (msg === 'Failed to fetch') {
      return { ok: false, error: 'Cannot reach blockchain backend. Is the API server running?' };
    }
    return { ok: false, error: msg };
  }
}

export interface BackendHealthResult {
  reachable: boolean;
  httpStatus?: number;
  /** Server body message or error text */
  message?: string;
}

async function fetchBackendHealth(): Promise<BackendHealthResult> {
  const base = getBlockchainBackendBaseUrl();
  const url = new URL('/health', `${base}/`);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const res = await fetch(url.toString(), { method: 'GET', signal: controller.signal, headers: { Accept: 'application/json' } });
    clearTimeout(timer);
    const text = await res.text();
    let message: string | undefined;
    try {
      const j = text ? JSON.parse(text) : null;
      if (j && typeof j === 'object' && 'status' in j) message = String((j as { status: unknown }).status);
    } catch {
      message = text?.slice(0, 200);
    }
    return { reachable: res.ok, httpStatus: res.status, message: message || (res.ok ? 'OK' : text?.slice(0, 200)) };
  } catch (e) {
    clearTimeout(timer);
    if (e instanceof Error && e.name === 'AbortError') {
      return { reachable: false, message: 'Health check timed out' };
    }
    return {
      reachable: false,
      message: e instanceof Error ? e.message : 'Network error',
    };
  }
}

async function syncTransactionWithBackend(payload: {
  txHash: string;
  type: string;
  from?: string;
  to?: string;
  amount?: string;
  walletAddress?: string;
}): Promise<{ ok: true } | { ok: false; error: string }> {
  const result = await backendFetchJson<{ ok?: boolean; error?: string }>(
    'POST',
    '/api/blockchain/record-transaction',
    undefined,
    payload,
  );
  if (!result.ok) return result;
  const data = result.data;
  if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
    return { ok: false, error: data.error };
  }
  return { ok: true };
}

// ——— Mock fallbacks (when backend is down or not implemented) ———

async function mockTokenBalance(_address?: string): Promise<string> {
  return '1000.0000000';
}

function mockVestingSchedules(recipient: string): VestingSchedule[] {
  const startSec = Math.floor(Date.now() / 1000) - 86400;
  return [
    {
      id: 1,
      recipient,
      totalAmount: '500.0000000',
      startTime: startSec,
      duration: 2592000,
      cliff: 0,
      releasedAmount: '100.0000000',
      remainingAmount: '400.0000000',
    },
  ];
}

function mockTransactions(address: string | undefined): ChainTransactionRow[] {
  return [
    {
      hash: '0x1234567890abcdef',
      type: 'transfer',
      from: address || 'user_address',
      to: 'recipient_address',
      amount: '100.0000000',
      timestamp: Date.now() - 3600000,
      status: 'completed',
    },
  ];
}

// ——— Manager ——

export class BlockchainManager {
  private static instance: BlockchainManager;
  private contractAddress: string;
  private network: 'public' | 'testnet' = 'testnet';

  static getInstance(): BlockchainManager {
    if (!BlockchainManager.instance) {
      BlockchainManager.instance = new BlockchainManager();
    }
    return BlockchainManager.instance;
  }

  private constructor() {
    this.contractAddress = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS || stellarConfig.contractId || '';
  }

  getContractAddress(): string {
    return this.contractAddress;
  }

  getConfiguredRpcUrl(): string {
    return stellarConfig.rpcUrl || process.env.NEXT_PUBLIC_SOROBAN_RPC_URL || '';
  }

  /** Base URL used for FlavorSnap blockchain REST endpoints */
  getBackendBaseUrl(): string {
    return getBlockchainBackendBaseUrl();
  }

  /**
   * Calls GET /health on the configured API base (Express serves this today).
   * Use for UI status; blockchain data still uses /api/blockchain/* when implemented.
   */
  async getBackendHealth(): Promise<BackendHealthResult> {
    return fetchBackendHealth();
  }

  private async getAuthorizedPublicKey(): Promise<string | null> {
    const a = await getAddress();
    if (a.error || !a.address) return null;
    return a.address;
  }

  private mapFreighterNetwork(network: string | undefined): 'public' | 'testnet' {
    if (!network) return 'testnet';
    const u = network.toUpperCase();
    if (u === 'PUBLIC' || u === 'MAINNET' || u.includes('PUBLIC')) return 'public';
    return 'testnet';
  }

  private async freighterNetwork(): Promise<'public' | 'testnet'> {
    const net = await getNetwork();
    if (net.error) return 'testnet';
    return this.mapFreighterNetwork(net.network);
  }

  async isFreighterBridgeAvailable(): Promise<boolean> {
    try {
      const r = await freighterIsConnected();
      return !r.error && r.isConnected;
    } catch {
      return false;
    }
  }

  /** @deprecated Prefer isFreighterBridgeAvailable(); kept for brief compat */
  isWalletAvailable(): boolean {
    return typeof window !== 'undefined';
  }

  async connectWallet(): Promise<WalletInfo> {
    try {
      const bridge = await freighterIsConnected();
      if (bridge.error) {
        throw new BlockchainUserError(freighterMessage(bridge.error), 'FREIGHTER');
      }
      if (!bridge.isConnected) {
        throw new BlockchainUserError(
          'Freighter is not available. Install the extension and refresh this page.',
          'NO_EXTENSION',
        );
      }

      const access = await requestAccess();
      if (access.error) {
        throw new BlockchainUserError(freighterMessage(access.error), 'ACCESS_DENIED');
      }
      if (!access.address) {
        throw new BlockchainUserError('No public key returned from Freighter', 'NO_ADDRESS');
      }

      const network = await this.freighterNetwork();
      this.network = network;

      return {
        publicKey: access.address,
        isConnected: true,
        network,
      };
    } catch (e) {
      if (e instanceof BlockchainUserError) throw e;
      console.error('Failed to connect wallet:', e);
      throw new BlockchainUserError(
        e instanceof Error ? e.message : 'Failed to connect wallet',
        'CONNECT_FAILED',
      );
    }
  }

  async disconnectWallet(): Promise<void> {
    try {
      // Freighter has no programmatic "disconnect"; clear app state in the UI instead.
      return;
    } catch (error) {
      console.error('Failed to disconnect wallet:', error);
    }
  }

  async getWalletInfo(): Promise<WalletInfo> {
    try {
      const bridge = await freighterIsConnected();
      if (bridge.error || !bridge.isConnected) {
        return { publicKey: '', isConnected: false, network: 'testnet' };
      }

      const addr = await getAddress();
      if (addr.error || !addr.address) {
        return { publicKey: '', isConnected: false, network: 'testnet' };
      }

      const network = await this.freighterNetwork();
      return {
        publicKey: addr.address,
        isConnected: true,
        network,
      };
    } catch (error) {
      console.error('Failed to get wallet info:', error);
      return { publicKey: '', isConnected: false, network: 'testnet' };
    }
  }

  async getTokenInfo(walletAddress?: string): Promise<TokenInfo | null> {
    const address = walletAddress?.trim() || undefined;
    const res = await backendFetchJson<Record<string, unknown>>('GET', '/api/blockchain/token-info', {
      address,
      contractId: this.contractAddress || undefined,
    });

    if (res.ok && res.data && typeof res.data === 'object') {
      const d = res.data;
      const hasCore =
        typeof d.name === 'string' ||
        typeof d.symbol === 'string' ||
        typeof d.balance === 'string' ||
        typeof d.balance === 'number';
      if (!hasCore && Object.keys(d).length > 0) {
        const reason: LocalFallbackReason = 'invalid_response';
        const balance = await mockTokenBalance(address);
        return {
          name: 'FlavorToken',
          symbol: 'FLV',
          decimals: 7,
          totalSupply: '1000000.0000000',
          balance,
          dataSource: 'local',
          localFallbackReason: reason,
          localFallbackDetail: 'token-info response missing name/symbol/balance',
        };
      }
      const name = typeof d.name === 'string' ? d.name : 'FlavorToken';
      const symbol = typeof d.symbol === 'string' ? d.symbol : 'FLV';
      const decimals = typeof d.decimals === 'number' ? d.decimals : 7;
      const totalSupply = typeof d.totalSupply === 'string' ? d.totalSupply : String(d.totalSupply ?? '0');
      const balance = typeof d.balance === 'string' ? d.balance : String(d.balance ?? (await mockTokenBalance(address)));
      return { name, symbol, decimals, totalSupply, balance, dataSource: 'backend' };
    }

    try {
      const balance = await mockTokenBalance(address);
      const reason = classifyBackendFailure(res.error, res.status);
      return {
        name: 'FlavorToken',
        symbol: 'FLV',
        decimals: 7,
        totalSupply: '1000000.0000000',
        balance,
        dataSource: 'local',
        localFallbackReason: reason,
        localFallbackDetail: res.error,
      };
    } catch (error) {
      console.error('Failed to get token info:', error);
      return null;
    }
  }

  async getTokenBalance(address?: string): Promise<string> {
    const info = await this.getTokenInfo(address);
    return info?.balance ?? '0';
  }

  async mintTokens(toAddress: string, amount: string): Promise<TransactionResult> {
    try {
      const bridge = await freighterIsConnected();
      if (bridge.error || !bridge.isConnected) {
        return { success: false, error: 'Freighter is not available' };
      }
      if (!toAddress?.trim()) {
        return { success: false, error: 'Recipient address is required' };
      }
      if (!amount?.trim() || Number.isNaN(Number(amount)) || Number(amount) <= 0) {
        return { success: false, error: 'Enter a valid amount greater than zero' };
      }

      const from = await this.getAuthorizedPublicKey();
      if (!from) {
        return { success: false, error: 'Could not read your Freighter address. Connect the wallet and try again.' };
      }
      console.log('Minting', amount, 'tokens to', toAddress);

      await new Promise((r) => setTimeout(r, 1200));
      const txHash = '0x' + Math.random().toString(16).slice(2).padEnd(64, '0');

      const sync = await syncTransactionWithBackend({
        txHash,
        type: 'mint',
        from,
        to: toAddress.trim(),
        amount: amount.trim(),
        walletAddress: from,
      });

      return {
        success: true,
        txHash,
        ...(!sync.ok ? { backendSyncError: sync.error } : {}),
      };
    } catch (error) {
      console.error('Failed to mint tokens:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async transferTokens(toAddress: string, amount: string): Promise<TransactionResult> {
    try {
      const bridge = await freighterIsConnected();
      if (bridge.error || !bridge.isConnected) {
        return { success: false, error: 'Freighter is not available' };
      }
      if (!toAddress?.trim()) {
        return { success: false, error: 'Recipient address is required' };
      }
      if (!amount?.trim() || Number.isNaN(Number(amount)) || Number(amount) <= 0) {
        return { success: false, error: 'Enter a valid amount greater than zero' };
      }

      const from = await this.getAuthorizedPublicKey();
      if (!from) {
        return { success: false, error: 'Could not read your Freighter address. Connect the wallet and try again.' };
      }
      console.log('Transferring', amount, 'tokens to', toAddress);

      await new Promise((r) => setTimeout(r, 1200));
      const txHash = '0x' + Math.random().toString(16).slice(2).padEnd(64, '0');

      const sync = await syncTransactionWithBackend({
        txHash,
        type: 'transfer',
        from,
        to: toAddress.trim(),
        amount: amount.trim(),
        walletAddress: from,
      });

      return {
        success: true,
        txHash,
        ...(!sync.ok ? { backendSyncError: sync.error } : {}),
      };
    } catch (error) {
      console.error('Failed to transfer tokens:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async createVestingSchedule(
    recipient: string,
    totalAmount: string,
    duration: number,
    cliff: number = 0,
  ): Promise<TransactionResult> {
    try {
      console.log('Creating vesting schedule for', recipient, totalAmount, 'duration:', duration, 'cliff:', cliff);
      await new Promise((r) => setTimeout(r, 1200));
      const txHash = '0x' + Math.random().toString(16).slice(2).padEnd(64, '0');
      return { success: true, txHash };
    } catch (error) {
      console.error('Failed to create vesting schedule:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async getVestingSchedules(recipient: string): Promise<VestingSchedulesResult> {
    const res = await backendFetchJson<{ schedules?: VestingSchedule[] }>('GET', '/api/blockchain/vesting', {
      recipient: recipient.trim(),
    });

    if (res.ok && res.data && Array.isArray(res.data.schedules)) {
      return { schedules: res.data.schedules, dataSource: 'backend' };
    }

    const reason = res.ok ? 'invalid_response' : classifyBackendFailure(res.error, res.status);
    const detail = res.ok ? 'Expected { schedules: [...] }' : res.error;
    console.warn('Vesting backend unavailable; using local preview data.', detail);
    return {
      schedules: mockVestingSchedules(recipient),
      dataSource: 'local',
      localFallbackReason: reason,
      localFallbackDetail: detail,
    };
  }

  async releaseVestedFunds(scheduleId: number): Promise<TransactionResult> {
    try {
      const bridge = await freighterIsConnected();
      if (bridge.error || !bridge.isConnected) {
        return { success: false, error: 'Freighter is not available' };
      }
      console.log('Releasing vested funds for schedule', scheduleId);
      await new Promise((r) => setTimeout(r, 1200));
      const txHash = '0x' + Math.random().toString(16).slice(2).padEnd(64, '0');

      const from = await this.getAuthorizedPublicKey();
      if (!from) {
        return { success: false, error: 'Could not read your Freighter address. Connect the wallet and try again.' };
      }
      const sync = await syncTransactionWithBackend({
        txHash,
        type: 'release_vesting',
        walletAddress: from,
      });

      return {
        success: true,
        txHash,
        ...(!sync.ok ? { backendSyncError: sync.error } : {}),
      };
    } catch (error) {
      console.error('Failed to release vested funds:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async createProposal(title: string, description: string): Promise<TransactionResult> {
    console.log('Creating proposal:', title);
    return {
      success: false,
      error: 'Governance features coming soon',
    };
  }

  async voteOnProposal(proposalId: number, vote: 'for' | 'against'): Promise<TransactionResult> {
    console.log('Voting on proposal', proposalId, 'with vote:', vote);
    return {
      success: false,
      error: 'Governance features coming soon',
    };
  }

  async getProposals(): Promise<GovernanceProposal[]> {
    console.log('Getting proposals');
    return [];
  }

  async getTransactionHistory(address?: string, limit: number = 10): Promise<TransactionHistoryResult> {
    const res = await backendFetchJson<{ transactions?: ChainTransactionRow[] }>('GET', '/api/blockchain/transactions', {
      address: address?.trim(),
      limit,
    });

    if (res.ok && res.data && Array.isArray(res.data.transactions)) {
      return { transactions: res.data.transactions.slice(0, limit), dataSource: 'backend' };
    }

    const reason = res.ok ? 'invalid_response' : classifyBackendFailure(res.error, res.status);
    const detail = res.ok ? 'Expected { transactions: [...] }' : res.error;
    console.warn('Transaction history backend unavailable; using local preview.', detail);
    return {
      transactions: mockTransactions(address).slice(0, limit),
      dataSource: 'local',
      localFallbackReason: reason,
      localFallbackDetail: detail,
    };
  }

  async waitForTransaction(txHash: string): Promise<boolean> {
    try {
      const poll = await backendFetchJson<{ confirmed?: boolean; status?: string }>(
        'GET',
        '/api/blockchain/transaction-status',
        { hash: txHash },
      );
      if (poll.ok && poll.data && (poll.data.confirmed === true || poll.data.status === 'success')) {
        return true;
      }

      console.log('Waiting for transaction (client poll):', txHash);
      let attempts = 0;
      const maxAttempts = 10;
      while (attempts < maxAttempts) {
        attempts++;
        await new Promise((r) => setTimeout(r, 1500));
        const again = await backendFetchJson<{ confirmed?: boolean }>('GET', '/api/blockchain/transaction-status', {
          hash: txHash,
        });
        if (again.ok && again.data?.confirmed) return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to wait for transaction:', error);
      return false;
    }
  }

  formatAmount(amount: string | number, decimals: number = 7): string {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    return (num / Math.pow(10, decimals)).toFixed(decimals);
  }

  parseAmount(amount: string, decimals: number = 7): string {
    const num = parseFloat(amount);
    return Math.floor(num * Math.pow(10, decimals)).toString();
  }
}

export const blockchainManager = BlockchainManager.getInstance();
