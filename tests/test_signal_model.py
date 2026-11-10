from signal_model import SignalFeatures, features_from_ohlcv, score_features


def candles(count=40, step=1.0, volume=10.0):
    rows = []
    for index in range(count):
        close = 100.0 + index * step
        rows.append([index * 60_000, close - 0.2, close + 0.3, close - 0.4, close, volume])
    return rows


def test_rising_history_is_bullish():
    signal = score_features(features_from_ohlcv(candles()))
    assert signal.direction == "UP"
    assert 0.5 < signal.raw_probability_up <= 0.99


def test_falling_history_is_bearish():
    signal = score_features(features_from_ohlcv(candles(step=-1.0)))
    assert signal.direction == "DOWN"
    assert 0.01 <= signal.raw_probability_up < 0.5


def test_volume_ratio_amplifies_but_score_stays_bounded():
    features = SignalFeatures(2.0, 4.0, 2.0, 100.0, 0.5)
    signal = score_features(features)
    assert signal.score == 1.0
    assert signal.strength == 99
