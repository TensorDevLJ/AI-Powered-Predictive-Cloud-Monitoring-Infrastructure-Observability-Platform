from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.services.prometheus import prometheus_client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def collect_metrics_job():
    """
    Collect metrics every minute automatically
    """

    db: Session = SessionLocal()

    try:
        instances = db.query(models.Instance).filter(
            models.Instance.is_monitored == True
        ).all()

        logger.info(f"Collecting metrics for {len(instances)} instances")

        for instance in instances:

            # Must match the "ip:port" target format used everywhere else
            # (metrics.py, ml_routes.py) - passing just the IP meant this
            # scheduled collector queried a different Prometheus target
            # label than the rest of the app, so it never matched real data.
            target = f"{instance.ip_address}:{instance.port}"

            metrics = prometheus_client.get_all_metrics(target)

            snapshot = models.MetricsSnapshot(
                instance_id=instance.id,
                cpu_usage=metrics.get("cpu_usage", 0),
                memory_usage=metrics.get("memory_usage", 0),
                disk_usage=metrics.get("disk_usage", 0),
                network_rx=metrics.get("network_rx", 0),
                network_tx=metrics.get("network_tx", 0),
                network_rx_errors=metrics.get("network_rx_errors", 0),
                network_tx_errors=metrics.get("network_tx_errors", 0),
                load_1min=metrics.get("load_1min", 0),
                load_5min=metrics.get("load_5min", 0),
                load_15min=metrics.get("load_15min", 0),
            )

            db.add(snapshot)

        db.commit()

        logger.info(f"Metrics collected successfully at {datetime.now()}")

    except Exception as e:
        logger.error(f"Scheduler error: {e}")

    finally:
        db.close()


def start_scheduler():

    scheduler.add_job(
        collect_metrics_job,
        trigger='interval',
        minutes=1,
        id='metrics_collector',
        replace_existing=True
    )

    scheduler.start()

    logger.info("Metrics scheduler started")