# Changelog

## 2.0.0 — 2026-11-10

Version 2 turns the original live demo into an evidence-first signal lab.

### Added

- Leakage-resistant historical replay using one-minute Binance candles.
- Expanding-window calibration that uses prior observations only.
- Persistence and seeded-random baselines.
- Configurable trading fees and slippage on every simulated round trip.
- Brier score and expected calibration error alongside directional accuracy.
- Network-free unit tests, a Streamlit smoke test and GitHub Actions CI.
- Monthly Dependabot checks for Python and GitHub Actions dependencies.

### Changed

- A live prediction is now locked once per five-minute window. Version 1 kept
  changing the displayed call until the window closed, which made its session
  score too optimistic.
- The scored model now uses only fully closed candles from before the target
  window, so the same rule can be replayed without look-ahead.
- Order-book imbalance and trade pressure remain live context, but are not
  included in the evaluated signal because free historical depth snapshots are
  not available from the same endpoint.
- The old “confidence” number is explicitly described as signal strength, not
  a calibrated probability.

## 1.0.0 — 2026-10-11

- Initial live Streamlit dashboard and terminal monitor.
- Five-minute UP/DOWN calls with Binance market data.
- Session-only scorecard and signal display.
