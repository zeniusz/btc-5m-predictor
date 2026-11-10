from datetime import UTC, datetime

from evaluation import build_predictions, evaluate_predictions


def synthetic_candles(count=1800):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = []
    price = 100.0
    for index in range(count):
        drift = 0.04 if (index // 30) % 2 == 0 else -0.03
        open_price = price
        price = max(1.0, price + drift + ((index % 7) - 3) * 0.003)
        rows.append(
            [
                int(start.timestamp() * 1000) + index * 60_000,
                open_price,
                max(open_price, price) + 0.01,
                min(open_price, price) - 0.01,
                price,
                10.0 + index % 5,
            ]
        )
    return rows


def test_build_predictions_has_no_target_candle_in_features():
    predictions = build_predictions(synthetic_candles(100))
    assert not predictions.empty
    assert predictions.iloc[0]["timestamp"].minute % 5 == 0


def test_walk_forward_summary_includes_costs_and_baselines():
    predictions = build_predictions(synthetic_candles())
    summary, detail = evaluate_predictions(predictions, min_train=100)
    assert summary.windows == len(detail)
    assert summary.round_trip_cost_bps == 12.0
    assert 0.0 <= summary.model_accuracy <= 1.0
    assert 0.0 <= summary.persistence_accuracy <= 1.0
    assert 0.0 <= summary.random_accuracy <= 1.0
    assert 0.0 <= summary.brier_score <= 1.0
    assert detail["calibrated_probability_up"].notna().all()
