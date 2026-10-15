"""
Per-instance model registry + retrain throttle for health_model/failure_model.

This fixes two related problems that existed before:

1. **Shared global singleton across all instances.** `health_model` and
   `failure_model` were created once as module-level singletons and reused
   for every instance. Training on instance B's data overwrote the
   in-memory model (and the on-disk .pkl file) that instance A had just
   been trained with, so predictions could silently use the wrong
   instance's model if requests interleaved.

2. **Retraining on every single GET request.** Every dashboard refresh
   re-fit a RandomForest on all historical rows for that instance, which
   gets slower as the metrics_snapshots table grows.

This registry keeps one model instance per (model_type, db instance id),
each with its own on-disk path, and only retrains a given instance's model
after TRAIN_INTERVAL_SECONDS has elapsed (or if it has never been trained
in this process yet).
"""
import time
from typing import Dict, Tuple, Type

TRAIN_INTERVAL_SECONDS = 5 * 60  # retrain at most once every 5 minutes

_model_registry: Dict[Tuple[str, int], object] = {}
_last_trained: Dict[Tuple[str, int], float] = {}


def get_or_create_model(model_cls: Type, model_name: str, instance_id: int):
    """Return the cached model instance for this (model_type, instance),
    creating a fresh one (with its own model_dir) on first use."""
    key = (model_name, instance_id)
    model = _model_registry.get(key)
    if model is None:
        model = model_cls(model_dir=f"ml_data/models/{model_name}/instance_{instance_id}")
        _model_registry[key] = model
    return model


def train_if_stale(model, model_name: str, instance_id: int, *train_args, **train_kwargs) -> None:
    """Train `model` on `*train_args`/`**train_kwargs` only if it's due for
    a retrain (never trained yet in this process, or the throttle window
    elapsed). Extra args/kwargs are forwarded as-is to `model.train(...)`,
    so this works for models whose train() needs more than just historical
    snapshots (e.g. health_model/failure_model also need real Alert
    history to build non-circular labels)."""
    key = (model_name, instance_id)
    last = _last_trained.get(key)
    is_stale = last is None or (time.time() - last) >= TRAIN_INTERVAL_SECONDS

    if getattr(model, "model", None) is None or is_stale:
        model.train(*train_args, **train_kwargs)
        _last_trained[key] = time.time()
