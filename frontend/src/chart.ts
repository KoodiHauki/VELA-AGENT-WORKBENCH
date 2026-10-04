/**
 * Vela WebGL2 Chart Manager & PineTS Engine Driver
 * Supports MultiProviderFeed (Hyperliquid & Binance), multiple active indicators,
 * weekly/monthly intervals, and chart state snapshots.
 */

import { Vela, MultiProviderFeed } from '@luxalgo/vela';
import { PineWorkerEngine, PineEngine } from '@luxalgo/vela-pinets';
import { HyperliquidProvider } from '@luxalgo/vela/providers/hyperliquid';
import { BinanceProvider } from '@luxalgo/vela/providers/binance';

export interface ActiveIndicatorItem {
  id: string;
  name: string;
  code: string;
  handle: any;
  visible: boolean;
  addedAt: number;
}

export interface ChartContextSnapshot {
  symbol: string;
  timeframe: string;
  source: string;
  activeIndicators: { id: string; name: string; visible: boolean; code: string }[];
}

export class ArchiveProvider {
  async getBars(ticker: string, timeframe: string, _range?: any): Promise<any[]> {
    try {
      const host = window.location.hostname || '127.0.0.1';
      const port = 8765;
      let url = `http://${host}:${port}/api/candles?source=archive&timeframe=${encodeURIComponent(timeframe)}`;
      if (ticker.endsWith('.csv')) {
        url += `&file=${encodeURIComponent(ticker)}`;
      } else {
        url += `&symbol=${encodeURIComponent(ticker)}`;
      }
      const res = await fetch(url);
      if (!res.ok) return [];
      const data = await res.json();
      return (data.candles || []).map((c: any) => ({
        time: Number(c.openTime || c.time),
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
        volume: Number(c.volume || 0),
      }));
    } catch (e) {
      console.warn('[ArchiveProvider] Failed to fetch candles:', e);
      return [];
    }
  }
}

export class VelaChartManager {
  private container: HTMLElement;
  public chart: Vela | null = null;
  private currentSymbol: string = 'BTC';
  private currentTimeframe: string = '60';
  private currentSource: string = 'hyperliquid';
  private activeIndicatorsMap: Map<string, ActiveIndicatorItem> = new Map();
  public onActiveIndicatorsChange: ((indicators: ActiveIndicatorItem[]) => void) | null = null;

  constructor(container: HTMLElement | string) {
    if (typeof container === 'string') {
      const el = document.querySelector(container) as HTMLElement;
      if (!el) throw new Error(`Container element not found: ${container}`);
      this.container = el;
    } else {
      this.container = container;
    }
  }

  private cleanSymbol(s: string, source: string = 'hyperliquid'): string {
    let clean = s.trim();
    if (clean.includes(':')) {
      clean = clean.split(':', 2)[1];
    }
    const src = source.toLowerCase();
    if (src === 'archive') {
      return `ARCHIVE:${clean}`;
    }
    const upper = clean.toUpperCase();
    let symbolOnly = upper;
    if (symbolOnly.endsWith('USDT') && symbolOnly.length > 4) symbolOnly = symbolOnly.slice(0, -4);
    if (symbolOnly.endsWith('USD') && symbolOnly.length > 3) symbolOnly = symbolOnly.slice(0, -3);

    if (src === 'binance') {
      return `BINANCE:${symbolOnly}USDT`;
    }
    return `HYPERLIQUID:${symbolOnly}`;
  }

  private formatTimeframe(tf: string): string {
    const map: Record<string, string> = {
      '1m': '1',
      '3m': '3',
      '5m': '5',
      '15m': '15',
      '30m': '30',
      '1h': '60',
      '4h': '240',
      '1d': 'D',
      '1w': 'W',
      '1M': 'M',
      '60': '60',
      '240': '240',
      'D': 'D',
      'W': 'W',
      'M': 'M',
      'w': 'W',
      'm': 'M',
    };
    return map[tf] || tf;
  }

  public init(symbol: string = 'BTC', timeframe: string = '1h', source: string = 'hyperliquid') {
    this.currentSymbol = symbol;
    this.currentTimeframe = this.formatTimeframe(timeframe);
    this.currentSource = source.toLowerCase();

    try {
      // 1. Create MultiProviderFeed with Hyperliquid, Binance, and Archive providers
      const feed = new MultiProviderFeed();
      feed.registerProvider('hyperliquid', new HyperliquidProvider());
      feed.registerProvider('binance', new BinanceProvider());
      feed.registerProvider('archive', new ArchiveProvider() as any);

      // 2. Initialize Vela instance with feed in deps
      this.chart = new Vela(
        this.container,
        {
          symbol: this.cleanSymbol(this.currentSymbol, this.currentSource),
          timeframe: this.currentTimeframe,
          live: true,
          theme: 'dark',
          defaultLanguage: 'pine',
        },
        {
          dataFeed: feed,
        }
      );


      // 3. Register PineTS execution engine (worker preferred, fallback to sync engine)
      try {
        this.chart.registerEngine('pine', new PineWorkerEngine());
        console.log('[Vela] Registered PineWorkerEngine successfully.');
      } catch (workerErr) {
        console.warn('[Vela] Worker engine registration failed, using PineEngine:', workerErr);
        this.chart.registerEngine('pine', new PineEngine());
      }

      // 4. Resize observer for responsive layout
      const ro = new ResizeObserver(() => {
        if (this.chart) {
          this.chart.resize();
        }
      });
      ro.observe(this.container);

    } catch (err) {
      console.error('[Vela] Initialization error:', err);
      throw err;
    }
  }

