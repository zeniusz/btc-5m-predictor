"""Pure, replayable signal logic shared by the live app and backtest."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import pstdev


@dataclass(frozen=True)
class SignalFeatures:
    momentum_5m_pct: float
    momentum_15m_pct: float
    vwap_deviation_pct: float
    volume_ratio: float
    volatility_pct: float


@dataclass(frozen=True)
class Signal:
    features: SignalFeatures
    score: float
    direction: str
    strength: int
    raw_probability_up: float


def clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def features_from_ohlcv(candles: Sequence[Sequence[float]]) -> SignalFeatures:
    """Build features from at least 31 fully closed one-minute candles.

    Each candle is ``[timestamp_ms, open, high, low, close, volume]``. The
    caller is responsible for excluding the interval being predicted.
    """
    if len(candles) < 31:
        raise ValueError("At least 31 closed one-minute candles are required")

    recent = candles[-31:]
    closes = [float(row[4]) for row in recent]
    volumes = [float(row[5]) for row in recent]
    last_close = closes[-1]

    momentum_5m_pct = (last_close / closes[-6] - 1.0) * 100.0
    momentum_15m_pct = (last_close / closes[-16] - 1.0) * 100.0

    vwap_rows = recent[-30:]
    volume_total = sum(float(row[5]) for row in vwap_rows)
    if volume_total <= 0:
        vwap = last_close
    else:
        vwap = (
            sum(
                ((float(row[2]) + float(row[3]) + float(row[4])) / 3.0) * float(row[5])
                for row in vwap_rows
            )
            / volume_total
        )
    vwap_deviation_pct = (last_close / vwap - 1.0) * 100.0 if vwap else 0.0

    baseline_volume = sum(volumes[-31:-1]) / 30.0
    volume_ratio = volumes[-1] / baseline_volume if baseline_volume > 0 else 1.0

    returns = [(closes[index] / closes[index - 1] - 1.0) * 100.0 for index in range(1, len(closes))]
    volatility_pct = pstdev(returns) if len(returns) > 1 else 0.0

    return SignalFeatures(
        momentum_5m_pct=momentum_5m_pct,
        momentum_15m_pct=momentum_15m_pct,
        vwap_deviation_pct=vwap_deviation_pct,
        volume_ratio=volume_ratio,
        volatility_pct=volatility_pct,
    )


def score_features(features: SignalFeatures) -> Signal:
    """Score a fixed, interpretable momentum signal without fitted parameters."""
    raw = (
        0.45 * clip(features.momentum_5m_pct / 0.20)
        + 0.35 * clip(features.vwap_deviation_pct / 0.20)
        + 0.20 * clip(features.momentum_15m_pct / 0.45)
    )
    volume_amplifier = 1.0 + 0.20 * clip((features.volume_ratio - 1.0) / 2.0)
    score = clip(raw * volume_amplifier)
    probability_up = 0.5 + 0.49 * score
    return Signal(
        features=features,
        score=score,
        direction="UP" if score >= 0 else "DOWN",
        strength=int(50 + min(49, abs(score) * 100)),
        raw_probability_up=probability_up,
    )


def signal_from_ohlcv(candles: Sequence[Sequence[float]]) -> Signal:
    return score_features(features_from_ohlcv(candles))
