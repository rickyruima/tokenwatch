import os
from datetime import UTC, datetime, timedelta

from click.testing import CliRunner

from tokenwatch import TokenWatch
from tokenwatch.anomaly import Anomaly, detect_spikes
from tokenwatch.cli import main


def _seed(db_path, daily_costs):
    """Seed one event per day; daily_costs[0] is the oldest day."""
    tw = TokenWatch(db_path=db_path)
    now = datetime.now(UTC)
    n = len(daily_costs)
    for i, cost in enumerate(daily_costs):
        days_ago = n - 1 - i
        rec = tw.record(provider="openai", model="gpt-4",
                        input_tokens=100, output_tokens=50, cost_usd=cost)
        rec.timestamp = now - timedelta(days=days_ago)
        tw.storage._get_conn().execute(
            "UPDATE events SET timestamp = ? WHERE id = ?", (rec.timestamp.isoformat(), rec.id))
        tw.storage._get_conn().commit()


def test_flags_point_far_above_baseline():
    # flat ~$10/day baseline, then a $50 spike
    series = [("2026-05-01", 10.0), ("2026-05-02", 11.0), ("2026-05-03", 9.0),
              ("2026-05-04", 10.0), ("2026-05-05", 50.0)]
    spikes = detect_spikes(series, threshold=2.0)
    assert len(spikes) == 1
    assert spikes[0].period == "2026-05-05"
    assert spikes[0].value == 50.0
    assert spikes[0].baseline < 50.0
    assert spikes[0].z_score > 2.0


def test_no_spike_when_steady():
    series = [("2026-05-01", 10.0), ("2026-05-02", 10.5), ("2026-05-03", 9.5),
              ("2026-05-04", 10.2), ("2026-05-05", 9.8)]
    assert detect_spikes(series, threshold=2.0) == []


def test_returns_empty_when_history_too_short():
    # not enough baseline points to judge -> no false alarms
    series = [("2026-05-04", 10.0), ("2026-05-05", 500.0)]
    assert detect_spikes(series, threshold=2.0, min_history=3) == []


def test_dip_is_not_flagged():
    # a sharp DROP in spend is not a "spend spike"
    series = [("2026-05-01", 50.0), ("2026-05-02", 51.0), ("2026-05-03", 49.0),
              ("2026-05-04", 50.0), ("2026-05-05", 1.0)]
    assert detect_spikes(series, threshold=2.0) == []


def test_flat_baseline_flags_any_increase():
    # zero-variance baseline: any rise above it is a spike (no div-by-zero crash)
    series = [("2026-05-01", 10.0), ("2026-05-02", 10.0), ("2026-05-03", 10.0),
              ("2026-05-04", 25.0)]
    spikes = detect_spikes(series, threshold=2.0)
    assert len(spikes) == 1
    assert spikes[0].period == "2026-05-04"


def test_check_detects_spike(tmp_path):
    db = tmp_path / "tw.db"
    _seed(db, [1.0, 1.2, 0.9, 1.1, 1.0, 0.95, 50.0])  # last day spikes
    os.environ["TOKENWATCH_DB"] = str(db)
    try:
        result = CliRunner().invoke(main, ["check"])
    finally:
        del os.environ["TOKENWATCH_DB"]
    assert result.exit_code == 0
    assert "50" in result.output  # the spike amount
    assert "spike" in result.output.lower() or "🚨" in result.output


def test_check_clean_when_steady(tmp_path):
    db = tmp_path / "tw.db"
    _seed(db, [1.0, 1.1, 0.9, 1.05, 0.95, 1.0, 1.02])
    os.environ["TOKENWATCH_DB"] = str(db)
    try:
        result = CliRunner().invoke(main, ["check"])
    finally:
        del os.environ["TOKENWATCH_DB"]
    assert result.exit_code == 0
    assert "no" in result.output.lower()  # "no anomalies"/"no spikes"


def test_check_no_data(tmp_path):
    db = tmp_path / "tw.db"
    TokenWatch(db_path=db)  # creates empty db
    os.environ["TOKENWATCH_DB"] = str(db)
    try:
        result = CliRunner().invoke(main, ["check"])
    finally:
        del os.environ["TOKENWATCH_DB"]
    assert result.exit_code == 0
