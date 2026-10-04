/**
 * Single-User Persistent Memory System for Vela Agent Workbench.
 * Persists workspace state across reloads (localStorage) and machine restarts (/api/user-state).
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
    timestamp: string;
  } | null;
}

const STORAGE_KEY = 'vela_user_memory_v1';

export class UserMemoryManager {
  private currentState: UserMemoryState;
  private backendBaseUrl: string;

  constructor(backendBaseUrl: string = '') {
    this.backendBaseUrl = backendBaseUrl;
    this.currentState = this.loadInitialLocalState();
  }

  private getDefaultState(): UserMemoryState {
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
    };
  }

  private loadInitialLocalState(): UserMemoryState {
    const defaults = this.getDefaultState();
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          ...defaults,
          ...parsed,
          selectedMarket: { ...defaults.selectedMarket, ...(parsed.selectedMarket || {}) },
          favoriteKeys: Array.isArray(parsed.favoriteKeys) ? parsed.favoriteKeys : defaults.favoriteKeys,
          activeIndicators: Array.isArray(parsed.activeIndicators) ? parsed.activeIndicators : [],
        };
      }
    } catch (e) {
      console.warn('[UserMemory] Failed to load localStorage:', e);
    }
    return defaults;
  }

  public getState(): UserMemoryState {
    return this.currentState;
  }

  public async syncFromBackend(): Promise<UserMemoryState> {
    try {
      const url = `${this.backendBaseUrl}/api/user-state`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const serverState = data.state;
        if (serverState && Object.keys(serverState).length > 0) {
          // If local storage had no active indicators or default market, adopt server state
          if (this.currentState.activeIndicators.length === 0 && Array.isArray(serverState.activeIndicators) && serverState.activeIndicators.length > 0) {
            this.currentState.activeIndicators = serverState.activeIndicators;
          }
          if (serverState.lastBacktest && !this.currentState.lastBacktest) {
            this.currentState.lastBacktest = serverState.lastBacktest;
          }
          this.saveStateLocally();
        }
      }
    } catch (e) {
      console.warn('[UserMemory] Backend sync skipped or unavailable:', e);
    }
    return this.currentState;
  }

  private saveStateLocally() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.currentState));
    } catch (e) {
      console.warn('[UserMemory] Failed to write localStorage:', e);
    }
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
      // Background save failure is non-blocking
    }
  }

  public save(partial: Partial<UserMemoryState>) {
    this.currentState = {
      ...this.currentState,
      ...partial,
      selectedMarket: partial.selectedMarket ? { ...this.currentState.selectedMarket, ...partial.selectedMarket } : this.currentState.selectedMarket,
    };
    this.saveStateLocally();
    this.pushStateToBackend();
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
          timestamp: typeof textOrData.timestamp === 'string' ? textOrData.timestamp : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      });
    } else {
      this.save({
        lastAnalysis: {
          text: textOrData,
          bias: bias,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      });
    }
  }
}
