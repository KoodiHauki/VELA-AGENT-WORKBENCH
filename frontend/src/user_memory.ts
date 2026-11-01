/**
 * Single-User Persistent Memory System for Vela Agent Workbench.
 * Persists workspace state across all browser sessions and machine restarts
 * via backend authority (/api/user-state) with fast local mirror (localStorage).
 */

export interface SavedActiveIndicator {
  id: string;
  name: string;
  code: string;
  visible: boolean;
}

export interface UserMemoryState {
  selectedMarket: {
    symbol: string;
    timeframe: string;
    source: string;
    displayName: string;
  };
  favoriteKeys: string[];
  activeIndicators: SavedActiveIndicator[];
  lastBacktest?: {
    strategy: string;
    metrics: any;
    summary: string;
    timestamp: number;
  } | null;
  lastAnalysis?: {
    text: string;
    bias?: string;
    symbol?: string;
    timestamp: string | number;
  } | null;
  selectedModel?: string;
  selectedMode?: string;
  terminalLogs?: string[];
}

const STORAGE_KEY = 'vela_user_memory_v1';

export class UserMemoryManager {
  private currentState: UserMemoryState;
  private backendBaseUrl: string;
  private isInitialized: boolean = false;
  private pushTimer: any = null;
  private initPromise: Promise<UserMemoryState> | null = null;

  constructor(backendBaseUrl: string = '') {
    if (!backendBaseUrl && typeof window !== 'undefined' && window.location) {
      if (window.location.protocol === 'https:' || (window.location.port !== '5173' && window.location.port !== '8765')) {
        this.backendBaseUrl = window.location.origin;
      } else {
        const host = window.location.hostname || '127.0.0.1';
        this.backendBaseUrl = `http://${host}:8765`;
      }
    } else {
      this.backendBaseUrl = backendBaseUrl;
    }
    // Synchronous immediate local fallback for instant paint
    this.currentState = this.loadInitialLocalState();
  }

  public getDefaultState(): UserMemoryState {
    return {
      selectedMarket: {
        symbol: 'BTC',
        timeframe: '1h',
        source: 'hyperliquid',
        displayName: 'BTC/USD',
      },
      favoriteKeys: ['hyperliquid:BTC', 'hyperliquid:ETH', 'hyperliquid:SOL', 'binance:BTCUSDT'],
      activeIndicators: [],
      lastBacktest: null,
      lastAnalysis: null,
      selectedModel: 'gemini-3.8-flash-high',
      selectedMode: 'auto',
      terminalLogs: [],
    };
  }

  private mergeWithDefaults(partial: any): UserMemoryState {
    const defaults = this.getDefaultState();
    if (!partial || typeof partial !== 'object') return defaults;

    return {
      selectedMarket: {
        symbol: partial.selectedMarket?.symbol || defaults.selectedMarket.symbol,
        timeframe: partial.selectedMarket?.timeframe || defaults.selectedMarket.timeframe,
        source: partial.selectedMarket?.source || defaults.selectedMarket.source,
        displayName: partial.selectedMarket?.displayName || defaults.selectedMarket.displayName,
      },
      favoriteKeys: Array.isArray(partial.favoriteKeys) && partial.favoriteKeys.length > 0
        ? partial.favoriteKeys
        : defaults.favoriteKeys,
      activeIndicators: Array.isArray(partial.activeIndicators) ? partial.activeIndicators : [],
      lastBacktest: partial.lastBacktest !== undefined ? partial.lastBacktest : defaults.lastBacktest,
      lastAnalysis: partial.lastAnalysis !== undefined ? partial.lastAnalysis : defaults.lastAnalysis,
      selectedModel: partial.selectedModel || defaults.selectedModel,
      selectedMode: partial.selectedMode || defaults.selectedMode,
      terminalLogs: Array.isArray(partial.terminalLogs) ? partial.terminalLogs : [],
    };
  }

