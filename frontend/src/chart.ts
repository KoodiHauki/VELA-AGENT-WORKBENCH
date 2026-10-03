/**
 * Vela WebGL2 Chart Manager & PineTS Engine Driver
 */

import { Vela, MultiProviderFeed } from '@luxalgo/vela';
import { PineWorkerEngine, PineEngine } from '@luxalgo/vela-pinets';
import { HyperliquidProvider } from '@luxalgo/vela/providers/hyperliquid';
import { BinanceProvider } from '@luxalgo/vela/providers/binance';

export class VelaChartManager {
  private container: HTMLElement;
  public chart: Vela | null = null;
  private currentSymbol: string = 'BTC';
  private currentTimeframe: string = '60';
  private currentSource: string = 'hyperliquid';
  private activeIndicators: string[] = [];

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
    let clean = s.toUpperCase().trim();
    if (clean.includes(':')) {
      clean = clean.split(':', 2)[1];
    }
    if (clean.endsWith('USDT') && clean.length > 4) clean = clean.slice(0, -4);
    if (clean.endsWith('USD') && clean.length > 3) clean = clean.slice(0, -3);

    if (source.toLowerCase() === 'binance') {
      return `BINANCE:${clean}USDT`;
    }
    return `HYPERLIQUID:${clean}`;
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
      '60': '60',
      '240': '240',
      'D': 'D',
    };
    return map[tf] || tf;
  }

  public init(symbol: string = 'BTC', timeframe: string = '1h', source: string = 'hyperliquid') {
    this.currentSymbol = symbol;
    this.currentTimeframe = this.formatTimeframe(timeframe);
    this.currentSource = source.toLowerCase();

    try {
      // 1. Create MultiProviderFeed with both Hyperliquid and Binance providers
      const feed = new MultiProviderFeed();
      feed.registerProvider('hyperliquid', new HyperliquidProvider());
      feed.registerProvider('binance', new BinanceProvider());

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

  /**
   * Inject and run a validated Pine Script indicator on the live chart
   */
  public async injectIndicator(code: string, name: string = 'Custom Indicator'): Promise<{ success: boolean; error?: string }> {
    if (!this.chart) {
      return { success: false, error: 'Vela-kaavio ei ole vielä alustettu.' };
    }

    try {
      console.log(`[Vela] Injektoidaan indikaattori: "${name}"...`);
      
      // Prefer runIndicator for safe evaluation and structured error return
      if (typeof this.chart.runIndicator === 'function') {
        const result: any = await this.chart.runIndicator(code);
        if (result && result.ok === false) {
          const errDetail = result.error?.message || String(result.error || 'Tuntematon virhe');
          console.warn('[Vela] runIndicator reported ok=false:', errDetail);
          return { success: false, error: errDetail };
        }
        this.activeIndicators.push(name);
        return { success: true };
      } else if (typeof this.chart.addIndicator === 'function') {
        await this.chart.addIndicator(code);
        this.activeIndicators.push(name);
        return { success: true };
      } else {
        throw new Error('Vela chart does not support indicator injection methods.');
      }
    } catch (err: any) {
      console.error('[Vela] Indicator injection failed with exception:', err);
      return {
        success: false,
        error: err.message || String(err),
      };
    }
  }

  public getActiveIndicators(): string[] {
    return [...this.activeIndicators];
  }

  public resize() {
    if (this.chart) {
      this.chart.resize();
    }
  }

  public destroy() {
    if (this.chart) {
      try {
        this.chart.destroy();
      } catch (_) {}
      this.chart = null;
    }
  }
}
