"""Statistical anomaly detection for spend series — local, no ML, no cloud."""

import statistics
from dataclasses import dataclass


@dataclass
class Anomaly:
    """A spend value that deviates sharply above its baseline."""

    period: str
    value: float
    baseline: float
    z_score: float


def detect_spikes(
    series: list[tuple[str, float]],
    *,
    threshold: float = 2.0,
    min_history: int = 3,
) -> list[Anomaly]:
    """Flag points whose value spikes above the baseline of prior points.

    Uses a z-score against all preceding points. Only upward spikes are
    flagged (a spend *drop* is not an anomaly we care about). Points without
    at least ``min_history`` preceding points are skipped, so sparse data
    never produces false alarms.
    """
    spikes: list[Anomaly] = []
    for i, (period, value) in enumerate(series):
        baseline_values = [v for _, v in series[:i]]
        if len(baseline_values) < min_history:
            continue
        mean = statistics.fmean(baseline_values)
        if value <= mean:
            continue
        std = statistics.stdev(baseline_values)
        z = float("inf") if std == 0 else (value - mean) / std
        if z > threshold:
            spikes.append(Anomaly(period=period, value=value, baseline=mean, z_score=z))
    return spikes