  public async setMarket(symbol: string, timeframe: string, source?: string) {
    this.currentSymbol = symbol;
    this.currentTimeframe = this.formatTimeframe(timeframe);
    if (source) {
      this.currentSource = source.toLowerCase();
    }

    if (this.chart) {
      try {
        await this.chart.setMarket({
          symbol: this.cleanSymbol(this.currentSymbol, this.currentSource),
          timeframe: this.currentTimeframe,
        });
      } catch (err) {
        console.error('[Vela] Error changing market:', err);
      }
    }
  }

  public async loadArchiveData(filenameOrSymbol: string, timeframe: string = '1h') {
    await this.setMarket(filenameOrSymbol, timeframe, 'archive');
  }


  private notifyIndicatorsChanged() {
    if (this.onActiveIndicatorsChange) {
      this.onActiveIndicatorsChange(this.getActiveIndicatorsList());
    }
  }

  /**
   * Inject and run a validated Pine Script indicator on the live chart.
   * Supports multiple concurrent indicators without removing existing ones.
   */
  public async injectIndicator(code: string, name: string = 'Custom Indicator'): Promise<{ success: boolean; id?: string; error?: string }> {
    if (!this.chart) {
      return { success: false, error: 'Vela-kaavio ei ole vielä alustettu.' };
    }

    try {
      console.log(`[Vela] Injektoidaan indikaattori: "${name}"...`);
      const id = 'ind_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
      let handle: any = null;

      // Prefer runIndicator for safe evaluation and structured error return
      if (typeof this.chart.runIndicator === 'function') {
        const result: any = await this.chart.runIndicator(code);
        if (result && result.ok === false) {
          const errDetail = result.error?.message || String(result.error || 'Tuntematon virhe');
          console.warn('[Vela] runIndicator reported ok=false:', errDetail);
          return { success: false, error: errDetail };
        }
        handle = result?.handle || result;
      } else if (typeof this.chart.addIndicator === 'function') {
        handle = await this.chart.addIndicator(code);
      } else {
        throw new Error('Vela chart does not support indicator injection methods.');
      }

      const item: ActiveIndicatorItem = {
        id,
        name,
        code,
        handle,
        visible: true,
        addedAt: Date.now(),
      };

      this.activeIndicatorsMap.set(id, item);
      this.notifyIndicatorsChanged();
      return { success: true, id };
    } catch (err: any) {
      console.error('[Vela] Indicator injection failed with exception:', err);
      return {
        success: false,
        error: err.message || String(err),
      };
    }
  }

  /**
   * Toggle visibility of an active indicator (hide/show)
   */
  public toggleIndicatorVisibility(id: string): boolean {
    const item = this.activeIndicatorsMap.get(id);
    if (!item) return false;

    item.visible = !item.visible;
    if (item.handle && typeof item.handle.setVisible === 'function') {
      try {
        item.handle.setVisible(item.visible);
      } catch (e) {
        console.warn(`[Vela] Failed to toggle visibility for ${id}:`, e);
      }
    }
    this.notifyIndicatorsChanged();
    return item.visible;
  }

  /**
   * Remove a specific indicator from the chart
   */
  public removeIndicator(id: string): boolean {
    const item = this.activeIndicatorsMap.get(id);
    if (!item) return false;

    if (item.handle && typeof item.handle.remove === 'function') {
      try {
        item.handle.remove();
      } catch (e) {
        console.warn(`[Vela] Error calling handle.remove() for ${id}:`, e);
      }
    }
    this.activeIndicatorsMap.delete(id);
    this.notifyIndicatorsChanged();
    return true;
  }

  /**
   * Remove all active indicators from the chart
   */
  public clearAllIndicators(): void {
    for (const item of this.activeIndicatorsMap.values()) {
      if (item.handle && typeof item.handle.remove === 'function') {
        try {
          item.handle.remove();
        } catch (_) {}
      }
    }
    this.activeIndicatorsMap.clear();
    this.notifyIndicatorsChanged();
  }

  public getActiveIndicatorsList(): ActiveIndicatorItem[] {
    return Array.from(this.activeIndicatorsMap.values());
  }

  /**
   * Backwards compatible name list
   */
  public getActiveIndicators(): string[] {
    return Array.from(this.activeIndicatorsMap.values()).map((i) => i.name);
  }

  /**
   * Get complete context snapshot of the chart for LLM technical analysis query
   */
  public getChartContextSnapshot(): ChartContextSnapshot {
    return {
      symbol: this.currentSymbol,
      timeframe: this.currentTimeframe,
      source: this.currentSource,
      activeIndicators: this.getActiveIndicatorsList().map((i) => ({
        id: i.id,
        name: i.name,
        visible: i.visible,
        code: i.code,
      })),
    };
  }

  public resize() {
    if (this.chart) {
      this.chart.resize();
    }
  }

  public destroy() {
    this.clearAllIndicators();
    if (this.chart) {
      try {
        this.chart.destroy();
      } catch (_) {}
      this.chart = null;
    }
  }
}
