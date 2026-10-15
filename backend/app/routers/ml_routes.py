"""
ML-Enhanced API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, auth
from app.dependencies import get_instance_or_404, get_prometheus_target
from app.ml_models.anomaly_detector import anomaly_detector
from app.ml_models.cpu_predictor import cpu_predictor
from app.ml_models.memory_predictor import memory_predictor
from app.ml_models.root_cause_analyzer import root_cause_analyzer, RootCauseAnalyzer
from app.ml_models.capacity_planner import capacity_planner
from app.services.prometheus import prometheus_client
from app.ml_models.health_model import HealthModel
from app.ml_models.failure_model import FailureModel
from app.ml_models.training_cache import get_or_create_model, train_if_stale
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

MIN_TRAINING_SAMPLES = 10


@router.post("/anomaly/train/{instance_id}")
async def train_anomaly_detector(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Train anomaly detection model for an instance"""
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id,
        models.MetricsSnapshot.timestamp >= datetime.utcnow() - timedelta(days=7)
    ).all()

    if len(historical_data) < MIN_TRAINING_SAMPLES:
        raise HTTPException(status_code=400, detail="Insufficient historical data (need at least 10 samples)")

    training_data = [{
        'cpu_usage': m.cpu_usage,
        'memory_usage': m.memory_usage,
        'disk_usage': m.disk_usage,
        'network_rx': m.network_rx,
        'network_tx': m.network_tx,
        'load_1min': m.load_1min,
        'load_5min': m.load_5min,
        'load_15min': m.load_15min
    } for m in historical_data]

    result = anomaly_detector.train(training_data)

    return {
        **result,
        'instance_id': instance.instance_id,
        'instance_name': instance.name
    }


@router.get("/anomaly/detect/{instance_id}")
async def detect_anomaly(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Detect anomalies in current metrics"""
    target = get_prometheus_target(instance)
    cpu_usage = prometheus_client.get_cpu_usage(target)
    memory_metrics = prometheus_client.get_memory_usage(target)
    disk_metrics = prometheus_client.get_disk_usage(target)
    network_metrics = prometheus_client.get_network_usage(target)
    load_avg = prometheus_client.get_load_average(target)

    current_metrics = {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_metrics.get('usage_percent', 0),
        'disk_usage': disk_metrics.get('usage_percent', 0),
        'network_rx': network_metrics.get('rx_bytes', 0),
        'network_tx': network_metrics.get('tx_bytes', 0),
        'load_1min': load_avg.get('load_1min', 0),
        'load_5min': load_avg.get('load_5min', 0),
        'load_15min': load_avg.get('load_15min', 0)
    }

    result = anomaly_detector.detect(current_metrics)

    return {
        **result,
        'instance_id': instance.instance_id,
        'instance_name': instance.name,
        'current_metrics': current_metrics
    }


@router.post("/cpu/train/{instance_id}")
async def train_cpu_predictor(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Train CPU prediction model"""
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id,
        models.MetricsSnapshot.timestamp >= datetime.utcnow() - timedelta(days=7)
    ).all()

    if len(historical_data) < MIN_TRAINING_SAMPLES:
        raise HTTPException(status_code=400, detail="Insufficient data")

    training_data = [{
        'timestamp': m.timestamp,
        'cpu_usage': m.cpu_usage
    } for m in historical_data]

    result = cpu_predictor.train(training_data)
    return result


@router.get("/cpu/predict/{instance_id}")
async def predict_cpu(
    minutes: int = 30,
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Predict CPU usage for next N minutes"""
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    formatted_data = [
        {"timestamp": m.timestamp, "cpu_usage": m.cpu_usage}
        for m in historical_data
    ]

    predictions = cpu_predictor.predict(formatted_data, minutes_ahead=minutes)

    return {
        **predictions,
        'instance_id': instance.instance_id,
        'instance_name': instance.name
    }


@router.post("/memory/train/{instance_id}")
async def train_memory_predictor(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Train memory prediction model"""
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id,
        models.MetricsSnapshot.timestamp >= datetime.utcnow() - timedelta(days=7)
    ).all()

    if len(historical_data) < MIN_TRAINING_SAMPLES:
        raise HTTPException(status_code=400, detail="Insufficient data")

    training_data = [{
        'timestamp': m.timestamp,
        'memory_usage': m.memory_usage
    } for m in historical_data]

    result = memory_predictor.train(training_data)
    return result


