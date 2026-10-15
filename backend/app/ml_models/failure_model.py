"""
System failure prediction.

PREVIOUSLY: trained a RandomForestClassifier on a label computed by a
static rule on the SAME row of features it predicts from:
    failure = 1 if (cpu_usage > 85 or memory_usage > 85) else 0
That's just re-encoding a hand-written threshold as a classifier - it can
never learn anything a plain `if` statement didn't already know.

NOW: trained on whether this instance ACTUALLY triggered a real CRITICAL
Alert within `lookahead_minutes` after each historical snapshot (see
label_generation.py). `failure_probability` is a genuine forecast -
"given current conditions, how likely is a critical incident soon?" -
learned from real recorded outcomes, not a restated threshold.

Same cold-start handling as health_model.py: if an instance has no
critical-alert history yet (all one class), one synthetic sample of the
opposite class is added purely for numerical stability, and this is
reported via `trained_on_real_incidents` so callers can be honest about
whether the number is backed by real incidents yet.
"""
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import joblib
import os
import logging

from app.ml_models.label_generation import build_alert_based_labels, has_both_classes

logger = logging.getLogger(__name__)

FEATURE_NAMES = ['cpu_usage', 'memory_usage', 'disk_usage', 'load_1min']

_SYNTHETIC_BAD_ROW = [95, 95, 90, 10]
_SYNTHETIC_GOOD_ROW = [5, 5, 5, 0.1]


class FailureModel:
    def __init__(self, model_dir='ml_data/models', lookahead_minutes=15):
        self.model_dir = model_dir
        self.model_path = f"{model_dir}/failure_model.pkl"
        self.model = None
        self.lookahead_minutes = lookahead_minutes
        self.trained_on_real_incidents = False
        os.makedirs(model_dir, exist_ok=True)

    def _row_from_snapshot(self, m):
        return [
            getattr(m, 'cpu_usage', 0) or 0,
            getattr(m, 'memory_usage', 0) or 0,
            getattr(m, 'disk_usage', 0) or 0,
            getattr(m, 'load_1min', 0) or 0,
        ]

    def _row_from_dict(self, m: dict):
        return [
            m.get('cpu_usage', 0) or 0,
            m.get('memory_usage', 0) or 0,
            m.get('disk_usage', 0) or 0,
            m.get('load_1min', 0) or 0,
        ]

    def train(self, snapshots, alerts):
        """
        snapshots: list of MetricsSnapshot ORM rows for one instance.
        alerts: list of Alert ORM rows for the same instance.
        """
        sorted_snaps, _, critical_labels = build_alert_based_labels(
            snapshots, alerts, lookahead_minutes=self.lookahead_minutes
        )

        X = np.array([self._row_from_snapshot(m) for m in sorted_snaps], dtype=float)
        y = np.array(critical_labels)

        self.trained_on_real_incidents = has_both_classes(y.tolist())

        if not self.trained_on_real_incidents:
            only_bad = len(y) > 0 and bool(y.all())
            synthetic_row = _SYNTHETIC_GOOD_ROW if only_bad else _SYNTHETIC_BAD_ROW
            synthetic_label = 0 if only_bad else 1
            X = np.vstack([X, synthetic_row])
            y = np.append(y, synthetic_label)

        self.model = RandomForestClassifier(
            n_estimators=150,
            max_depth=8,
            random_state=42,
            class_weight='balanced',
        )
        self.model.fit(X, y)
        joblib.dump({'model': self.model, 'trained_on_real_incidents': self.trained_on_real_incidents}, self.model_path)

        return {
            "status": "trained",
            "samples": int(len(X)),
            "real_alert_labels_used": self.trained_on_real_incidents,
            "lookahead_minutes": self.lookahead_minutes,
        }

    def predict(self, current_metrics):
        if self.model is None:
            saved = joblib.load(self.model_path)
            if isinstance(saved, dict):
                self.model = saved['model']
                self.trained_on_real_incidents = saved.get('trained_on_real_incidents', False)
            else:
                self.model = saved  # backward compat with old .pkl format

        X = np.array([self._row_from_dict(current_metrics)], dtype=float)
        proba = self.model.predict_proba(X)[0]
        classes = list(self.model.classes_)
        prob = float(proba[classes.index(1)]) if 1 in classes else 0.0

        return {
            "failure_probability": round(prob, 3),
            "status": "critical" if prob > 0.7 else "normal",
            "trained_on_real_incidents": self.trained_on_real_incidents,
        }


# Default/fallback instance (per-instance models are created via
# app.ml_models.training_cache.get_or_create_model instead of using this
# shared singleton directly).
failure_model = FailureModel()
