# Recorded v2 evaluation — 2026-11-10

This is the first recorded result for version 2. It is retained because a
negative result is more useful than an untested live score.

## Command

```bash
python backtest.py --days 14 --output backtest-results.csv
```

Defaults used:

- symbol: BTC/USDT on Binance;
- source: one-minute OHLCV candles through ccxt;
- calibration warm-up: 200 five-minute windows;
- fee: 4 basis points per side;
- slippage: 2 basis points per side;
- total simulated round-trip cost: 12 basis points per window;
- random baseline seed: 7.

## Result

| Metric | Result |
|---|---:|
| Evaluation period | 2026-10-27 17:05 to 2026-11-09 23:45 UTC |
| Windows after warm-up | 3,825 |
| Model directional accuracy | 48.89% |
| Previous-direction accuracy | 49.07% |
| Seeded-random accuracy | 49.41% |
| Brier score | 0.2511 |
| Expected calibration error | 3.49% |
| Model compounded gross return | -1.01% |
| Model compounded net return | -99.00% |
| Previous-direction net return | -98.99% |
| Seeded-random net return | -99.08% |

## Interpretation

The model did not beat either baseline. Its Brier score was slightly worse than
the 0.25 score of an uninformative 50/50 forecast. Trading every five-minute
window also makes modest per-trade costs compound rapidly; after the assumed
12 basis points per round trip, all three always-in-market strategies lost
almost all simulated capital.

This does **not** prove that every short-horizon BTC signal is useless. It shows
that this fixed signal, on this period and under these assumptions, did not
demonstrate an edge. A credible next experiment would first add an abstain zone
and evaluate it on a later untouched period rather than tune against this one.

The generated window-level CSV is intentionally ignored by Git because anyone
can reproduce it from the command above and market data may later be revised by
the provider.