  private loadInitialLocalState(): UserMemoryState {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          return this.mergeWithDefaults(parsed);
        }
      }
    } catch (e) {
      console.warn('[UserMemory] Failed to load localStorage:', e);
    }
    return this.getDefaultState();
  }

  /**
   * Authoritative initialization from single-user backend.
   * Ensures different browser sessions immediately load the shared state.
   */
  public async init(): Promise<UserMemoryState> {
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      try {
        const url = `${this.backendBaseUrl}/api/user-state`;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3500);

        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeout);

        if (res.ok) {
          const data = await res.json();
          if (data && data.state && Object.keys(data.state).length > 0) {
            this.currentState = this.mergeWithDefaults(data.state);
            this.saveStateLocally();
            this.isInitialized = true;
            console.log('[UserMemory] Synchronized persistent state from backend successfully.');
            return this.currentState;
          }
        }
      } catch (e) {
        console.warn('[UserMemory] Backend sync unavailable on startup, using local mirror:', e);
      }

      // If backend was empty or unreachable, use local state mirror
      this.isInitialized = true;
      return this.currentState;
    })();

    return this.initPromise;
  }

  public getState(): UserMemoryState {
    return this.currentState;
  }

  /**
   * Adopt remote state without re-pushing back to server (e.g. from WebSocket broadcast)
   */
  public adoptState(remoteState: Partial<UserMemoryState>) {
    this.currentState = this.mergeWithDefaults({
      ...this.currentState,
      ...remoteState,
    });
    this.saveStateLocally();
  }

  private saveStateLocally() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.currentState));
      }
    } catch (e) {
      console.warn('[UserMemory] Failed to write localStorage:', e);
    }
  }

  private schedulePushToBackend() {
    if (!this.isInitialized) {
      // Guard: never push empty/uninitialized defaults to the backend
      return;
    }
    if (this.pushTimer) {
      clearTimeout(this.pushTimer);
    }
    this.pushTimer = setTimeout(() => {
      this.pushStateToBackend();
    }, 250);
  }

  private async pushStateToBackend() {
    try {
      const url = `${this.backendBaseUrl}/api/user-state`;
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.currentState),
      });
    } catch (e) {
      console.warn('[UserMemory] Push to backend failed:', e);
    }
  }

  public save(partial: Partial<UserMemoryState>) {
    this.currentState = {
      ...this.currentState,
      ...partial,
      selectedMarket: partial.selectedMarket
        ? { ...this.currentState.selectedMarket, ...partial.selectedMarket }
        : this.currentState.selectedMarket,
    };
    this.saveStateLocally();
    this.schedulePushToBackend();
  }

  public setMarket(symbol: string, timeframe: string, source: string, displayName: string) {
    this.save({
      selectedMarket: { symbol, timeframe, source, displayName },
    });
  }

  public setFavorites(favoriteKeys: string[]) {
    this.save({ favoriteKeys });
  }

  public setActiveIndicators(activeIndicators: SavedActiveIndicator[]) {
    this.save({ activeIndicators });
  }

  public setModel(selectedModel: string) {
    this.save({ selectedModel });
  }

  public setMode(selectedMode: string) {
    this.save({ selectedMode });
  }

  public appendTerminalLog(logMessage: string) {
    const logs = [...(this.currentState.terminalLogs || [])];
    logs.push(logMessage);
    // Keep last 40 lines
    if (logs.length > 40) {
      logs.splice(0, logs.length - 40);
    }
    this.currentState.terminalLogs = logs;
    this.saveStateLocally();
    this.schedulePushToBackend();
  }

  public clearTerminalLogs() {
    this.save({ terminalLogs: [] });
  }

  public setLastBacktest(
    strategyOrData: string | { strategy?: string; symbol?: string; timeframe?: string; source?: string; metrics?: any; summary?: string; timestamp?: number },
    metrics?: any,
    summary?: string
  ) {
    if (typeof strategyOrData === 'object' && strategyOrData !== null) {
      this.save({
        lastBacktest: {
          strategy: strategyOrData.strategy || `${strategyOrData.symbol || 'BTC'} (${strategyOrData.timeframe || '1h'})`,
          metrics: strategyOrData.metrics || {},
          summary: strategyOrData.summary || '',
          timestamp: strategyOrData.timestamp || Date.now(),
        },
      });
    } else {
      this.save({
        lastBacktest: {
          strategy: strategyOrData || 'Manual Backtest',
          metrics: metrics || {},
          summary: summary || '',
          timestamp: Date.now(),
        },
      });
    }
  }

  public setLastAnalysis(
    textOrData: string | { text: string; bias?: string; symbol?: string; timestamp?: any },
    bias?: string
  ) {
    if (typeof textOrData === 'object' && textOrData !== null) {
      this.save({
        lastAnalysis: {
          text: textOrData.text,
          bias: textOrData.bias,
          symbol: textOrData.symbol,
          timestamp: typeof textOrData.timestamp === 'string' ? textOrData.timestamp : (textOrData.timestamp || Date.now()),
        },
      });
    } else {
      this.save({
        lastAnalysis: {
          text: textOrData,
          bias: bias,
          timestamp: Date.now(),
        },
      });
    }
  }
}
