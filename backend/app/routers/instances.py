"""
Instance management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas, auth
from app.dependencies import get_instance_or_404

router = APIRouter(prefix="/instances", tags=["Instances"])


@router.get("/", response_model=List[schemas.Instance])
async def list_instances(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """List instances.

    Admins see every instance. Regular users only see instances they own.
    Requires authentication (previously this endpoint had an `if/else` that
    ran the identical query in both branches, so ANY unauthenticated caller
    could list every user's instances regardless of ownership).
    """
    query = db.query(models.Instance)

    if not current_user.is_admin:
        query = query.filter(models.Instance.owner_id == current_user.id)

    instances = query.offset(skip).limit(limit).all()

    return instances


@router.get("/{instance_id}", response_model=schemas.Instance)
async def get_instance(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
):
    """Get instance by ID"""
    # Check permissions (only if authenticated)
    if current_user and not current_user.is_admin and instance.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return instance


@router.post("/", response_model=schemas.Instance, status_code=status.HTTP_201_CREATED)
async def add_instance(
    instance: schemas.InstanceCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a new instance"""
    # Check if instance already exists
    existing = db.query(models.Instance).filter(
        models.Instance.instance_id == instance.instance_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance ID already exists"
        )

    # Create new instance
    db_instance = models.Instance(
        **instance.dict(),
        owner_id=current_user.id,
        status="active"
    )

    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)

    return db_instance


@router.put("/{instance_id}", response_model=schemas.Instance)
async def update_instance(
    instance_update: schemas.InstanceUpdate,
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an instance"""
    # Check permissions
    if not current_user.is_admin and instance.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update fields
    update_data = instance_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(instance, field, value)

    db.commit()
    db.refresh(instance)

    return instance


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an instance"""
    # Check permissions
    if not current_user.is_admin and instance.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(instance)
    db.commit()

    return None


@router.get("/{instance_id}/alerts", response_model=List[schemas.Alert])
async def get_instance_alerts(
    active_only: bool = True,
    instance: models.Instance = Depends(get_instance_or_404),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get alerts for an instance"""
    # Check permissions (only if authenticated)
    if current_user and not current_user.is_admin and instance.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = db.query(models.Alert).filter(models.Alert.instance_id == instance.id)

    if active_only:
        query = query.filter(models.Alert.status == "active")

    alerts = query.order_by(models.Alert.triggered_at.desc()).all()

    return alerts
