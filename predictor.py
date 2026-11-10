"""Signal engine: pulls live Binance data (via ccxt) and scores the next 5-minute move."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import ccxt

from signal_model import signal_from_ohlcv

SYMBOL = "BTC/USDT"
INTERVAL_MINUTES = 5

_exchange = ccxt.binance({"enableRateLimit": True})


def interval_bounds(now=None):
    """Return (start, end) of the 5-minute window that contains `now` (UTC)."""
    now = now or datetime.now(UTC)
    start = now.replace(
        minute=(now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES, second=0, microsecond=0
    )
    return start, start + timedelta(minutes=INTERVAL_MINUTES)


@dataclass
class Snapshot:
    price: float
    open_price: float  # price at the start of the current 5m window
    interval_start: datetime
    interval_end: datetime
    momentum_pct: float  # % move since window open
    imbalance: float  # order book bid/ask imbalance, -1..1
    pressure: float  # taker buy/sell pressure, -1..1
    vwap_dev: float  # % deviation from 1m VWAP (last 30 candles)
    volume_spike: float  # last 1m volume / average 1m volume
    volatility: float  # stdev of 1m returns, in %
    score: float  # combined signal, -1..1
    direction: str  # "UP" | "DOWN"
    confidence: int  # 50..99 (signal strength, not a probability)
    closes: list  # recent 1m closes for the sparkline
    times: list


def fetch_snapshot(depth=20, trades_lookback=100):
    now = datetime.now(UTC)
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

    # The call for this interval uses only candles that closed before it began.
    # This makes the exact live rule replayable in the historical evaluation.
    history = [c for c in candles if c[0] < int(start.timestamp() * 1000)]
    signal = signal_from_ohlcv(history)
    vwap_dev = signal.features.vwap_deviation_pct
    volume_spike = signal.features.volume_ratio
    volatility = signal.features.volatility_pct

    closes = [c[4] for c in candles]

    momentum_pct = (price - window_open) / window_open * 100

    return Snapshot(
        price=price,
        open_price=window_open,
        interval_start=start,
        interval_end=end,
        momentum_pct=momentum_pct,
        imbalance=imbalance,
        pressure=pressure,
        vwap_dev=vwap_dev,
        volume_spike=volume_spike,
        volatility=volatility,
        score=signal.score,
        direction=signal.direction,
        confidence=signal.strength,
        closes=closes,
        times=[datetime.fromtimestamp(c[0] / 1000, UTC) for c in candles],
    )
