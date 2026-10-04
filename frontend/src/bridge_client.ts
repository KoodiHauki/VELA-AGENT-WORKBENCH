/**
 * WebSocket & HTTP client connecting the frontend to the backend Python bridge (port 8765).
 * Supports dynamic host discovery for Tailnet / MagicDNS access, multi-indicator
 * analysis queries, indicator storage, and historical archive downloads.
 */

export interface BacktestMetrics {
  strategy?: string;
  trades_count: number;
  win_rate: number;
  winning_trades?: number;
  losing_trades?: number;
  avg_return_pct: number;
  total_return_pct?: number;
  profit_factor: number;
  max_drawdown_pct: number;
  summary: string;
}

export interface SavedIndicator {
  id: string;
  name: string;
  description?: string;
  category?: string;
  author?: string;
  createdAt?: number;
  code: string;
}

export interface TradingSymbol {
  symbol: string;
  pair: string;
  base: string;
  quote: string;
  source: 'hyperliquid' | 'binance';
  maxLeverage?: number;
}


export type LogListener = (message: string) => void;
export type MetricsListener = (metrics: BacktestMetrics) => void;
export type IndicatorListener = (name: string, code: string) => void;
export type SummaryListener = (text: string) => void;
export type DoneListener = () => void;
export type ConnectionListener = (connected: boolean, status: string) => void;
export type ChartAnalysisListener = (analysis: { text: string; bias?: string }) => void;

