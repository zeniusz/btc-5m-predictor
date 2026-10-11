"""Terminal version of the predictor. For the full dashboard run: streamlit run app.py"""
import os
import time
from datetime import datetime, timezone

from predictor import INTERVAL_MINUTES, fetch_snapshot


def monitor_bot():
    while True:
        try:
            s = fetch_snapshot()
        except Exception as e:
            print(f"Binance error: {e}")
            time.sleep(3)
            continue
        secs = max(0, int((s.interval_end - datetime.now(timezone.utc)).total_seconds()))
        os.system("cls" if os.name == "nt" else "clear")
        print(f"BTC PRICE:        ${s.price:,.2f}")
        print(f"WINDOW:           {s.interval_start:%H:%M:%S} -> {s.interval_end:%H:%M:%S} UTC")
        print(f"PREDICTION:       {'🚀 UP' if s.direction == 'UP' else '📉 DOWN'} in next {INTERVAL_MINUTES} min "
              f"(strength {s.confidence}/99)")
        print(f"SECONDS TO END:   {secs}s")
        print(f"MOMENTUM:         {s.momentum_pct:+.3f}%")
        print(f"ORDERBOOK IMB:    {s.imbalance:+.2f}")
        print(f"TRADE PRESSURE:   {s.pressure:+.2f}")
        print(f"VWAP DEVIATION:   {s.vwap_dev:+.3f}%")
        print(f"VOLUME SPIKE:     {s.volume_spike:.1f}x")
        print(f"VOLATILITY:       {s.volatility:.3f}%")
        print("-" * 60)
        time.sleep(2)


if __name__ == "__main__":
    monitor_bot()
