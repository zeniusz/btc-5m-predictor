"""Signal engine: pulls live Binance data (via ccxt) and scores the next 5-minute move."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import pstdev

import ccxt

SYMBOL = "BTC/USDT"
INTERVAL_MINUTES = 5

_exchange = ccxt.binance({"enableRateLimit": True})


def interval_bounds(now=None):
    """Return (start, end) of the 5-minute window that contains `now` (UTC)."""
    now = now or datetime.now(timezone.utc)
    start = now.replace(minute=(now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES, second=0, microsecond=0)
    return start, start + timedelta(minutes=INTERVAL_MINUTES)


def _clip(x):
    return max(-1.0, min(1.0, x))


@dataclass
class Snapshot:
    price: float
    open_price: float          # price at the start of the current 5m window
    interval_start: datetime
    interval_end: datetime
    momentum_pct: float        # % move since window open
    imbalance: float           # order book bid/ask imbalance, -1..1
    pressure: float            # taker buy/sell pressure, -1..1
    vwap_dev: float            # % deviation from 1m VWAP (last 30 candles)
    volume_spike: float        # last 1m volume / average 1m volume
    volatility: float          # stdev of 1m returns, in %
    score: float               # combined signal, -1..1
    direction: str             # "UP" | "DOWN"
    confidence: int            # 50..99 (a signal-strength gauge, not a probability)
    closes: list               # recent 1m closes for the sparkline
    times: list


def fetch_snapshot(depth=20, trades_lookback=100):
    now = datetime.now(timezone.utc)
    start, end = interval_bounds(now)

    ticker = _exchange.fetch_ticker(SYMBOL)
    price = ticker["last"]

    candles = _exchange.fetch_ohlcv(SYMBOL, "1m", limit=60)  # [ts, o, h, l, c, v]
    window_open = next((c[1] for c in candles if c[0] >= int(start.timestamp() * 1000)), price)

    book = _exchange.fetch_order_book(SYMBOL, limit=max(depth, 5))
    bid_sum = sum(a for _, a in book["bids"][:depth])
    ask_sum = sum(a for _, a in book["asks"][:depth])
    imbalance = (bid_sum - ask_sum) / (bid_sum + ask_sum + 1e-9)

    trades = _exchange.fetch_trades(SYMBOL, limit=trades_lookback)
    buy = sum(t["amount"] for t in trades if t["side"] == "buy")
    sell = sum(t["amount"] for t in trades if t["side"] == "sell")
    pressure = (buy - sell) / (buy + sell + 1e-9)

    recent = candles[-30:]
    vol_total = sum(c[5] for c in recent) or 1e-9
    vwap = sum(((c[2] + c[3] + c[4]) / 3) * c[5] for c in recent) / vol_total
    vwap_dev = (price - vwap) / vwap * 100

    vols = [c[5] for c in candles[:-1]]
    volume_spike = candles[-1][5] / (sum(vols) / len(vols) + 1e-9)

    closes = [c[4] for c in candles]
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] * 100 for i in range(1, len(closes))]
    volatility = pstdev(rets) if len(rets) > 1 else 0.0

    momentum_pct = (price - window_open) / window_open * 100

    # Weighted blend of normalised signals. Volume spikes amplify whichever way the tape is leaning.
    raw = (
        0.35 * imbalance
        + 0.25 * pressure
        + 0.20 * _clip(momentum_pct / 0.15)
        + 0.20 * _clip(vwap_dev / 0.15)  # above VWAP = bullish
    )
    amplifier = 1 + 0.25 * _clip((volume_spike - 1) / 3)
    score = _clip(raw * amplifier)
    direction = "UP" if score >= 0 else "DOWN"
    confidence = int(50 + min(49, abs(score) * 100))

    return Snapshot(
        price=price, open_price=window_open, interval_start=start, interval_end=end,
        momentum_pct=momentum_pct, imbalance=imbalance, pressure=pressure,
        vwap_dev=vwap_dev, volume_spike=volume_spike, volatility=volatility,
        score=score, direction=direction, confidence=confidence,
        closes=closes, times=[datetime.fromtimestamp(c[0] / 1000, timezone.utc) for c in candles],
    )
