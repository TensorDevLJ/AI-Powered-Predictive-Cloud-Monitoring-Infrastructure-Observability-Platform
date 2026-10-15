"""
Metrics routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.database import get_db
from app import models, auth
from app.dependencies import get_instance_or_404, get_prometheus_target
from app.services.prometheus import prometheus_client
from app.services.alerting import alert_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/cpu/{instance_id}")
async def get_cpu_metrics(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get CPU metrics for an instance"""
    target = get_prometheus_target(instance)

    cpu_usage = prometheus_client.get_cpu_usage(target)
    cpu_per_core = prometheus_client.get_cpu_per_core(target)
    load_avg = prometheus_client.get_load_average(target)

    alert_service.check_cpu_threshold(db, instance, cpu_usage)

    return {
        "instance_id": instance.instance_id,
        "instance_name": instance.name,
        "timestamp": datetime.utcnow().timestamp(),
        "usage_percent": cpu_usage,
        "per_core": cpu_per_core,
        "load_1min": load_avg.get("load_1min", 0),
        "load_5min": load_avg.get("load_5min", 0),
        "load_15min": load_avg.get("load_15min", 0)
    }


@router.get("/memory/{instance_id}")
async def get_memory_metrics(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get memory metrics for an instance"""
    target = get_prometheus_target(instance)
    memory_metrics = prometheus_client.get_memory_usage(target)

    alert_service.check_memory_threshold(db, instance, memory_metrics.get("usage_percent", 0))

    return {
        "instance_id": instance.instance_id,
        "instance_name": instance.name,
        "timestamp": datetime.utcnow().timestamp(),
        **memory_metrics
    }


@router.get("/disk/{instance_id}")
async def get_disk_metrics(
    mount_point: str = Query(default="/", description="Disk mount point"),
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get disk metrics for an instance"""
    target = get_prometheus_target(instance)
    disk_metrics = prometheus_client.get_disk_usage(target, mount_point)

    alert_service.check_disk_threshold(db, instance, disk_metrics.get("usage_percent", 0))

    return {
        "instance_id": instance.instance_id,
        "instance_name": instance.name,
        "timestamp": datetime.utcnow().timestamp(),
        **disk_metrics
    }


@router.get("/network/{instance_id}")
async def get_network_metrics(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
):
    """Get network metrics for an instance"""
    target = get_prometheus_target(instance)
    network_metrics = prometheus_client.get_network_usage(target)

    return {
        "instance_id": instance.instance_id,
        "instance_name": instance.name,
        "timestamp": datetime.utcnow().timestamp(),
        **network_metrics
    }


@router.get("/load/{instance_id}")
async def get_load_metrics(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
):
    """Get load average for an instance"""
    target = get_prometheus_target(instance)
    load_avg = prometheus_client.get_load_average(target)
    uptime = prometheus_client.get_uptime(target)

    return {
        "instance_id": instance.instance_id,
        "instance_name": instance.name,
        "timestamp": datetime.utcnow().timestamp(),
        "uptime_seconds": uptime,
        **load_avg
    }


@router.get("/all/{instance_id}")
async def get_all_metrics(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get all metrics for an instance"""
    target = get_prometheus_target(instance)

    # Collect all metrics
    cpu_usage = prometheus_client.get_cpu_usage(target)
    cpu_per_core = prometheus_client.get_cpu_per_core(target)
    load_avg = prometheus_client.get_load_average(target)
    memory_metrics = prometheus_client.get_memory_usage(target)
    disk_metrics = prometheus_client.get_disk_usage(target)
    network_metrics = prometheus_client.get_network_usage(target)
    uptime = prometheus_client.get_uptime(target)

    # Check thresholds
    alert_service.check_cpu_threshold(db, instance, cpu_usage)
    alert_service.check_memory_threshold(db, instance, memory_metrics.get("usage_percent", 0))
    alert_service.check_disk_threshold(db, instance, disk_metrics.get("usage_percent", 0))

    # Persist a snapshot for ML training / historical analysis
    snapshot = models.MetricsSnapshot(
        instance_id=instance.id,
        timestamp=datetime.utcnow(),
        cpu_usage=cpu_usage,
        memory_usage=memory_metrics.get("usage_percent", 0),
        disk_usage=disk_metrics.get("usage_percent", 0),
        network_rx=network_metrics.get("rx_bytes", 0),
        network_tx=network_metrics.get("tx_bytes", 0),
        load_1min=load_avg.get("load_1min", 0),
        load_5min=load_avg.get("load_5min", 0),
        load_15min=load_avg.get("load_15min", 0),
    )

    db.add(snapshot)
    db.commit()

    return {
        "instance_id": instance.instance_id,
        "instance_name": instance.name,
        "timestamp": datetime.utcnow().timestamp(),
        "cpu": {
            "usage_percent": cpu_usage,
            "per_core": cpu_per_core,
            **load_avg
        },
        "memory": memory_metrics,
        "disk": disk_metrics,
        "network": network_metrics,
        "uptime_seconds": uptime
    }


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard summary with aggregated metrics"""
    instances = db.query(models.Instance).filter(models.Instance.is_monitored == True).all()

    total_instances = len(instances)
    active_instances = sum(1 for i in instances if i.status == "active")

    # Get alerts
    active_alerts = alert_service.get_active_alerts(db)
    total_alerts = len(active_alerts)
    critical_alerts = sum(1 for a in active_alerts if a.severity == "critical")

    # Calculate average metrics
    cpu_values = []
    memory_values = []
    disk_values = []

    for instance in instances:
        if instance.status == "active":
            target = get_prometheus_target(instance)
            try:
                cpu_values.append(prometheus_client.get_cpu_usage(target))
                memory_metrics = prometheus_client.get_memory_usage(target)
                memory_values.append(memory_metrics.get("usage_percent", 0))
                disk_metrics = prometheus_client.get_disk_usage(target)
                disk_values.append(disk_metrics.get("usage_percent", 0))
            except Exception:
                pass

    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
    avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
    avg_disk = sum(disk_values) / len(disk_values) if disk_values else 0

    return {
        "total_instances": total_instances,
        "active_instances": active_instances,
        "total_alerts": total_alerts,
        "critical_alerts": critical_alerts,
        "average_cpu": round(avg_cpu, 2),
        "average_memory": round(avg_memory, 2),
        "average_disk": round(avg_disk, 2)
    }
