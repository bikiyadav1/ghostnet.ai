import logging
import asyncio
import os
import sys
from datetime import datetime, timezone
from app.celery_app import celery_app

logger = logging.getLogger("ghostnet_tasks")

# Add /ml and /seed to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ML_DIR = os.path.join(BASE_DIR, "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)


@celery_app.task(name="recompute_predictions_task")
def recompute_predictions_task():
    """
    Asynchronous Celery task for running the ML dead-zone prediction pipeline
    and generating optimal telecom tower recommendations.
    """
    logger.info("[Celery Task] Starting ML dead-zone and tower recommendation pipeline...")
    start_time = datetime.now(timezone.utc)

    try:
        # Import ML modules dynamically
        from train import engineer_features_and_train
        from predict_dead_zones import run_dead_zone_predictions
        from recommend_towers import generate_tower_recommendations

        # 1. Train / Update Model
        engineer_features_and_train()

        # 2. Score District Grid
        dead_zones = run_dead_zone_predictions()

        # 3. Generate Candidate Towers
        tower_recs = generate_tower_recommendations()

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"[Celery Task] Completed in {duration:.2f}s. Scored {len(dead_zones)} cells, recommended {len(tower_recs)} towers.")

        return {
            "status": "success",
            "duration_seconds": round(duration, 2),
            "dead_zones_count": len(dead_zones),
            "recommended_towers": tower_recs,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[Celery Task] Prediction pipeline error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
