/**
 * WebSocket client connecting the frontend to the backend Python bridge (port 8765).
 * Supports dynamic host discovery for Tailnet / MagicDNS access.
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

export type LogListener = (message: string) => void;
export type MetricsListener = (metrics: BacktestMetrics) => void;
export type IndicatorListener = (name: string, code: string) => void;
export type SummaryListener = (text: string) => void;
export type DoneListener = () => void;
export type ConnectionListener = (connected: boolean, status: string) => void;

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

  constructor() {}

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
      type: 'generate_indicator',
      prompt: prompt,
      symbol: symbol,
      timeframe: timeframe,
      model: model,
      effort: effort,
      mode: mode,
    };

    this.ws.send(JSON.stringify(payload));
    return true;
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
