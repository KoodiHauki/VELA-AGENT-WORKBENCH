/**
 * Vela WebGL2 Chart Manager & PineTS Engine Driver
 */

import { Vela } from '@luxalgo/vela';
import { PineWorkerEngine, PineEngine } from '@luxalgo/vela-pinets';
import { HyperliquidProvider } from '@luxalgo/vela/providers/hyperliquid';

export interface ChartStatus {
  symbol: string;
  timeframe: string;
  indicatorsCount: number;
}

export class VelaChartManager {
  private container: HTMLElement;
  public chart: Vela | null = null;
  private currentSymbol: string = 'BTC';
  private currentTimeframe: string = '60'; // in minutes or timeframe string
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

  /**
   * Convert interval string (1m, 5m, 15m, 1h, 4h, 1d) to minutes/format expected by Vela
   */
  private formatTimeframe(tf: string): string {
    const map: Record<string, string> = {
      '1m': '1',
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

  public init(symbol: string = 'BTC', timeframe: string = '1h') {
    this.currentSymbol = symbol;
    this.currentTimeframe = this.formatTimeframe(timeframe);

    try {
      this.chart = new Vela(this.container, {
        symbol: this.currentSymbol,
        timeframe: this.currentTimeframe,
        live: true,
      });

      try {
        const provider = new HyperliquidProvider();
        this.chart.data.registerProvider('hyperliquid', provider);
      } catch (provErr) {
        console.warn('[Vela] HyperliquidProvider registration warning:', provErr);
      }

      // Register PineTS execution engine (worker preferred, fallback to sync engine)
      try {
        this.chart.registerEngine('pine', new PineWorkerEngine());
        console.log('[Vela] Registered PineWorkerEngine successfully.');
      } catch (workerErr) {
        console.warn('[Vela] Worker engine registration failed, using PineEngine:', workerErr);
        this.chart.registerEngine('pine', new PineEngine());
      }

      // Add resize observer for responsive chart resizing
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

  public async setMarket(symbol: string, timeframe: string) {
    this.currentSymbol = symbol;
    this.currentTimeframe = this.formatTimeframe(timeframe);

    if (this.chart) {
      try {
        await this.chart.setMarket({
          symbol: this.currentSymbol,
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
      
      // Use runIndicator for safe evaluation and injection
      if (typeof this.chart.runIndicator === 'function') {
        const handle = await this.chart.runIndicator(code);
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
      console.error('[Vela] Indicator injection failed:', err);
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
