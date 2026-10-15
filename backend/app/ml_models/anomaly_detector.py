
"""
Advanced Anomaly Detection System
Isolation Forest + One-Class SVM
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AnomalyDetector:

    def __init__(self, model_dir='ml_data/models'):

        self.model_dir = model_dir

        os.makedirs(model_dir, exist_ok=True)

        self.scaler = StandardScaler()

        self.isolation_forest = IsolationForest(
            contamination=0.08,
            n_estimators=200,
            max_samples='auto',
            random_state=42
        )

        self.one_class_svm = OneClassSVM(
            kernel='rbf',
            gamma='scale',
            nu=0.08
        )

        self.is_trained = False

    def prepare_features(self, metrics_data):

        df = pd.DataFrame(metrics_data)

        if len(df) == 0:
            raise ValueError("No metrics data found")

        features = []

        for _, row in df.iterrows():

            cpu = row.get('cpu_usage', 0)
            memory = row.get('memory_usage', 0)
            disk = row.get('disk_usage', 0)
            network_rx = row.get('network_rx', 0)
            network_tx = row.get('network_tx', 0)

            load1 = row.get('load_1min', 0)
            load5 = row.get('load_5min', 0)
            load15 = row.get('load_15min', 0)

            cpu_memory_ratio = cpu / (memory + 1)

            disk_pressure = disk / 100

            network_total = network_rx + network_tx

            feature_vector = [
                cpu,
                memory,
                disk,
                network_rx,
                network_tx,
                load1,
                load5,
                load15,
                cpu_memory_ratio,
                disk_pressure,
                network_total
            ]

            features.append(feature_vector)

        return np.array(features)

    def train(self, historical_data):

        logger.info("Training anomaly detection models...")

        try:

            X = self.prepare_features(historical_data)

            if len(X) < 20:

                return {
                    'status': 'error',
                    'message': 'Need at least 20 samples for training'
                }

            X_scaled = self.scaler.fit_transform(X)

            self.isolation_forest.fit(X_scaled)

            self.one_class_svm.fit(X_scaled)

            self.is_trained = True

            self.save_models()

            logger.info("Anomaly models trained successfully")

            return {
                'status': 'success',
                'samples_trained': len(X),
                'features_used': X.shape[1],
                'models': [
                    'IsolationForest',
                    'OneClassSVM'
                ]
            }

        except Exception as e:

            logger.error(f"Training failed: {e}")

            return {
                'status': 'error',
                'message': str(e)
            }

    def detect(self, current_metrics):

        try:

            if not self.is_trained:

                loaded = self.load_models()

                if not loaded:

                    return {
                        'status': 'error',
                        'message': 'Models not trained'
                    }

            features = self.prepare_features([current_metrics])

            scaled_features = self.scaler.transform(features)

            iso_prediction = self.isolation_forest.predict(scaled_features)[0]

            svm_prediction = self.one_class_svm.predict(scaled_features)[0]

            iso_score = self.isolation_forest.score_samples(
                scaled_features
            )[0]

            svm_score = self.one_class_svm.score_samples(
                scaled_features
            )[0]

            is_anomaly = (
                iso_prediction == -1 or svm_prediction == -1
            )

            normalized_iso = min(abs(iso_score), 1)

            normalized_svm = min(abs(svm_score), 1)

            confidence = round(
                (normalized_iso + normalized_svm) / 2,
                3
            )

            severity = "normal"

            if is_anomaly:

                if confidence > 0.8:
                    severity = "critical"

                elif confidence > 0.5:
                    severity = "warning"

                else:
                    severity = "minor"

            reasons = self.explain_anomaly(current_metrics)

            return {
                'status': 'success',
                'is_anomaly': bool(is_anomaly),
                'severity': severity,
                'confidence': confidence,
                'iso_score': float(iso_score),
                'svm_score': float(svm_score),
                'reasons': reasons,
                'metrics': {
                    'cpu_usage': current_metrics.get('cpu_usage', 0),
                    'memory_usage': current_metrics.get('memory_usage', 0),
                    'disk_usage': current_metrics.get('disk_usage', 0)
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:

            logger.error(f"Anomaly detection failed: {e}")

            return {
                'status': 'error',
                'message': str(e)
            }

    def explain_anomaly(self, metrics):

        reasons = []

        cpu = metrics.get('cpu_usage', 0)
        memory = metrics.get('memory_usage', 0)
        disk = metrics.get('disk_usage', 0)

        load1 = metrics.get('load_1min', 0)

        if cpu > 90:
            reasons.append("Extremely high CPU usage")

        elif cpu > 75:
            reasons.append("High CPU usage")

        if memory > 90:
            reasons.append("Memory almost full")

        elif memory > 75:
            reasons.append("High memory usage")

        if disk > 90:
            reasons.append("Disk almost full")

        elif disk > 80:
            reasons.append("Disk usage high")

        if load1 > 5:
            reasons.append("System load unusually high")

        if len(reasons) == 0:
            reasons.append("Pattern deviation detected by ML model")

        return reasons

    def save_models(self):

        joblib.dump(
            self.scaler,
            f'{self.model_dir}/anomaly_scaler.pkl'
        )

        joblib.dump(
            self.isolation_forest,
            f'{self.model_dir}/isolation_forest.pkl'
        )

        joblib.dump(
            self.one_class_svm,
            f'{self.model_dir}/one_class_svm.pkl'
        )

        logger.info("Anomaly models saved")

    def load_models(self):

        try:

            self.scaler = joblib.load(
                f'{self.model_dir}/anomaly_scaler.pkl'
            )

            self.isolation_forest = joblib.load(
                f'{self.model_dir}/isolation_forest.pkl'
            )

            self.one_class_svm = joblib.load(
                f'{self.model_dir}/one_class_svm.pkl'
            )

            self.is_trained = True

            logger.info("Anomaly models loaded")

            return True

        except Exception as e:

            logger.error(f"Failed to load anomaly models: {e}")

            return False


anomaly_detector = AnomalyDetector()
