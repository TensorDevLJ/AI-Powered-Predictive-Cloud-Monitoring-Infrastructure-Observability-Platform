"""
Advanced Root Cause Analysis Engine
AI + Rule-Based Infrastructure Diagnostics

The rule engine below captures real operational knowledge (which metric
patterns correlate with which infrastructure problems) and is kept
deliberately, for two reasons:

  1. It's the explainable fallback used when no trained model exists yet
     for an instance - interpretable conditions, fixed severities and
     actionable recommendations, always available immediately.
  2. It's the WEAK-SUPERVISION label generator used to bootstrap training
     data for a real classifier (see `train()` / `predict_ml()` below) -
     a standard ML technique for problems with no hand-labeled incident
     ground truth available.

`analyze()` always returns the rule-based `identified_causes` (so
explanations/recommendations are always available), and additionally
includes `ml_predicted_causes` once a classifier has been trained for the
instance - a RandomForest's own learned probability estimate for each
cause, generalized from the rule-bootstrapped historical data rather than
hard cutoffs alone. This lets the system flag a cause building up near a
threshold (e.g. a memory-leak-like pattern) even before the rule's exact
condition is literally crossed in the current reading.

NOTE: a previous bug in the "DDoS Attack" rule checked a
`network_rx_bytes` key that was never actually present in the metrics
dicts passed in anywhere in this codebase (the real key is `network_rx`),
so that rule could never fire regardless of actual traffic. Fixed below.
"""
from datetime import datetime
import logging
import os

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    'cpu_usage', 'memory_usage', 'disk_usage',
    'network_rx', 'network_tx', 'network_rx_errors', 'network_tx_errors',
    'disk_write_bytes', 'load_1min', 'load_5min',
]


