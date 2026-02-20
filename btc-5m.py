import ccxt
import time
from datetime import datetime, timedelta
import os

# ——— BINANCE SETUP ———
binance = ccxt.binance()
SYMBOL = "BTC/USDT"

INTERVAL_MINUTES = 5

def get_next_interval(now=None):
    now = now or datetime.utcnow()
    start_min = (now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
    start = now.replace(minute=start_min, second=0, microsecond=0)
    if now >= start:
        start += timedelta(minutes=INTERVAL_MINUTES)
    end = start + timedelta(minutes=INTERVAL_MINUTES)
    return start, end

def fetch_order_book_imbalance(symbol="BTC/USDT", depth=10):
    book = binance.fetch_order_book(symbol)
    bids = book["bids"][:depth]
    asks = book["asks"][:depth]
    bid_sum = sum([amt for price, amt in bids])
    ask_sum = sum([amt for price, amt in asks])
    return (bid_sum - ask_sum) / (bid_sum + ask_sum + 1e-6)

def fetch_trade_pressure(symbol="BTC/USDT", lookback=50):
    trades = binance.fetch_trades(symbol)
    recent = trades[-lookback:]
    buy_vol = sum([t["amount"] for t in recent if t["side"] == "buy"])
    sell_vol = sum([t["amount"] for t in recent if t["side"] == "sell"])
    return (buy_vol - sell_vol) / (buy_vol + sell_vol + 1e-6)

def monitor_bot():
    price_history = []
    interval_start, interval_end = get_next_interval()
    start_price = None
    interval_signal = None

    while True:
        now = datetime.utcnow()

        # Fetch current price
        ticker = binance.fetch_ticker(SYMBOL)
        current_price = ticker["last"]
        price_history.append(current_price)
        if len(price_history) > 50:
            price_history.pop(0)

        # Lock interval start price
        if start_price is None:
            start_price = current_price

        # Compute indicators
        momentum = current_price - start_price
        imbalance = fetch_order_book_imbalance()
        pressure = fetch_trade_pressure()

        # Score for prediction
        score = 0.5 * imbalance + 0.3 * pressure + 0.2 * (momentum / start_price)
        interval_signal = "🚀 UP" if score >= 0 else "📉 DOWN"

        # Countdown timer
        sec_to_end = int((interval_end - now).total_seconds())

        # Console output
        os.system("cls" if os.name == "nt" else "clear")
        print(f"BTC PRICE:        ${current_price:,.2f}")
        print(f"INTERVAL START:   {interval_start.strftime('%H:%M:%S')}")
        print(f"INTERVAL END:     {interval_end.strftime('%H:%M:%S')}")
        print(f"PREDICTION:       {interval_signal} in next {INTERVAL_MINUTES} min")
        print(f"SECONDS TO END:   {sec_to_end}s")
        print(f"MOMENTUM:         {momentum:+.2f}")
        print(f"ORDERBOOK IMB:    {imbalance:+.2f}")
        print(f"TRADE PRESSURE:   {pressure:+.2f}")
        print("-" * 60)

        # Move to next interval if time passed
        if now >= interval_end:
            interval_start, interval_end = get_next_interval(now + timedelta(seconds=1))
            start_price = None
            price_history.clear()

        time.sleep(1)

if __name__ == "__main__":
    monitor_bot()