export class BridgeClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private isDestroyed = false;

  public onLog: LogListener | null = null;
  public onMetrics: MetricsListener | null = null;
  public onRenderIndicator: IndicatorListener | null = null;
  public onSummary: SummaryListener | null = null;
  public onDone: DoneListener | null = null;
  public onConnectionChange: ConnectionListener | null = null;
  public onChartAnalysis: ChartAnalysisListener | null = null;

  constructor() {}

  public getHttpBaseUrl(): string {
    const host = window.location.hostname || '127.0.0.1';
    const port = 8765;
    return `http://${host}:${port}`;
  }

  private getBridgeUrl(): string {
    const host = window.location.hostname || '127.0.0.1';
    const port = 8765;
    return `ws://${host}:${port}/ws`;
  }

  public connect() {
    this.isDestroyed = false;
    if (this.ws) {
      try {
        this.ws.close();
      } catch (_) {}
    }

    const url = this.getBridgeUrl();
    this.notifyConnection(false, `Yhdistetään siltaan (${url})...`);

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.notifyConnection(true, 'Silta yhdistetty (Portti 8765)');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type;

          if (type === 'log') {
            if (this.onLog) this.onLog(data.message || '');
          } else if (type === 'metrics') {
            if (this.onMetrics) this.onMetrics(data.data as BacktestMetrics);
          } else if (type === 'render_indicator') {
            if (this.onRenderIndicator) this.onRenderIndicator(data.name || 'Custom Indicator', data.code || '');
          } else if (type === 'summary') {
            if (this.onSummary) this.onSummary(data.text || '');
          } else if (type === 'chart_analysis') {
            if (this.onChartAnalysis) this.onChartAnalysis({ text: data.text || '', bias: data.bias });
          } else if (type === 'done') {
            if (this.onDone) this.onDone();
          } else if (type === 'error') {
            if (this.onLog) this.onLog(`[Virhe] ${data.message || 'Tuntematon virhe'}`);
          }
        } catch (err) {
          console.error('[BridgeClient] Failed to parse message:', event.data, err);
        }
      };

      this.ws.onerror = (e) => {
        console.warn('[BridgeClient] WebSocket error:', e);
        this.notifyConnection(false, 'Siltayhteysvirhe');
      };

      this.ws.onclose = () => {
        this.notifyConnection(false, 'Silta ei yhteydessä');
        if (!this.isDestroyed) {
          this.scheduleReconnect();
        }
      };
    } catch (err) {
      console.error('[BridgeClient] Connection creation failed:', err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = window.setTimeout(() => {
      if (!this.isDestroyed) {
        this.connect();
      }
    }, 3000);
  }

  private notifyConnection(connected: boolean, status: string) {
    if (this.onConnectionChange) {
      this.onConnectionChange(connected, status);
    }
  }

  public sendPrompt(
    prompt: string,
    symbol: string = 'BTC',
    timeframe: string = '1h',
    model: string = 'gemini-3.8-flash-high',
    effort: string = 'high',
    mode: string = 'auto',
    source: string = 'hyperliquid'
  ): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      if (this.onLog) {
        this.onLog('[Virhe] Siltayhteys ei ole aktiivinen. Yritetään yhdistää uudelleen...');
      }
      this.connect();
      return false;
    }

    const payload = {
      type: 'generate_indicator',
      prompt: prompt,
      symbol: symbol,
      timeframe: timeframe,
      model: model,
      effort: effort,
      mode: mode,
      source: source,
    };

    this.ws.send(JSON.stringify(payload));
    return true;
  }

  public askAboutChart(
    question: string,
    snapshot: any,
    model: string = 'gemini-3.8-flash-high',
    effort: string = 'high',
    mode: string = 'auto'
  ): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      if (this.onLog) {
        this.onLog('[Virhe] Siltayhteys ei ole aktiivinen. Yritetään yhdistää uudelleen...');
      }
      this.connect();
      return false;
    }

    const payload = {
      type: 'analyze_chart',
      question,
      snapshot,
      model,
      effort,
      mode,
    };

    this.ws.send(JSON.stringify(payload));
    return true;
  }

  // REST API methods for Saved Indicators & Historical Archives
  public async getIndicators(): Promise<SavedIndicator[]> {
    try {
      const res = await fetch(`${this.getHttpBaseUrl()}/api/indicators`);
      if (res.ok) {
        const data = await res.json();
        return data.indicators || [];
      }
    } catch (e) {
      console.warn('[BridgeClient] Failed to fetch saved indicators:', e);
    }
    return [];
  }

  public async saveIndicator(ind: Partial<SavedIndicator>): Promise<SavedIndicator | null> {
    try {
      const res = await fetch(`${this.getHttpBaseUrl()}/api/indicators`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ind),
      });
      if (res.ok) {
        const data = await res.json();
        return data.indicator;
      }
    } catch (e) {
      console.error('[BridgeClient] Failed to save indicator:', e);
    }
    return null;
  }

  public async deleteIndicator(id: string): Promise<boolean> {
    try {
      const res = await fetch(`${this.getHttpBaseUrl()}/api/indicators/${id}`, {
        method: 'DELETE',
      });
      return res.ok;
    } catch (e) {
      console.error('[BridgeClient] Failed to delete indicator:', e);
      return false;
    }
  }

  public async getSymbols(source: string = 'all', refresh: boolean = false): Promise<TradingSymbol[]> {
    try {
      const res = await fetch(`${this.getHttpBaseUrl()}/api/symbols?source=${source}&refresh=${refresh}`);
      if (res.ok) {
        const data = await res.json();
        return data.symbols || [];
      }
    } catch (e) {
      console.warn('[BridgeClient] Failed to fetch symbols:', e);
    }
    return [];
  }


  public async getHistoricalArchives(): Promise<{ archives: any[]; free_resources: any }> {
    try {
      const res = await fetch(`${this.getHttpBaseUrl()}/api/historical/list`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('[BridgeClient] Failed to fetch historical archives list:', e);
    }
    return { archives: [], free_resources: {} };
  }

  public async downloadHistorical(params: {
    symbol: string;
    interval: string;
    start_year: number;
    start_month: number;
    end_year: number;
    end_month: number;
  }): Promise<any> {
    try {
      const res = await fetch(`${this.getHttpBaseUrl()}/api/historical/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error('[BridgeClient] Failed to trigger historical download:', e);
    }
    return { status: 'error', error: 'Verkkovirhe tai yhteysongelma' };
  }

  public destroy() {
    this.isDestroyed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      try {
        this.ws.close();
      } catch (_) {}
      this.ws = null;
    }
  }
}
