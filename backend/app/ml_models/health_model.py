"""
Instance health scoring.

PREVIOUSLY: trained a RandomForestRegressor on a label computed by a fixed
formula from the SAME row of features it predicts from:
    score = 100 - (cpu*0.3 + memory*0.3 + disk*0.2 + load_1min*5)
That's not machine learning - it's the model re-discovering arithmetic you
already wrote down. It can never disagree with the formula, so "training"
it added latency without adding any real predictive signal.

NOW: trained on whether this instance ACTUALLY triggered a real Alert
within `lookahead_minutes` after each historical snapshot (see
label_generation.py). The health score reported is
`100 * P(no alert within the lookahead window)` - a genuine forecast of
"is trouble about to happen" learned from real historical outcomes.

If an instance has no alert history yet, there's nothing real to learn
from two classes, so a single synthetic "bad" sample is added purely for
numerical stability (RandomForestClassifier needs >= 2 classes to fit) -
the same cold-start technique already used by failure_model.py. This is
reported back via `real_alert_labels_used` so callers/UI can be honest
about whether the score is backed by real incidents yet.
"""
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import joblib
import os
import logging

from app.ml_models.label_generation import build_alert_based_labels, has_both_classes

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    'cpu_usage', 'memory_usage', 'disk_usage',
    'network_rx', 'network_tx', 'load_1min', 'load_5min',
]

# Deliberately extreme synthetic rows used only to give the classifier a
# second class to fit when an instance's real alert history is all one
# class (most commonly: no alerts have ever fired yet).
_SYNTHETIC_BAD_ROW = [95, 95, 90, 1e8, 1e8, 10, 10]
_SYNTHETIC_GOOD_ROW = [5, 5, 5, 0, 0, 0.1, 0.1]


class HealthModel:
    def __init__(self, model_dir='ml_data/models', lookahead_minutes=15):
        self.model_dir = model_dir
        self.model_path = f"{model_dir}/health_model.pkl"
        self.model = None
        self.lookahead_minutes = lookahead_minutes
        self.trained_on_real_incidents = False
        os.makedirs(model_dir, exist_ok=True)

    def _row_from_snapshot(self, m):
        return [
            getattr(m, 'cpu_usage', 0) or 0,
            getattr(m, 'memory_usage', 0) or 0,
            getattr(m, 'disk_usage', 0) or 0,
            getattr(m, 'network_rx', 0) or 0,
            getattr(m, 'network_tx', 0) or 0,
            getattr(m, 'load_1min', 0) or 0,
            getattr(m, 'load_5min', 0) or 0,
        ]

    def _row_from_dict(self, m: dict):
        return [
            m.get('cpu_usage', 0) or 0,
            m.get('memory_usage', 0) or 0,
            m.get('disk_usage', 0) or 0,
            m.get('network_rx', m.get('network_rx_bytes', 0)) or 0,
            m.get('network_tx', 0) or 0,
            m.get('load_1min', 0) or 0,
            m.get('load_5min', 0) or 0,
        ]

    def train(self, snapshots, alerts):
        """
        snapshots: list of MetricsSnapshot ORM rows for one instance.
        alerts: list of Alert ORM rows for the same instance (full history
                is fine - only triggered_at/severity are used).
        """
        sorted_snaps, any_alert_labels, _ = build_alert_based_labels(
            snapshots, alerts, lookahead_minutes=self.lookahead_minutes
        )

        X = np.array([self._row_from_snapshot(m) for m in sorted_snaps], dtype=float)
        # label=1 means "alert happened soon" (i.e. unhealthy-soon)
        y = np.array(any_alert_labels)

        self.trained_on_real_incidents = has_both_classes(y.tolist())

        if not self.trained_on_real_incidents:
            # Cold start: this instance's real alert history is all one
            # class (most commonly: no alerts have ever fired yet). Add one
            # synthetic sample of the opposite class purely so the
            # classifier can fit - predictions will correctly skew towards
            # "healthy" until real incidents start accumulating.
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
        p_alert_soon = float(proba[classes.index(1)]) if 1 in classes else 0.0

        health_score = round(100 * (1 - p_alert_soon), 2)

        return {
            "health_score": health_score,
            "alert_risk_probability": round(p_alert_soon, 3),
            "trained_on_real_incidents": self.trained_on_real_incidents,
        }


# Default/fallback instance (per-instance models are created via
# app.ml_models.training_cache.get_or_create_model instead of using this
# shared singleton directly).
health_model = HealthModel()
