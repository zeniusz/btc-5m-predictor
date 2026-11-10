from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from predictor import Snapshot


def fake_snapshot():
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return Snapshot(
        price=100_100.0,
        open_price=100_000.0,
        interval_start=start,
        interval_end=start + timedelta(minutes=5),
        momentum_pct=0.1,
        imbalance=0.2,
        pressure=0.1,
        vwap_dev=0.05,
        volume_spike=1.2,
        volatility=0.08,
        score=0.3,
        direction="UP",
        confidence=80,
        closes=[100_000.0, 100_100.0],
        times=[start - timedelta(minutes=1), start],
    )


def test_dashboard_renders_with_a_snapshot():
    with patch("predictor.fetch_snapshot", return_value=fake_snapshot()):
        app = AppTest.from_file("../app.py", default_timeout=15).run()
    assert not app.exception
    assert len(app.metric) == 5
