"""Command-line walk-forward evaluation.

Example: ``python backtest.py --days 14 --output backtest-results.csv``
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation import build_predictions, evaluate_predictions, fetch_ohlcv_history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Historical days to fetch (1-90)")
    parser.add_argument("--fee-bps", type=float, default=4.0, help="Fee in bps per side")
    parser.add_argument("--slippage-bps", type=float, default=2.0, help="Slippage in bps per side")
    parser.add_argument(
        "--min-train", type=int, default=200, help="Warm-up windows for calibration"
    )
    parser.add_argument("--output", type=Path, help="Optional CSV path for window-level results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candles = fetch_ohlcv_history(args.days)
    predictions = build_predictions(candles)
    summary, detail = evaluate_predictions(
        predictions,
        fee_bps_per_side=args.fee_bps,
        slippage_bps_per_side=args.slippage_bps,
        min_train=args.min_train,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        detail.to_csv(args.output, index=False)
    print(json.dumps(summary.to_dict(), indent=2))


if __name__ == "__main__":
    main()
