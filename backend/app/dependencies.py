"""
Shared FastAPI dependencies.

Previously this instance-lookup logic was copy-pasted 13+ times across
metrics.py, instances.py, and ml_routes.py (and a couple of endpoints had
a slightly different, buggier version of it). It's centralized here so
there is exactly one place to fix lookup bugs or change behavior.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models


def get_instance_or_404(instance_id: str, db: Session = Depends(get_db)) -> models.Instance:
    """Look up an Instance by numeric primary key `id` or by its string
    `instance_id` field, trying whichever is applicable, and raise a 404
    if nothing matches.

    This is used consistently by every route so that passing either the
    database id or the AWS-style instance id string always works the same
    way everywhere (previously a couple of ML endpoints only supported the
    string form, causing confusing 404s depending on which identifier the
    frontend happened to send).
    """
    instance = None

    if instance_id.isdigit():
        instance = db.query(models.Instance).filter(
            models.Instance.id == int(instance_id)
        ).first()

    if instance is None:
        instance = db.query(models.Instance).filter(
            models.Instance.instance_id == instance_id
        ).first()

    if instance is None:
        raise HTTPException(status_code=404, detail="Instance not found")

    return instance


def get_prometheus_target(instance: models.Instance) -> str:
    """Build the `ip:port` target string Prometheus uses to label a host."""
    return f"{instance.ip_address}:{instance.port}"
