import math
from typing import Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
except ImportError:
    AsyncSession = None
    text = None

try:
    import pygeohash as pgh
except ImportError:
    pgh = None

try:
    from app.models import SosCategoryEnum
except ImportError:
    SosCategoryEnum = None

# Category weight mapping per SIH 2026 specification
CATEGORY_WEIGHTS = {
    "medical": 1.0,
    "disaster": 0.9,
    "security": 0.8,
    "general": 0.5,
    getattr(SosCategoryEnum, 'MEDICAL', 'medical'): 1.0,
    getattr(SosCategoryEnum, 'DISASTER', 'disaster'): 0.9,
    getattr(SosCategoryEnum, 'SECURITY', 'security'): 0.8,
    getattr(SosCategoryEnum, 'GENERAL', 'general'): 0.5,
}

# Exponential decay lambda chosen so recency score halves every 30 minutes
# λ = ln(2) / 30 ≈ 0.0231049
LAMBDA_DECAY = math.log(2) / 30.0


def calculate_priority_score_pure(
    category: Any,
    created_at: datetime,
    corroboration_count: int,
    location_risk: float = 0.0,
    now: Optional[datetime] = None,
) -> Tuple[float, dict]:
    """
    Computes transparent multi-factor priority score:
      score = 0.40 * category_weight
            + 0.25 * recency_decay
            + 0.20 * corroboration_norm
            + 0.15 * location_risk
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Category Weight (0.40)
    cat_key = category.value if hasattr(category, 'value') else str(category).lower()
    cat_weight = CATEGORY_WEIGHTS.get(cat_key, CATEGORY_WEIGHTS.get(category, 0.5))


    # 2. Recency Decay (0.25)
    # Convert timezone if needed
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    minutes_elapsed = max(0.0, (now - created_at).total_seconds() / 60.0)
    recency_decay = math.exp(-LAMBDA_DECAY * minutes_elapsed)

    # 3. Proximity Corroboration Normalization (0.20)
    # Capped at 5 nearby reports in last 1h, normalized 0.0 - 1.0
    corroboration_norm = min(corroboration_count, 5) / 5.0

    # 4. Location Risk (0.15)
    loc_risk = max(0.0, min(1.0, location_risk))

    # Total Score
    total_score = (
        0.40 * cat_weight
        + 0.25 * recency_decay
        + 0.20 * corroboration_norm
        + 0.15 * loc_risk
    )

    breakdown = {
        "category_term": round(0.40 * cat_weight, 4),
        "recency_term": round(0.25 * recency_decay, 4),
        "corroboration_term": round(0.20 * corroboration_norm, 4),
        "location_risk_term": round(0.15 * loc_risk, 4),
        "raw_score": round(total_score, 4),
        "minutes_elapsed": round(minutes_elapsed, 1),
    }

    return round(total_score, 4), breakdown


async def compute_db_priority_score(
    db: AsyncSession,
    lat: float,
    lon: float,
    category: SosCategoryEnum,
    created_at: datetime,
    exclude_alert_id: Optional[str] = None,
) -> Tuple[float, int, float, dict]:
    """
    Queries PostGIS to count active alerts within 500m in the last 1 hour
    and checks if the point falls inside a predicted dead-zone cell.
    """
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    exclude_clause = ""
    params = {
        "lat": lat,
        "lon": lon,
        "one_hour_ago": one_hour_ago,
    }

    if exclude_alert_id:
        exclude_clause = "AND id != :exclude_alert_id"
        params["exclude_alert_id"] = exclude_alert_id

    # 1. Count nearby corroborating alerts within 500m in last 1 hour using ST_DWithin
    corrob_sql = text(f"""
        SELECT COUNT(*) 
        FROM sos_alerts
        WHERE ST_DWithin(
            location, 
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 
            500.0
        )
        AND created_at >= :one_hour_ago
        AND status != 'resolved'
        {exclude_clause};
    """)
    result = await db.execute(corrob_sql, params)
    corroboration_count = result.scalar() or 0

    # 2. Check location risk from dead_zones table using geohash
    geohash_str = pgh.encode(lat, lon, precision=6)
    dz_sql = text("""
        SELECT predicted_score 
        FROM dead_zones 
        WHERE cell_geohash = :geohash 
        LIMIT 1;
    """)
    dz_res = await db.execute(dz_sql, {"geohash": geohash_str})
    dz_row = dz_res.fetchone()
    location_risk = float(dz_row[0]) if dz_row else 0.0

    score, breakdown = calculate_priority_score_pure(
        category=category,
        created_at=created_at,
        corroboration_count=corroboration_count,
        location_risk=location_risk,
    )

    return score, corroboration_count, location_risk, breakdown
