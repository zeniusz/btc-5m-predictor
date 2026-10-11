# ⚡ btc-5m-predictor

Live UP / DOWN call for the current 5-minute BTC window, built from real Binance market-microstructure signals
(via [ccxt](https://github.com/ccxt/ccxt), no API key needed):

order-book imbalance · trade pressure · VWAP deviation · volume spikes · volatility · tick momentum

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py      # dashboard: live price, gauge, countdown, chart, live track record
python btc-5m.py          # plain terminal version
```

## Files
- `predictor.py` – fetches Binance data and computes the signal
- `app.py` – Streamlit dashboard
- `btc-5m.py` – terminal version

> Experimental, for research purposes only. 5-minute price moves are extremely noisy and often close to random.
> Not financial advice.
