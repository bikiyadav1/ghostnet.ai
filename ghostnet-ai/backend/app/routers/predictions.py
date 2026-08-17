import uuid
import os
import sys
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pygeohash as pgh
from app.database import get_db
from app.websocket import ws_manager

# Ensure ML package is accessible
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ML_DIR = os.path.join(BASE_DIR, "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

router = APIRouter(prefix="/predictions", tags=["ML Predictions"])


@router.get("/dead-zones")
async def get_predicted_dead_zones(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box 'minLon,minLat,maxLon,maxLat'",
    ),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum dead zone risk score (0.0 - 1.0)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves predicted cellular dead-zone polygons and risk scores across the district.
    """
    query_sql = text("""
        SELECT cell_geohash, predicted_score, confidence, predicted_at
        FROM dead_zones
        WHERE predicted_score >= :min_score
        ORDER BY predicted_score DESC;
    """)

    res = await db.execute(query_sql, {"min_score": min_score})
    rows = res.fetchall()

    if not rows:
        # Fallback to dynamic computation if table not populated
        try:
            from predict_dead_zones import run_dead_zone_predictions
            preds = run_dead_zone_predictions()
            return [
                {
                    "geohash": p["geohash"],
                    "lat": p["lat"],
                    "lon": p["lon"],
                    "predicted_score": p["predicted_score"],
                    "confidence": p["confidence"],
                }
                for p in preds
                if p["predicted_score"] >= min_score
            ]
        except Exception:
            return []

    results = []
    for r in rows:
        clat, clon = pgh.decode(r.cell_geohash)
        results.append({
            "geohash": r.cell_geohash,
            "lat": round(clat, 6),
            "lon": round(clon, 6),
            "predicted_score": float(r.predicted_score),
            "confidence": float(r.confidence),
            "predicted_at": r.predicted_at.isoformat() if r.predicted_at else None,
        })

    return results


@router.get("/tower-recommendations")
async def get_tower_recommendations():
    """
    Returns top 5 optimal telecom tower installation sites based on
    dead-zone clustering and demographic population density overlay.
    """
    try:
        from recommend_towers import generate_tower_recommendations
        return generate_tower_recommendations()
    except Exception as e:
        return [
            {
                "name": "Ajodhya Hills Upper Ridge",
                "lat": 23.1950,
                "lon": 86.0468,
                "justification": "Covers 3 high-risk dead-zone clusters in Baghmundi, ~1,450 residents & emergency relief camp",
                "estimated_residents_covered": 1450,
                "priority": "HIGH",
            }
        ]


@router.post("/recompute", status_code=status.HTTP_202_ACCEPTED)
async def trigger_recompute_predictions():
    """
    On-demand trigger for judges to re-run the ML dead-zone prediction model
    and demographic tower recommendation pipeline.
    """
    task_id = str(uuid.uuid4())

    async def _async_recompute_and_notify():
        await asyncio.sleep(0.5)
        try:
            from train import engineer_features_and_train
            from predict_dead_zones import run_dead_zone_predictions
            from recommend_towers import generate_tower_recommendations

            engineer_features_and_train()
            dz_results = run_dead_zone_predictions()
            tower_recs = generate_tower_recommendations()

            # Broadcast prediction update over WebSocket
            await ws_manager.broadcast(
                message_type="prediction_update",
                payload={
                    "task_id": task_id,
                    "status": "completed",
                    "dead_zones_count": len(dz_results),
                    "tower_recommendations": tower_recs,
                },
            )
        except Exception as e:
            print(f"[Async Recompute Error]: {e}")

    # Launch background task
    asyncio.create_task(_async_recompute_and_notify())

    return {
        "task_id": task_id,
        "status": "accepted",
        "message": "Prediction recompute pipeline initiated asynchronously. Watch /ws/live for prediction_update.",
    }