@router.get("/memory/predict/{instance_id}")
async def predict_memory(
    minutes: int = 30,
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Predict memory usage"""
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    formatted_data = [
        {"timestamp": m.timestamp, "memory_usage": m.memory_usage}
        for m in historical_data
    ]

    predictions = memory_predictor.predict(formatted_data, minutes_ahead=minutes)

    return {
        **predictions,
        'instance_id': instance.instance_id,
        'instance_name': instance.name
    }


@router.get("/memory/leak-detection/{instance_id}")
async def detect_memory_leak(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Detect memory leaks"""
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id,
        models.MetricsSnapshot.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).all()

    if len(historical_data) < MIN_TRAINING_SAMPLES:
        raise HTTPException(status_code=400, detail="Insufficient data")

    data = [{'timestamp': m.timestamp, 'memory_usage': m.memory_usage} for m in historical_data]
    result = memory_predictor.detect_memory_leak(data)

    return {
        **result,
        'instance_id': instance.instance_id,
        'instance_name': instance.name
    }


@router.get("/health-score/{instance_id}")
async def get_health_score(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db)
):
    """Get health score for an instance.

    The score is `100 * P(no alert within the next 15 minutes)`, predicted
    by a classifier trained on this instance's real Alert history (see
    health_model.py / label_generation.py) - not a fixed CPU/memory/disk
    formula. `trainedOnRealIncidents` tells you whether the score is
    actually backed by real recorded incidents yet, or is still using the
    cold-start fallback because this instance hasn't had any alerts yet.
    """
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    if len(historical_data) < MIN_TRAINING_SAMPLES:
        raise HTTPException(status_code=400, detail="Not enough data for ML")

    alerts = db.query(models.Alert).filter(models.Alert.instance_id == instance.id).all()

    target = get_prometheus_target(instance)
    current_metrics = {
        'cpu_usage': prometheus_client.get_cpu_usage(target),
        'memory_usage': prometheus_client.get_memory_usage(target).get('usage_percent', 0),
        'disk_usage': prometheus_client.get_disk_usage(target).get('usage_percent', 0),
        'network_rx': prometheus_client.get_network_usage(target).get('rx_bytes', 0),
        'network_tx': prometheus_client.get_network_usage(target).get('tx_bytes', 0),
        'load_1min': prometheus_client.get_load_average(target).get('load_1min', 0),
        'load_5min': prometheus_client.get_load_average(target).get('load_5min', 0),
    }

    # Per-instance model, retrained at most once every few minutes instead
    # of on every single request (see training_cache.py for why).
    health_model = get_or_create_model(HealthModel, "health_model", instance.id)
    train_if_stale(health_model, "health_model", instance.id, historical_data, alerts)
    result = health_model.predict(current_metrics)

    return {
        "instanceId": instance.instance_id,
        "healthScore": result.get("health_score", 0),
        "alertRiskProbability": result.get("alert_risk_probability", 0),
        "trainedOnRealIncidents": result.get("trained_on_real_incidents", False),
    }


