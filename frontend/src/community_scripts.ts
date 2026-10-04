/**
 * Curated TradingView Community Scripts Library
 * Open-source Pine Script v5 indicators tested for Vela WebGL2 & PineTS.
 */

export interface CommunityScript {
  id: string;
  name: string;
  author: string;
  category: 'Trendi' | 'Oskillaattorit' | 'Volatiliteetti' | 'Hintatoiminta';
  overlay: boolean;
  description: string;
  code: string;
}

export const COMMUNITY_SCRIPTS: CommunityScript[] = [
  {
    id: 'cs_supertrend',
    name: 'SuperTrend',
    author: 'Olivier Seban / KivancOzbilgic',
    category: 'Trendi',
    overlay: true,
    description: 'Yksi maailman suosituimmista trendiseuraajista. ATR-pohjainen trailing stop -linja, joka vaihtaa väriä trendin kääntyessä.',
    code: `//@version=5
indicator("SuperTrend", overlay=true)

atr_len = input.int(10, "ATR Length")
factor = input.float(3.0, "Factor", step=0.1)

[supertrend, direction] = ta.supertrend(factor, atr_len)

body_middle = plot((open + close) / 2, display=display.none)
up_trend = plot(direction < 0 ? supertrend : na, "Up Trend", color=color.green, style=plot.style_linebr)
down_trend = plot(direction < 0 ? na : supertrend, "Down Trend", color=color.red, style=plot.style_linebr)

fill(body_middle, up_trend, color.new(color.green, 90), fillgaps=false)
fill(body_middle, down_trend, color.new(color.red, 90), fillgaps=false)
`,
  },
  {
    id: 'cs_squeeze_momentum',
    name: 'Squeeze Momentum Indicator',
    author: 'LazyBear',
    category: 'Oskillaattorit',
    overlay: false,
    description: 'John Carterin kuuluisa TTM Squeeze -klooni. Tunnistaa volatiliteetin puristustilat (Bollinger vs. Keltner) ja momentumin vapautumisen.',
    code: `//@version=5
indicator("Squeeze Momentum Indicator", overlay=false)

bb_len = input.int(20, "BB Length")
bb_mult = input.float(2.0, "BB MultFactor")
kc_len = input.int(20, "KC Length")
kc_mult = input.float(1.5, "KC MultFactor")

// Bollinger Bands
basis = ta.sma(close, bb_len)
dev = bb_mult * ta.stdev(close, bb_len)
upper_bb = basis + dev
lower_bb = basis - dev

// Keltner Channel
ma = ta.sma(close, kc_len)
range_ma = ta.ema(ta.tr, kc_len)
upper_kc = ma + range_ma * kc_mult
lower_kc = ma - range_ma * kc_mult

sqz_on = (lower_bb > lower_kc) and (upper_bb < upper_kc)
sqz_off = (lower_bb < lower_kc) and (upper_bb > upper_kc)
no_sqz = not sqz_on and not sqz_off

// Momentum linear regression
val = ta.linreg(close - math.avg(math.avg(ta.highest(high, kc_len), ta.lowest(low, kc_len)), ta.sma(close, kc_len)), kc_len, 0)

b_color = val > 0 ? (val > nz(val[1]) ? color.lime : color.green) : (val < nz(val[1]) ? color.red : color.maroon)
sc_color = no_sqz ? color.blue : (sqz_on ? color.black : color.gray)

plot(val, color=b_color, style=plot.style_columns, linewidth=2, title="Momentum")
plot(0, color=sc_color, style=plot.style_circles, linewidth=2, title="Squeeze Dot")
`,
  },
  {
    id: 'cs_wavetrend',
    name: 'WaveTrend Oscillator',
    author: 'LazyBear',
    category: 'Oskillaattorit',
    overlay: false,
    description: 'Tehokas syklisen momentumin oskillaattori. Tunnistaa ylimyydyt pohjat ja yliostetut huiput nopeilla risteyssignaaleilla.',
    code: `//@version=5
indicator("WaveTrend Oscillator", overlay=false)

n1 = input.int(10, "Channel Length")
n2 = input.int(21, "Average Length")
ob_level = input.int(60, "Overbought Level")
os_level = input.int(-60, "Oversold Level")

ap = hlc3
esa = ta.ema(ap, n1)
d = ta.ema(math.abs(ap - esa), n1)
ci = (ap - esa) / (0.015 * d)
tci = ta.ema(ci, n2)

wt1 = tci
wt2 = ta.sma(wt1, 4)

plot(0, color=color.gray, title="Zero Line")
plot(ob_level, color=color.red, linestyle=plot.style_line, title="Overbought")
plot(os_level, color=color.green, linestyle=plot.style_line, title="Oversold")

plot(wt1, color=color.green, linewidth=2, title="WT1")
plot(wt2, color=color.red, linewidth=1, style=plot.style_line, title="WT2")
plot(wt1 - wt2, color=color.new(color.blue, 70), style=plot.style_area, title="Histogram")
`,
  },
  {
    id: 'cs_hull_suite',
    name: 'Hull Suite (HMA / EHMA)',
    author: 'InSilico',
    category: 'Trendi',
    overlay: true,
    description: 'Nopeasti reagoiva Hull Moving Average -trendinauha, joka minimoi viiveen säilyttäen silti pehmeän suodatuksen.',
    code: `//@version=5
indicator("Hull Suite", overlay=true)

src = input(close, "Source")
length = input.int(55, "Length")

// Hull Moving Average calculation
hma(s, l) =>
    ta.wma(2 * ta.wma(s, math.floor(l / 2)) - ta.wma(s, l), math.floor(math.sqrt(l)))

hull = hma(src, length)
c_hull = hull > hull[1] ? color.new(#00e676, 0) : color.new(#ff1744, 0)

plot(hull, title="Hull MA", color=c_hull, linewidth=3)
`,
  },
  {
    id: 'cs_chandelier_exit',
    name: 'Chandelier Exit',
    author: 'Everget',
    category: 'Trendi',
    overlay: true,
    description: 'Charles LeBoun kehittämä ATR-pohjainen suojapysäytys. Seuraa korkeimpia huippuja nousutrendissä ja alimpia pohjia laskutrendissä.',
    code: `//@version=5
indicator("Chandelier Exit", overlay=true)

length = input.int(22, "ATR Period")
mult = input.float(3.0, "ATR Multiplier")

atr = mult * ta.atr(length)
long_stop = ta.highest(high, length) - atr
short_stop = ta.lowest(low, length) + atr

plot(long_stop, "Long Stop", color=color.green, style=plot.style_linebr, linewidth=2)
plot(short_stop, "Short Stop", color=color.red, style=plot.style_linebr, linewidth=2)
`,
  },
  {
    id: 'cs_vwap_bands',
    name: 'VWAP with StDev Bands',
    author: 'TradingView Community',
    category: 'Hintatoiminta',
    overlay: true,
    description: 'Volyymipainotettu keskihinta (VWAP) sekä 1.0 ja 2.0 keskihajonnan standardipoikkeamavyöhykkeet institutionaalisille tasoille.',
    code: `//@version=5
indicator("VWAP with StDev Bands", overlay=true)

vwap_val = ta.vwap(close)
dev = ta.stdev(close, 20)

plot(vwap_val, "VWAP", color=color.orange, linewidth=2)
plot(vwap_val + dev, "Upper Band 1", color=color.new(color.blue, 30))
plot(vwap_val - dev, "Lower Band 1", color=color.new(color.blue, 30))
plot(vwap_val + (dev * 2), "Upper Band 2", color=color.new(color.purple, 30))
plot(vwap_val - (dev * 2), "Lower Band 2", color=color.new(color.purple, 30))
`,
  },
  {
    id: 'cs_rsi_divergence',
    name: 'RSI Divergence Detector',
    author: 'TradingView Community',
    category: 'Oskillaattorit',
    overlay: false,
    description: 'RSI 14 oskillaattori huippujen ja pohjien automaattisella divergenssitunnistuksella (bullish / bearish käännesignaalit).',
    code: `//@version=5
indicator("RSI Divergence Detector", overlay=false)

len = input.int(14, "RSI Length")
r = ta.rsi(close, len)

plot(r, "RSI", color=color.purple, linewidth=2)
hline(70, "Overbought", color=color.red, linestyle=hline.style_dashed)
hline(30, "Oversold", color=color.green, linestyle=hline.style_dashed)
hline(50, "Midline", color=color.gray, linestyle=hline.style_dotted)

bull_div = (close < close[5]) and (r > r[5]) and (r < 35)
bear_div = (close > close[5]) and (r < r[5]) and (r > 65)

plotshape(bull_div, "Bullish Divergence", style=shape.triangleup, location=location.bottom, color=color.green, size=size.small)
plotshape(bear_div, "Bearish Divergence", style=shape.triangledown, location=location.top, color=color.red, size=size.small)
`,
  },
  {
    id: 'cs_ema_ribbon',
    name: 'EMA Ribbon / Cloud (4 EMAs)',
    author: 'TradingView Community',
    category: 'Trendi',
    overlay: true,
    description: 'Moniaikajänteinen liukuvien keskiarvojen nauha (EMA 20, 50, 100, 200) trendin vahvuuden ja suunnan nopeaan visuaaliseen hahmottamiseen.',
    code: `//@version=5
indicator("EMA Ribbon Cloud", overlay=true)

e20 = ta.ema(close, 20)
e50 = ta.ema(close, 50)
e100 = ta.ema(close, 100)
e200 = ta.ema(close, 200)

plot(e20, "EMA 20", color=color.yellow, linewidth=1)
plot(e50, "EMA 50", color=color.orange, linewidth=2)
plot(e100, "EMA 100", color=color.blue, linewidth=2)
plot(e200, "EMA 200", color=color.purple, linewidth=3)
`,
  },
  {
    id: 'cs_donchian_breakout',
    name: 'Donchian Breakout 20',
    author: 'Richard Donchian / Turtle Traders',
    category: 'Volatiliteetti',
    overlay: true,
    description: 'Legendaarinen Turtle Traders -kanavastrategia. Seuraa 20 kynttilän ylimpiä ja alimpia ääripisteitä ja kanavan keskipistettä.',
    code: `//@version=5
indicator("Donchian Breakout 20", overlay=true)

len = input.int(20, "Lookback")
up = ta.highest(high, len)
dn = ta.lowest(low, len)
mid = (up + dn) / 2

p_up = plot(up, "Channel High", color=color.teal, linewidth=2)
p_dn = plot(dn, "Channel Low", color=color.maroon, linewidth=2)
plot(mid, "Midline", color=color.gray, linestyle=plot.style_line)
fill(p_up, p_dn, color=color.new(color.teal, 95))
`,
  },
  {
    id: 'cs_macd_4c',
    name: 'MACD 4-Color Histogram',
    author: 'Gerald Appel',
    category: 'Oskillaattorit',
    overlay: false,
    description: 'Klassinen MACD (12, 26, 9) nelivärisellä histogrammilla, joka erottaa vahvistuvan ja heikkenevän momentumin nousu- ja laskutrendeissä.',
    code: `//@version=5
indicator("MACD 4-Color Histogram", overlay=false)

fast_len = input.int(12, "Fast Length")
slow_len = input.int(26, "Slow Length")
sig_len = input.int(9, "Signal Length")

[macd_line, sig_line, hist] = ta.macd(close, fast_len, slow_len, sig_len)

hist_color = hist >= 0 ? (hist > hist[1] ? color.lime : color.green) : (hist < hist[1] ? color.red : color.maroon)

plot(hist, "Histogram", color=hist_color, style=plot.style_columns)
plot(macd_line, "MACD", color=color.blue, linewidth=2)
plot(sig_line, "Signal", color=color.orange, linewidth=2)
hline(0, "Zero", color=color.gray, linestyle=hline.style_dotted)
`,
  },
];
