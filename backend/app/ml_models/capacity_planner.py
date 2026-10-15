"""
Advanced Capacity Planning & AI Auto-Scaling

`analyze_capacity()` projects CPU/memory/disk usage `forecast_days` ahead.
Previously this used ONLY a linear trend (`np.polyfit` slope projected
forward) - a legitimate statistical technique, but not a trained model,
despite being advertised as part of the "ML-Powered Features".

Now it first tries a genuinely trained day-level RandomForestRegressor
(fit on daily-aggregated historical usage, predicting N days ahead) when
there's enough daily history (>= MIN_DAYS_FOR_ML distinct days). When
there isn't enough daily history yet (e.g. a freshly-added instance with
only a few hours of data), it falls back to the linear-trend projection,
and `projection_method` in the response says exactly which one was used -
no pretending a trend fallback is a trained model, or vice versa.

`get_autoscaling_recommendation()` already accepted real `cpu_prediction`/
`memory_prediction`/`failure_prediction` ML outputs as optional params -
but the API route never actually passed them in, so it silently fell back
to using raw instantaneous metrics as if they were "predictions". That
wiring is fixed in app/routers/ml_routes.py alongside this file.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
import logging

logger = logging.getLogger(__name__)

MIN_DAYS_FOR_ML_FORECAST = 5


class CapacityPlanner:

    def __init__(self):

        self.thresholds = {
            'cpu_scale_up': 80,
            'memory_scale_up': 85,
            'disk_scale_up': 90,
            'cpu_scale_down': 25,
            'memory_scale_down': 35
        }

    def _daily_aggregates(self, historical_metrics):
        """historical_metrics: list of dicts with 'timestamp' + metric
        keys. Returns a DataFrame of one row per calendar day (mean of
        each metric that day), or None if timestamps aren't available."""
        rows = [m for m in historical_metrics if m.get('timestamp') is not None]
        if len(rows) < 10:
            return None

        df = pd.DataFrame(rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date

        agg = {}
        for col in ('cpu_usage', 'memory_usage', 'disk_usage'):
            if col in df.columns:
                agg[col] = 'mean'
        if not agg:
            return None

        daily = df.groupby('date').agg(agg).reset_index().sort_values('date')
        return daily

    def _train_daily_forecast(self, daily_df, column, forecast_days):
        """Fit a small RandomForestRegressor on day-index -> daily mean
        value, project `forecast_days` ahead, return the mean of the
        projected horizon. Returns None if not enough distinct days or the
        column isn't present."""
        if daily_df is None or column not in daily_df.columns:
            return None
        if len(daily_df) < MIN_DAYS_FOR_ML_FORECAST:
            return None

        y = daily_df[column].values.astype(float)
        X = np.arange(len(y)).reshape(-1, 1)

        model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        model.fit(X, y)

        future_X = np.arange(len(y), len(y) + max(1, forecast_days)).reshape(-1, 1)
        preds = model.predict(future_X)
        return float(np.mean(preds))

    def analyze_capacity(
        self,
        historical_metrics,
        forecast_days=7
    ):

        try:

            if len(historical_metrics) < 20:

                return {
                    'status': 'error',
                    'message': 'Need at least 20 samples'
                }

            cpu_values = [
                m.get('cpu_usage', 0)
                for m in historical_metrics
            ]

            memory_values = [
                m.get('memory_usage', 0)
                for m in historical_metrics
            ]

            disk_values = [
                m.get('disk_usage', 0)
                for m in historical_metrics
            ]

            cpu_trend = self.calculate_trend(cpu_values)
            memory_trend = self.calculate_trend(memory_values)
            disk_trend = self.calculate_trend(disk_values)

            trend_cpu_projection = float(np.mean(cpu_values) + (cpu_trend * forecast_days))
            trend_memory_projection = float(np.mean(memory_values) + (memory_trend * forecast_days))
            trend_disk_projection = float(np.mean(disk_values) + (disk_trend * forecast_days))

            # Try a genuinely trained day-level forecaster first.
            daily_df = self._daily_aggregates(historical_metrics)
            ml_cpu = self._train_daily_forecast(daily_df, 'cpu_usage', forecast_days)
            ml_memory = self._train_daily_forecast(daily_df, 'memory_usage', forecast_days)
            ml_disk = self._train_daily_forecast(daily_df, 'disk_usage', forecast_days)

            used_ml = ml_cpu is not None and ml_memory is not None and ml_disk is not None

            if used_ml:
                cpu_projection = ml_cpu
                memory_projection = ml_memory
                disk_projection = ml_disk
                projection_method = 'trained_ml'
                distinct_days = int(len(daily_df))
            else:
                cpu_projection = trend_cpu_projection
                memory_projection = trend_memory_projection
                disk_projection = trend_disk_projection
                projection_method = 'trend_fallback'
                distinct_days = int(len(daily_df)) if daily_df is not None else 0

            scaling_needed = bool(
                cpu_projection > 85
                or memory_projection > 85
                or disk_projection > 90
            )

            infrastructure_pressure = self.calculate_pressure(
                cpu_projection,
                memory_projection,
                disk_projection
            )

            recommendations = self.generate_recommendations(
                cpu_projection,
                memory_projection,
                disk_projection
            )

            cost_optimization = self.calculate_cost_optimization(
                cpu_values,
                memory_values
            )

            return {
                'status': 'success',
                'scaling_needed': scaling_needed,
                'forecast_days': forecast_days,
                'projection_method': projection_method,
                'distinct_days_of_history': distinct_days,
                'min_days_for_ml_forecast': MIN_DAYS_FOR_ML_FORECAST,
                'infrastructure_pressure': infrastructure_pressure,
                'projections': {
                    'cpu_projection': round(cpu_projection, 2),
                    'memory_projection': round(memory_projection, 2),
                    'disk_projection': round(disk_projection, 2)
                },
                'trends': {
                    'cpu_trend': round(cpu_trend, 4),
                    'memory_trend': round(memory_trend, 4),
                    'disk_trend': round(disk_trend, 4)
                },
                'recommendations': recommendations,
                'cost_optimization': cost_optimization,
                'analysis_time': datetime.now().isoformat()
            }

        except Exception as e:

            logger.error(f"Capacity analysis failed: {e}")

            return {
                'status': 'error',
                'message': str(e)
            }

    def get_autoscaling_recommendation(
        self,
        current_metrics,
        cpu_prediction=None,
        memory_prediction=None,
        failure_prediction=None
    ):

        try:

            cpu = current_metrics.get(
                'cpu_usage',
                0
            )

            memory = current_metrics.get(
                'memory_usage',
                0
            )

            disk = current_metrics.get(
                'disk_usage',
                0
            )

            actions = []

            severity = "normal"

            predicted_cpu = cpu

            predicted_memory = memory

            used_real_predictions = False

            if cpu_prediction:

                predictions = cpu_prediction.get(
                    'predictions',
                    []
                )

                if predictions:
                    predicted_cpu = max([
                        p.get('predicted_cpu', cpu)
                        for p in predictions
                    ])
                    used_real_predictions = True

            if memory_prediction:

                predictions = memory_prediction.get(
                    'predictions',
                    []
                )

                if predictions:
                    predicted_memory = max([
                        p.get(
                            'predicted_memory',
                            memory
                        )
                        for p in predictions
                    ])
                    used_real_predictions = True

            failure_probability = 0

            if failure_prediction:

                raw_prob = failure_prediction.get(
                    'failure_probability',
                    0
                )
                # failure_model reports a 0-1 probability; normalize to a
                # 0-100 scale to match the thresholds used below.
                failure_probability = raw_prob * 100 if raw_prob <= 1 else raw_prob

            # Scale Up Logic
            if (
                predicted_cpu > 85
                or predicted_memory > 85
                or failure_probability > 70
            ):

                severity = "critical"

                actions.append({
                    'action': 'scale_up',
                    'reason': (
                        f'Predicted CPU: {predicted_cpu:.2f}% '
                        f'Predicted Memory: {predicted_memory:.2f}%'
                    ),
                    'recommended_instance': (
                        self.recommend_instance_type(
                            predicted_cpu,
                            predicted_memory
                        )
                    ),
                    'estimated_instances_needed': (
                        self.calculate_instances_needed(
                            predicted_cpu,
                            predicted_memory
                        )
                    ),
                    'urgency': 'immediate'
                })

            # Scale Down Logic
            elif (
                cpu < 30
                and memory < 35
            ):

                severity = "optimization"

                actions.append({
                    'action': 'scale_down',
                    'reason': (
                        'Resources underutilized'
                    ),
                    'estimated_cost_saving': (
                        '30-50%'
                    ),
                    'urgency': 'consider'
                })

            # Stable
            else:

                actions.append({
                    'action': 'maintain',
                    'reason': (
                        'Infrastructure stable'
                    ),
                    'urgency': 'none'
                })

            return {
                'status': 'success',
                'severity': severity,
                'actions': actions,
                'used_real_ml_predictions': used_real_predictions,
                'predicted_cpu': round(predicted_cpu, 2),
                'predicted_memory': round(
                    predicted_memory,
                    2
                ),
                'failure_probability': round(failure_probability, 2),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:

            logger.error(f"Autoscaling failed: {e}")

            return {
                'status': 'error',
                'message': str(e)
            }

    def calculate_trend(self, values):

        if len(values) < 2:
            return 0

        x = np.arange(len(values))

        slope, intercept = np.polyfit(
            x,
            values,
            1
        )

        return float(slope)

    def calculate_pressure(
        self,
        cpu,
        memory,
        disk
    ):

        avg_pressure = (
            cpu + memory + disk
        ) / 3

        if avg_pressure > 90:
            return "critical"

        elif avg_pressure > 75:
            return "high"

        elif avg_pressure > 50:
            return "moderate"

        return "low"

    def generate_recommendations(
        self,
        cpu,
        memory,
        disk
    ):

        recommendations = []

        if cpu > 85:

            recommendations.append(
                "Increase compute resources"
            )

        if memory > 85:

            recommendations.append(
                "Upgrade RAM capacity"
            )

        if disk > 90:

            recommendations.append(
                "Expand storage immediately"
            )

        if len(recommendations) == 0:

            recommendations.append(
                "Infrastructure capacity healthy"
            )

        return recommendations

    def calculate_cost_optimization(
        self,
        cpu_values,
        memory_values
    ):

        avg_cpu = np.mean(cpu_values)

        avg_memory = np.mean(memory_values)

        if avg_cpu < 30 and avg_memory < 40:

            return {
                'optimization_possible': True,
                'recommendation': (
                    'Downsize instance type'
                ),
                'estimated_savings': '30-50%'
            }

        return {
            'optimization_possible': False,
            'recommendation': (
                'Current sizing appropriate'
            )
        }

    def recommend_instance_type(
        self,
        cpu,
        memory
    ):

        pressure = max(cpu, memory)

        if pressure > 95:
            return "c5.2xlarge"

        elif pressure > 85:
            return "c5.xlarge"

        elif pressure > 70:
            return "t3.large"

        return "Current instance sufficient"

    def calculate_instances_needed(
        self,
        cpu,
        memory
    ):

        pressure = max(cpu, memory)

        if pressure > 95:
            return 3

        elif pressure > 85:
            return 2

        elif pressure > 70:
            return 1

        return 0


capacity_planner = CapacityPlanner()
