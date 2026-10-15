"""
Non-circular label generation for health/failure prediction models.

Previously, health_model.py and failure_model.py derived their training
labels from a fixed formula/threshold computed on the SAME row of features
they predict from (e.g. "unhealthy if cpu > 85 or memory > 85"). That just
teaches a model to re-learn arithmetic/thresholds it was already given as
input - it adds latency and noise without any genuine predictive value.

These helpers instead derive labels from what ACTUALLY happened next: did
this instance trigger a real `Alert` row (any severity, or specifically
"critical") within a lookahead window after a given metrics snapshot? That
makes health/failure scoring a genuine forecasting problem - "given current
conditions, is trouble about to happen?" - learned from real recorded
outcomes (the Alert table), not synthesized from the same inputs being
predicted from.
"""
import bisect
from datetime import timedelta
from typing import List, Tuple

from app import models


def _alert_timestamps(alerts: List["models.Alert"], critical_only: bool = False) -> List:
    """Sorted list of trigger timestamps, optionally filtered to critical severity."""
    ts = []
    for a in alerts:
        if critical_only and (a.severity or "").lower() != "critical":
            continue
        if a.triggered_at is not None:
            ts.append(a.triggered_at)
    return sorted(ts)


def build_alert_based_labels(
    snapshots: List["models.MetricsSnapshot"],
    alerts: List["models.Alert"],
    lookahead_minutes: int = 15,
) -> Tuple[List["models.MetricsSnapshot"], List[int], List[int]]:
    """
    For each snapshot (returned sorted by timestamp), compute two labels:

      - any_alert_label: 1 if ANY alert for this instance triggered within
        (snapshot.timestamp, snapshot.timestamp + lookahead], else 0.
      - critical_alert_label: same, but only counting severity == 'critical'.

    Returns (sorted_snapshots, any_alert_labels, critical_alert_labels),
    all aligned by index.
    """
    sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
    any_ts = _alert_timestamps(alerts, critical_only=False)
    critical_ts = _alert_timestamps(alerts, critical_only=True)
    window = timedelta(minutes=lookahead_minutes)

    any_labels: List[int] = []
    critical_labels: List[int] = []

    for snap in sorted_snapshots:
        start = snap.timestamp
        end = snap.timestamp + window

        lo = bisect.bisect_right(any_ts, start)
        hi = bisect.bisect_right(any_ts, end)
        any_labels.append(1 if hi > lo else 0)

        lo_c = bisect.bisect_right(critical_ts, start)
        hi_c = bisect.bisect_right(critical_ts, end)
        critical_labels.append(1 if hi_c > lo_c else 0)

    return sorted_snapshots, any_labels, critical_labels


def has_both_classes(labels: List[int]) -> bool:
    """True if the label list contains at least one 0 and one 1 - i.e. real
    alert history actually gives the classifier something to discriminate."""
    return len(set(labels)) >= 2
