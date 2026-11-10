# BTC 5-minute signal lab · v2

[![Version](https://img.shields.io/badge/version-2.0.0-2563eb)](CHANGELOG.md)
[![CI](https://github.com/zeniusz/btc-5m-predictor/actions/workflows/ci.yml/badge.svg)](https://github.com/zeniusz/btc-5m-predictor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776ab)](https://www.python.org/)

An evidence-first experiment for five-minute BTC direction. It makes one
**UP/DOWN** call per Binance five-minute window, shows the live market context,
and evaluates the replayable signal against simple baselines.

> **Finding, not a sales pitch:** five-minute BTC moves are noisy. A strategy
> is not useful merely because its directional accuracy is above 50%; it must
> also beat naive baselines, remain calibrated and survive realistic costs.

## What changed in v2

Version 1 was a live dashboard. Its displayed call could change until the final
seconds of a window, so the session score was not a fair out-of-sample result.

Version 2:

- locks the prediction once per five-minute window;
- calculates it only from candles closed before that window starts;
- adds an expanding-window walk-forward evaluation;
- compares it with previous-direction and seeded-random baselines;
- reports probability calibration, fees and slippage;
- adds automated tests and CI.

See the full [changelog](CHANGELOG.md).

## Evaluation design

For every historical five-minute window, the evaluator:

1. builds momentum, VWAP-deviation, volume and volatility features using only
   earlier one-minute candles;
2. records the next window's open-to-close direction;
3. calibrates the raw score using earlier predictions only (expanding window);
4. compares the call with persistence and deterministic random baselines;
5. subtracts a configurable fee and slippage on both entry and exit.

The default round-trip cost is **12 bps**: 4 bps fee plus 2 bps slippage per
side. This is deliberately stricter than a frictionless chart.

### Recorded v2 result

Run on 14 days of Binance BTC/USDT one-minute candles, ending 2026-11-09 UTC:

| Walk-forward result | Value |
|---|---:|
| Evaluated windows | 3,825 |
| Model accuracy | **48.89%** |
| Previous-direction baseline | 49.07% |
| Seeded-random baseline | 49.41% |
| Brier score | 0.2511 |
| Expected calibration error | 3.49% |
| Model gross return | -1.01% |
| Model return after 12 bps/window | -99.00% |

**Conclusion:** this fixed signal showed no predictive or tradable edge in the
recorded period. That negative result is the point of v2: the repository now
tests the idea instead of presenting signal strength as evidence. Full method,
parameters and interpretation: [recorded evaluation](docs/evaluation-2026-11-10.md).

```bash
python backtest.py --days 14 --output backtest-results.csv
```

The command prints model, persistence and random accuracy; Brier score and
expected calibration error; compounded gross and after-cost returns; and the
evaluation dates, number of windows and cost assumptions.

Historical performance is not evidence of future returns. The fixed signal is
an interpretable research baseline, not a trained production model.

## Live dashboard

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The dashboard refreshes every two seconds and shows:

- the locked call and its signal strength (not a win probability);
- the current five-minute price window;
- recent session results;
- order-book imbalance and trade pressure as **unevaluated live context**;
- VWAP deviation, volume ratio and volatility.

For a terminal-only view, run `python btc-5m.py`.

No exchange account or API key is required; market data comes from Binance
through [ccxt](https://github.com/ccxt/ccxt).

## Tests and quality checks

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

CI runs the suite on Python 3.11 and 3.12. Tests do not call Binance.

## Repository map

```text
app.py              Streamlit dashboard
btc-5m.py           terminal monitor
predictor.py        live Binance snapshot and locked-window inputs
signal_model.py     pure feature and score logic shared with evaluation
evaluation.py       historical replay, calibration, baselines and costs
backtest.py         command-line evaluation
tests/              network-free unit and app smoke tests
```

## Limits

- Five-minute direction is close to random and very sensitive to costs.
- The backtest uses Binance candles, not historical order-book snapshots.
- Calibration is evaluated walk-forward, but the signal weights are fixed by
  hand rather than learned in each training fold.
- Funding, spread variation, latency, partial fills and market impact are not
  modelled; the slippage input is only an approximation.
- Session results disappear when the dashboard restarts.

Experimental software for research and education only. **Not financial advice.**