@router.get("/failure/predict/{instance_id}")
async def predict_failure(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Predict system failure.

    `failureProbability` is predicted by a classifier trained on whether
    this instance actually triggered a CRITICAL alert within 15 minutes
    after each historical snapshot (see failure_model.py /
    label_generation.py) - not a static "cpu>85 or memory>85" rule.
    """
    target = get_prometheus_target(instance)

    cpu_usage = prometheus_client.get_cpu_usage(target)
    memory_metrics = prometheus_client.get_memory_usage(target)
    disk_metrics = prometheus_client.get_disk_usage(target)
    network_metrics = prometheus_client.get_network_usage(target)
    load_avg = prometheus_client.get_load_average(target)

    current_metrics = {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_metrics.get('usage_percent', 0),
        'disk_usage': disk_metrics.get('usage_percent', 0),
        'load_1min': load_avg.get('load_1min', 0),
        'load_5min': load_avg.get('load_5min', 0),
        'network_rx_errors': network_metrics.get('rx_errors', 0),
        'network_tx_errors': network_metrics.get('tx_errors', 0)
    }

    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    if len(historical_data) < MIN_TRAINING_SAMPLES:
        raise HTTPException(status_code=400, detail="Not enough data for ML")

    alerts = db.query(models.Alert).filter(models.Alert.instance_id == instance.id).all()

    failure_model = get_or_create_model(FailureModel, "failure_model", instance.id)
    train_if_stale(failure_model, "failure_model", instance.id, historical_data, alerts)
    result = failure_model.predict(current_metrics)

    return {
        "instanceId": instance.instance_id,
        "instanceName": instance.name,
        "failureProbability": result.get("failure_probability", 0),
        "status": result.get("status", "normal"),
        "trainedOnRealIncidents": result.get("trained_on_real_incidents", False),
    }


@router.get("/autoscale/recommend/{instance_id}")
async def get_autoscale_recommendation(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Get auto-scaling recommendations.

    `capacity_planner.get_autoscaling_recommendation()` is designed to
    weigh real CPU/memory FORECASTS and a real failure probability, not
    just the current instantaneous reading - but this endpoint previously
    never fetched or passed those predictions in, so it silently fell back
    to treating "current metrics" as if they were "predictions". Fixed:
    real CPU/memory predictions and failure probability are now computed
    and passed in. `usedRealMlPredictions` in the response tells you
    whether real forecasts were available and used.
    """
    target = get_prometheus_target(instance)
    cpu_usage = prometheus_client.get_cpu_usage(target)
    memory_metrics = prometheus_client.get_memory_usage(target)
    disk_metrics = prometheus_client.get_disk_usage(target)
    load_avg = prometheus_client.get_load_average(target)

    current_metrics = {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_metrics.get('usage_percent', 0),
        'disk_usage': disk_metrics.get('usage_percent', 0),
    }

    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    cpu_prediction = None
    memory_prediction = None
    failure_prediction = None

    try:
        cpu_hist = [{"timestamp": m.timestamp, "cpu_usage": m.cpu_usage} for m in historical_data]
        memory_hist = [{"timestamp": m.timestamp, "memory_usage": m.memory_usage} for m in historical_data]
        cpu_prediction = cpu_predictor.predict(cpu_hist, minutes_ahead=30)
        memory_prediction = memory_predictor.predict(memory_hist, minutes_ahead=30)
    except Exception as e:
        logger.warning(f"Autoscale: CPU/memory prediction unavailable for instance {instance.id}: {e}")

    if len(historical_data) >= MIN_TRAINING_SAMPLES:
        try:
            alerts = db.query(models.Alert).filter(models.Alert.instance_id == instance.id).all()
            failure_model = get_or_create_model(FailureModel, "failure_model", instance.id)
            train_if_stale(failure_model, "failure_model", instance.id, historical_data, alerts)
            failure_prediction = failure_model.predict({
                'cpu_usage': cpu_usage,
                'memory_usage': memory_metrics.get('usage_percent', 0),
                'disk_usage': disk_metrics.get('usage_percent', 0),
                'load_1min': load_avg.get('load_1min', 0),
            })
        except Exception as e:
            logger.warning(f"Autoscale: failure prediction unavailable for instance {instance.id}: {e}")

    result = capacity_planner.get_autoscaling_recommendation(
        current_metrics,
        cpu_prediction=cpu_prediction,
        memory_prediction=memory_prediction,
        failure_prediction=failure_prediction,
    )

    return {
        **result,
        'instance_id': instance.instance_id,
        'instance_name': instance.name
    }


@router.get("/capacity/plan/{instance_id}")
async def get_capacity_plan(
    forecast_days: int = 14,
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """14-30 day capacity forecast.

    Uses a trained day-level RandomForest forecaster when there's enough
    daily history (>= 5 distinct days); otherwise falls back to a linear
    trend projection. `projectionMethod` in the response says which one
    was actually used - see capacity_planner.py.
    """
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    if len(historical_data) < 20:
        raise HTTPException(status_code=400, detail="Need at least 20 samples for capacity planning")

    historical_metrics = [
        {
            'timestamp': m.timestamp,
            'cpu_usage': m.cpu_usage,
            'memory_usage': m.memory_usage,
            'disk_usage': m.disk_usage,
        }
        for m in historical_data
    ]

    result = capacity_planner.analyze_capacity(historical_metrics, forecast_days=forecast_days)

    return {
        **result,
        'instance_id': instance.instance_id,
        'instance_name': instance.name,
    }


@router.get("/root-cause/analyze/{instance_id}")
async def get_root_cause_analysis(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Root cause analysis: rule-based explanations (always available) plus
    `mlPredictedCauses` from a classifier trained on this instance's own
    history (rules used as weak-supervision labels - see
    root_cause_analyzer.py)."""
    target = get_prometheus_target(instance)
    cpu_metrics = prometheus_client.get_cpu_usage(target)
    memory_metrics = prometheus_client.get_memory_usage(target)
    disk_metrics = prometheus_client.get_disk_usage(target)
    network_metrics = prometheus_client.get_network_usage(target)
    load_avg = prometheus_client.get_load_average(target)

    current_metrics = {
        'cpu_usage': cpu_metrics,
        'memory_usage': memory_metrics.get('usage_percent', 0),
        'disk_usage': disk_metrics.get('usage_percent', 0),
        'network_rx': network_metrics.get('rx_bytes', 0),
        'network_tx': network_metrics.get('tx_bytes', 0),
        'network_rx_errors': network_metrics.get('rx_errors', 0),
        'network_tx_errors': network_metrics.get('tx_errors', 0),
        'disk_write_bytes': disk_metrics.get('write_bytes', 0),
        'load_1min': load_avg.get('load_1min', 0),
        'load_5min': load_avg.get('load_5min', 0),
    }

    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    if len(historical_data) >= MIN_TRAINING_SAMPLES:
        historical_metrics = [
            {
                'cpu_usage': m.cpu_usage,
                'memory_usage': m.memory_usage,
                'disk_usage': m.disk_usage,
                'network_rx': m.network_rx,
                'network_tx': m.network_tx,
                'network_rx_errors': m.network_rx_errors,
                'network_tx_errors': m.network_tx_errors,
                'disk_write_bytes': m.disk_write_bytes,
                'load_1min': m.load_1min,
                'load_5min': m.load_5min,
            }
            for m in historical_data
        ]
        rca_model = get_or_create_model(RootCauseAnalyzer, "root_cause_analyzer", instance.id)
        train_if_stale(rca_model, "root_cause_analyzer", instance.id, historical_metrics)
    else:
        rca_model = root_cause_analyzer

    result = rca_model.analyze(current_metrics)

    return {
        **result,
        'instance_id': instance.instance_id,
        'instance_name': instance.name,
    }


@router.get("/dashboard/ml-summary/{instance_id}")
async def get_ml_dashboard_summary(
    instance: models.Instance = Depends(get_instance_or_404),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user)
):
    """Get comprehensive ML analysis for dashboard"""
    target = get_prometheus_target(instance)
    cpu_usage = prometheus_client.get_cpu_usage(target)
    memory_metrics = prometheus_client.get_memory_usage(target)
    disk_metrics = prometheus_client.get_disk_usage(target)
    network_metrics = prometheus_client.get_network_usage(target)
    load_avg = prometheus_client.get_load_average(target)

    metrics = {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_metrics.get('usage_percent', 0),
        'disk_usage': disk_metrics.get('usage_percent', 0),
        'network_rx': network_metrics.get('rx_bytes', 0),
        'network_tx': network_metrics.get('tx_bytes', 0),
        'network_rx_errors': network_metrics.get('rx_errors', 0),
        'network_tx_errors': network_metrics.get('tx_errors', 0),
        'disk_write_bytes': disk_metrics.get('write_bytes', 0),
        'load_1min': load_avg.get('load_1min', 0),
        'load_5min': load_avg.get('load_5min', 0),
        'cpu_count': 4
    }

    anomaly = anomaly_detector.detect(metrics)
    historical_data = db.query(models.MetricsSnapshot).filter(
        models.MetricsSnapshot.instance_id == instance.id
    ).all()

    if len(historical_data) >= MIN_TRAINING_SAMPLES:
        alerts = db.query(models.Alert).filter(models.Alert.instance_id == instance.id).all()

        health_model = get_or_create_model(HealthModel, "health_model", instance.id)
        failure_model = get_or_create_model(FailureModel, "failure_model", instance.id)
        train_if_stale(health_model, "health_model", instance.id, historical_data, alerts)
        train_if_stale(failure_model, "failure_model", instance.id, historical_data, alerts)
        health = health_model.predict(metrics)
        failure = failure_model.predict(metrics)

        historical_metrics_dicts = [
            {
                'cpu_usage': m.cpu_usage,
                'memory_usage': m.memory_usage,
                'disk_usage': m.disk_usage,
                'network_rx': m.network_rx,
                'network_tx': m.network_tx,
                'network_rx_errors': m.network_rx_errors,
                'network_tx_errors': m.network_tx_errors,
                'disk_write_bytes': m.disk_write_bytes,
                'load_1min': m.load_1min,
                'load_5min': m.load_5min,
            }
            for m in historical_data
        ]
        rca_model = get_or_create_model(RootCauseAnalyzer, "root_cause_analyzer", instance.id)
        train_if_stale(rca_model, "root_cause_analyzer", instance.id, historical_metrics_dicts)
    else:
        health = {"health_score": 50, "status": "insufficient_data"}
        failure = {"failure_probability": 0, "status": "insufficient_data"}
        rca_model = root_cause_analyzer

    root_cause = rca_model.analyze(metrics, anomaly_result=anomaly, failure_prediction=failure)

    try:
        formatted_cpu_data = [
            {"timestamp": m.timestamp, "cpu_usage": m.cpu_usage}
            for m in historical_data
        ]
        formatted_memory_data = [
            {"timestamp": m.timestamp, "memory_usage": m.memory_usage}
            for m in historical_data
        ]

        cpu_pred = cpu_predictor.predict(formatted_cpu_data, minutes_ahead=30)
        memory_pred = memory_predictor.predict(formatted_memory_data, minutes_ahead=30)
    except Exception as e:
        logger.warning(f"ML summary prediction failed for instance {instance.id}: {e}")
        cpu_pred = {'predictions': []}
        memory_pred = {'predictions': []}

    # Feed the REAL CPU/memory forecasts + failure probability into the
    # autoscale decision instead of just current instantaneous metrics.
    autoscale = capacity_planner.get_autoscaling_recommendation(
        metrics,
        cpu_prediction=cpu_pred,
        memory_prediction=memory_pred,
        failure_prediction=failure,
    )
    autoscale_actions = autoscale.get("actions", [])
    autoscale_summary = autoscale_actions[0]["reason"] if autoscale_actions else "No recommendation"

    return {
        "instanceId": instance.instance_id,
        "instanceName": instance.name,
        "healthScore": health.get("health_score", 0),
        "trainedOnRealIncidents": health.get("trained_on_real_incidents", False),
        "failureProbability": failure.get("failure_probability", 0),
        "failureStatus": failure.get("status", "normal"),
        "anomaly": anomaly.get("is_anomaly", False),
        "anomalyConfidence": anomaly.get("confidence", 0),
        "cpuPrediction": cpu_pred.get("predictions", [])[:10],
        "memoryPrediction": memory_pred.get("predictions", [])[:10],
        "autoscaleRecommendation": autoscale_summary,
        "autoscaleActions": autoscale_actions,
        "rootCause": root_cause,
        "timestamp": datetime.now().isoformat()
    }
