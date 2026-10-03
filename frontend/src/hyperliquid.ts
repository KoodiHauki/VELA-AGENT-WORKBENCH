/**
 * Hyperliquid Market Data Streamer (WebSocket + REST snapshots)
 */

export interface Candle {
  openTime: number;
  closeTime?: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type CandleCallback = (candle: Candle, isNewBar: boolean) => void;
export type StatusCallback = (connected: boolean, status: string) => void;

export class HyperliquidStreamer {
  private ws: WebSocket | null = null;
  private coin: string = 'BTC';
  private interval: string = '1h';
  private onCandleCallback: CandleCallback | null = null;
  private onStatusCallback: StatusCallback | null = null;
  private reconnectTimer: number | null = null;
  private isDestroyed = false;

  constructor(coin: string = 'BTC', interval: string = '1h') {
    this.coin = this.cleanCoin(coin);
    this.interval = interval;
  }

  private cleanCoin(c: string): string {
    const upper = c.toUpperCase().trim();
    if (upper.endsWith('USDT')) return upper.slice(0, -4);
    if (upper.endsWith('USD')) return upper.slice(0, -3);
    return upper;
  }

  public setCallbacks(onCandle: CandleCallback, onStatus?: StatusCallback) {
    this.onCandleCallback = onCandle;
    if (onStatus) this.onStatusCallback = onStatus;
  }

  public setMarket(coin: string, interval: string) {
    const clean = this.cleanCoin(coin);
    if (this.coin === clean && this.interval === interval) return;
    this.coin = clean;
    this.interval = interval;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.subscribe();
    }
  }

  /**
   * Fetch initial historical bars via Hyperliquid REST
   */
  public async fetchHistoricalCandles(bars: number = 500): Promise<Candle[]> {
    try {
      this.notifyStatus(false, 'Ladataan kynttilöitä...');
      const response = await fetch('https://api.hyperliquid.xyz/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'candleSnapshot',
          req: {
            coin: this.coin,
            interval: this.interval,
            startTime: 0,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const raw = await response.json();
      if (!Array.isArray(raw)) return [];

      const slice = raw.length > bars ? raw.slice(-bars) : raw;
      const candles: Candle[] = slice.map((c: any) => ({
        openTime: Number(c.t),
        closeTime: Number(c.T || c.t + 3600000),
        open: parseFloat(c.o),
        high: parseFloat(c.h),
        low: parseFloat(c.l),
        close: parseFloat(c.c),
        volume: parseFloat(c.v),
      }));

      this.notifyStatus(true, 'Kynttilät ladattu');
      return candles;
    } catch (err) {
      console.error('Failed to fetch historical candles:', err);
      this.notifyStatus(false, 'Virhe ladattaessa kynttilöitä');
      return [];
    }
  }

  /**
   * Start live WebSocket candle subscription
   */
  public connect() {
    this.isDestroyed = false;
    if (this.ws) {
      try {
        this.ws.close();
      } catch (_) {}
    }

    const wsUrl = 'wss://api.hyperliquid.xyz/ws';
    this.notifyStatus(false, 'Yhdistetään Hyperliquidiin...');

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.notifyStatus(true, 'HL WS yhdistetty');
        this.subscribe();
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.channel === 'candle' && msg.data) {
            const d = msg.data;
            if (d.s === this.coin && d.i === this.interval) {
              const candle: Candle = {
                openTime: Number(d.t),
                closeTime: Number(d.T || d.t + 3600000),
                open: parseFloat(d.o),
                high: parseFloat(d.h),
                low: parseFloat(d.l),
                close: parseFloat(d.c),
                volume: parseFloat(d.v),
              };
              if (this.onCandleCallback) {
                this.onCandleCallback(candle, false);
              }
            }
          }
        } catch (e) {
          console.error('Error handling candle WS message:', e);
        }
      };

      this.ws.onerror = (e) => {
        console.warn('Hyperliquid WS error:', e);
        this.notifyStatus(false, 'HL yhteysvirhe');
      };

      this.ws.onclose = () => {
        this.notifyStatus(false, 'HL yhteys katkennut');
        if (!this.isDestroyed) {
          this.scheduleReconnect();
        }
      };
    } catch (err) {
      console.error('Cannot create Hyperliquid WS:', err);
      this.scheduleReconnect();
    }
  }

  private subscribe() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const subMsg = {
      method: 'subscribe',
      subscription: {
        type: 'candle',
        coin: this.coin,
        interval: this.interval,
      },
    };
    this.ws.send(JSON.stringify(subMsg));
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = window.setTimeout(() => {
      if (!this.isDestroyed) {
        this.connect();
      }
    }, 4000);
  }

  private notifyStatus(connected: boolean, status: string) {
    if (this.onStatusCallback) {
      this.onStatusCallback(connected, status);
    }
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
