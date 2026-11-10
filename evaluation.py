"""Leakage-resistant walk-forward evaluation for the five-minute signal."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

import ccxt
import pandas as pd

from predictor import INTERVAL_MINUTES, SYMBOL
from signal_model import signal_from_ohlcv


@dataclass(frozen=True)
class EvaluationSummary:
    windows: int
    start: str
    end: str
    model_accuracy: float
    persistence_accuracy: float
    random_accuracy: float
    brier_score: float
    expected_calibration_error: float
    gross_return_pct: float
    net_return_pct: float
    persistence_net_return_pct: float
    random_net_return_pct: float
    round_trip_cost_bps: float

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def fetch_ohlcv_history(days: int = 14, exchange=None) -> list[list[float]]:
    """Fetch one-minute Binance candles in deterministic chronological pages."""
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    client = exchange or ccxt.binance({"enableRateLimit": True})
    end_ms = int(datetime.now(UTC).timestamp() * 1000)
    since = int((datetime.now(UTC) - timedelta(days=days)).timestamp() * 1000)
    rows: list[list[float]] = []

    while since < end_ms:
        batch = client.fetch_ohlcv(SYMBOL, "1m", since=since, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        next_since = int(batch[-1][0]) + 60_000
        if next_since <= since:
            break
        since = next_since
        if len(batch) < 1000:
            break

    deduplicated = {int(row[0]): list(row) for row in rows if int(row[0]) < end_ms}
    return [deduplicated[key] for key in sorted(deduplicated)]


def build_predictions(candles: Iterable[Iterable[float]]) -> pd.DataFrame:
    """Replay predictions using only candles closed before each target window."""
    rows = [list(row) for row in candles]
    rows.sort(key=lambda row: row[0])
    records: list[dict[str, object]] = []

    for index in range(31, len(rows) - INTERVAL_MINUTES + 1):
        timestamp = datetime.fromtimestamp(float(rows[index][0]) / 1000, UTC)
        if timestamp.minute % INTERVAL_MINUTES or timestamp.second:
            continue

        history = rows[:index]
        target = rows[index : index + INTERVAL_MINUTES]
        if len(target) < INTERVAL_MINUTES:
            continue
        expected = [int(target[0][0]) + minute * 60_000 for minute in range(INTERVAL_MINUTES)]
        if [int(row[0]) for row in target] != expected:
            continue

        signal = signal_from_ohlcv(history)
        actual_return_pct = (float(target[-1][4]) / float(target[0][1]) - 1.0) * 100.0
        actual_up = actual_return_pct >= 0.0
        records.append(
            {
                "timestamp": timestamp,
                "score": signal.score,
                "raw_probability_up": signal.raw_probability_up,
                "model_up": signal.direction == "UP",
                "actual_up": actual_up,
                "actual_return_pct": actual_return_pct,
                "momentum_5m_pct": signal.features.momentum_5m_pct,
                "momentum_15m_pct": signal.features.momentum_15m_pct,
                "vwap_deviation_pct": signal.features.vwap_deviation_pct,
                "volume_ratio": signal.features.volume_ratio,
                "volatility_pct": signal.features.volatility_pct,
            }
        )

    return pd.DataFrame.from_records(records)


def add_walk_forward_calibration(
    predictions: pd.DataFrame,
    *,
    min_train: int = 200,
    bins: int = 10,
) -> pd.DataFrame:
    """Calibrate each row from prior rows only, with a conservative beta prior."""
    if len(predictions) <= min_train:
        raise ValueError(f"Need more than {min_train} prediction windows")
    if bins < 2:
        raise ValueError("bins must be at least 2")

    frame = predictions.reset_index(drop=True).copy()
    calibrated: list[float | None] = []
    for index, row in frame.iterrows():
        if index < min_train:
            calibrated.append(None)
            continue
        probability = float(row["raw_probability_up"])
        bucket = min(bins - 1, int(probability * bins))
        history = frame.iloc[:index]
        history_buckets = (history["raw_probability_up"] * bins).astype(int).clip(upper=bins - 1)
        peers = history.loc[history_buckets == bucket, "actual_up"]
        calibrated.append((float(peers.sum()) + 5.0) / (len(peers) + 10.0))

    frame["calibrated_probability_up"] = calibrated
    return frame.iloc[min_train:].reset_index(drop=True)


def _compounded_return(returns_pct: pd.Series) -> float:
    wealth = float((1.0 + returns_pct / 100.0).prod())
    return (wealth - 1.0) * 100.0


def _calibration_error(probabilities: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    bucket = (probabilities * bins).astype(int).clip(upper=bins - 1)
    total = len(probabilities)
    error = 0.0
    for value in range(bins):
        mask = bucket == value
        count = int(mask.sum())
        if not count:
            continue
        error += count / total * abs(float(probabilities[mask].mean()) - float(actual[mask].mean()))
    return error


def evaluate_predictions(
    predictions: pd.DataFrame,
    *,
    fee_bps_per_side: float = 4.0,
    slippage_bps_per_side: float = 2.0,
    min_train: int = 200,
    seed: int = 7,
) -> tuple[EvaluationSummary, pd.DataFrame]:
    """Compare the model with persistence and seeded-random baselines."""
    frame = add_walk_forward_calibration(predictions, min_train=min_train)
    probabilities = frame["calibrated_probability_up"].astype(float)
    frame["model_up_calibrated"] = probabilities >= 0.5
    frame["persistence_up"] = frame["actual_return_pct"].shift(1).fillna(0.0) >= 0.0
    rng = random.Random(seed)
    frame["random_up"] = [bool(rng.getrandbits(1)) for _ in range(len(frame))]

    cost_bps = 2.0 * (fee_bps_per_side + slippage_bps_per_side)
    cost_pct = cost_bps / 100.0
    actual_return = frame["actual_return_pct"].astype(float)
    for label, direction in (
        ("model", frame["model_up_calibrated"]),
        ("persistence", frame["persistence_up"]),
        ("random", frame["random_up"]),
    ):
        sign = direction.map({True: 1.0, False: -1.0})
        frame[f"{label}_gross_return_pct"] = sign * actual_return
        frame[f"{label}_net_return_pct"] = frame[f"{label}_gross_return_pct"] - cost_pct

    actual = frame["actual_up"].astype(bool)
    summary = EvaluationSummary(
        windows=len(frame),
        start=frame["timestamp"].min().isoformat(),
        end=frame["timestamp"].max().isoformat(),
        model_accuracy=float((frame["model_up_calibrated"] == actual).mean()),
        persistence_accuracy=float((frame["persistence_up"] == actual).mean()),
        random_accuracy=float((frame["random_up"] == actual).mean()),
        brier_score=float(((probabilities - actual.astype(float)) ** 2).mean()),
        expected_calibration_error=_calibration_error(probabilities, actual.astype(float)),
        gross_return_pct=_compounded_return(frame["model_gross_return_pct"]),
        net_return_pct=_compounded_return(frame["model_net_return_pct"]),
        persistence_net_return_pct=_compounded_return(frame["persistence_net_return_pct"]),
        random_net_return_pct=_compounded_return(frame["random_net_return_pct"]),
        round_trip_cost_bps=cost_bps,
    )
    return summary, frame