class RootCauseAnalyzer:

    def __init__(self, model_dir='ml_data/models/root_cause_analyzer'):
        self.rules = self.initialize_rules()
        self.cause_names = [r['name'] for r in self.rules]
        self.model_dir = model_dir
        self.model_path = f"{model_dir}/root_cause_classifier.pkl"
        self.model = None
        os.makedirs(model_dir, exist_ok=True)

    def initialize_rules(self):

        return [

            {
                'name': 'DDoS Attack',
                'severity': 'critical',
                'confidence': 0.90,
                'condition': lambda m:
                    m.get('network_rx', 0) > 1_000_000_000
                    and m.get('cpu_usage', 0) > 85,

                'recommendation': (
                    'Enable WAF, rate limiting, '
                    'traffic filtering, and DDoS protection'
                )
            },

            {
                'name': 'Memory Leak',
                'severity': 'high',
                'confidence': 0.85,
                'condition': lambda m:
                    m.get('memory_usage', 0) > 90
                    and m.get('cpu_usage', 0) < 50,

                'recommendation': (
                    'Investigate application memory allocation '
                    'and restart affected services'
                )
            },

            {
                'name': 'CPU Bottleneck',
                'severity': 'critical',
                'confidence': 0.92,
                'condition': lambda m:
                    m.get('cpu_usage', 0) > 92
                    and m.get('load_1min', 0) > 8,

                'recommendation': (
                    'Optimize high CPU processes '
                    'or scale compute resources'
                )
            },

            {
                'name': 'Disk I/O Saturation',
                'severity': 'high',
                'confidence': 0.80,
                'condition': lambda m:
                    m.get('disk_usage', 0) > 90
                    or m.get('disk_write_bytes', 0) > 100_000_000,

                'recommendation': (
                    'Upgrade storage performance '
                    'or clean unnecessary files'
                )
            },

            {
                'name': 'Network Congestion',
                'severity': 'medium',
                'confidence': 0.75,
                'condition': lambda m:
                    (
                        m.get('network_rx_errors', 0)
                        + m.get('network_tx_errors', 0)
                    ) > 100,

                'recommendation': (
                    'Inspect bandwidth, packet loss, '
                    'and network interface configuration'
                )
            },

            {
                'name': 'Infrastructure Overload',
                'severity': 'critical',
                'confidence': 0.88,
                'condition': lambda m:
                    (
                        m.get('cpu_usage', 0)
                        + m.get('memory_usage', 0)
                        + m.get('disk_usage', 0)
                    ) / 3 > 85,

                'recommendation': (
                    'Scale infrastructure immediately '
                    'or distribute workloads'
                )
            },

            {
                'name': 'Application Instability',
                'severity': 'high',
                'confidence': 0.78,
                'condition': lambda m:
                    m.get('load_5min', 0) > 6
                    and m.get('memory_usage', 0) > 75,

                'recommendation': (
                    'Investigate unstable applications '
                    'or memory-intensive services'
                )
            }
        ]

    def _feature_row(self, m: dict):
        return [m.get(f, 0) or 0 for f in FEATURE_NAMES]

    def train(self, historical_metrics):
        """
        historical_metrics: list of dicts with FEATURE_NAMES keys, one per
        historical snapshot.

        Labels are generated by evaluating the rule engine against each
        historical row (weak supervision / rule distillation - there is no
        hand-labeled "this incident's true cause was X" dataset available,
        so the rules' domain knowledge is used to bootstrap one). The
        trained classifier then learns a smoothed, generalized version of
        those rules from the actual feature distributions instead of being
        limited to hard cutoffs only.
        """
        if not historical_metrics:
            return {"status": "error", "message": "No historical data"}

        X = np.array([self._feature_row(m) for m in historical_metrics], dtype=float)

        # One binary label column per rule/cause.
        columns = []
        for rule in self.rules:
            col = []
            for m in historical_metrics:
                try:
                    col.append(1 if rule['condition'](m) else 0)
                except Exception:
                    col.append(0)
            columns.append(col)
        Y = np.array(columns).T  # shape: (n_samples, n_rules)

        base = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        self.model = MultiOutputClassifier(base)
        self.model.fit(X, Y)
        joblib.dump(self.model, self.model_path)

        causes_with_real_signal = int((Y.sum(axis=0) > 0).sum())
        return {
            "status": "trained",
            "samples": int(len(X)),
            "causes_with_real_signal": causes_with_real_signal,
            "total_causes": len(self.rules),
        }

    def predict_ml(self, metrics: dict):
        """Trained classifier's probability estimate for each cause, or
        None if no model has been trained for this instance yet."""
        if self.model is None:
            if not os.path.exists(self.model_path):
                return None
            self.model = joblib.load(self.model_path)

        X = np.array([self._feature_row(metrics)], dtype=float)
        try:
            proba_per_output = self.model.predict_proba(X)
        except Exception as e:
            logger.warning(f"Root cause ML prediction failed: {e}")
            return None

        results = []
        for idx, name in enumerate(self.cause_names):
            proba = proba_per_output[idx]
            classes = list(self.model.estimators_[idx].classes_)
            p = float(proba[0][classes.index(1)]) if 1 in classes else 0.0
            results.append({'cause': name, 'ml_confidence': round(p, 3)})

        results.sort(key=lambda r: r['ml_confidence'], reverse=True)
        return results

    def analyze(
        self,
        metrics,
        anomaly_result=None,
        failure_prediction=None
    ):

        try:

            identified_causes = []

            for rule in self.rules:

                try:

                    if rule['condition'](metrics):

                        identified_causes.append({
                            'cause': rule['name'],
                            'severity': rule['severity'],
                            'confidence': rule['confidence'],
                            'recommendation': (
                                rule['recommendation']
                            ),
                            'source': 'rule',
                        })

                except Exception:
                    continue

            # Add anomaly context
            if (
                anomaly_result
                and anomaly_result.get('is_anomaly')
            ):

                identified_causes.append({
                    'cause': 'ML Detected Behavioral Anomaly',
                    'severity': anomaly_result.get(
                        'severity',
                        'warning'
                    ),
                    'confidence': anomaly_result.get(
                        'confidence',
                        0.75
                    ),
                    'recommendation': (
                        'Investigate unusual '
                        'system behavior patterns'
                    ),
                    'source': 'ml',
                })

            # Add failure prediction context
            if failure_prediction:

                probability = failure_prediction.get(
                    'failure_probability',
                    0
                )

                if probability > 0.7:

                    identified_causes.append({
                        'cause': 'Predicted Infrastructure Failure',
                        'severity': 'critical',
                        'confidence': probability,
                        'recommendation': (
                            'Immediate intervention required'
                        ),
                        'source': 'ml',
                    })

            identified_causes.sort(
                key=lambda x: x['confidence'],
                reverse=True
            )

            primary_cause = (
                identified_causes[0]
                if identified_causes
                else None
            )

            summary = self.generate_summary(
                primary_cause
            )

            infrastructure_state = self.determine_state(
                identified_causes
            )

            # Trained classifier's own probability estimate per cause,
            # generalized from rule-bootstrapped historical data. None
            # until the instance has been trained at least once.
            ml_predicted_causes = self.predict_ml(metrics)

            return {
                'status': 'success',
                'infrastructure_state': (
                    infrastructure_state
                ),
                'identified_causes': identified_causes,
                'primary_cause': primary_cause,
                'ml_predicted_causes': ml_predicted_causes,
                'summary': summary,
                'recommendation_count': (
                    len(identified_causes)
                ),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:

            logger.error(
                f"Root cause analysis failed: {e}"
            )

            return {
                'status': 'error',
                'message': str(e)
            }

    def generate_summary(self, primary_cause):

        if not primary_cause:

            return (
                "No critical infrastructure issues detected"
            )

        return (
            f"Primary issue detected: "
            f"{primary_cause['cause']} "
            f"with confidence "
            f"{primary_cause['confidence'] * 100:.1f}%"
        )

    def determine_state(self, causes):

        if not causes:
            return "healthy"

        severities = [
            c['severity']
            for c in causes
        ]

        if 'critical' in severities:
            return "critical"

        if 'high' in severities:
            return "warning"

        return "stable"


# Default/fallback instance (per-instance models are created via
# app.ml_models.training_cache.get_or_create_model instead of using this
# shared singleton directly for training, though analyze() can be called
# on it directly for rule-based-only results).
root_cause_analyzer = RootCauseAnalyzer()
