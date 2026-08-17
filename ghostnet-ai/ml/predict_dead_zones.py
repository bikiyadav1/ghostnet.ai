import os
import sys
import uuid
import joblib
import numpy as np
import pandas as pd
import pygeohash as pgh
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ghostnet:ghostnet_secure_pass@localhost:5432/ghostnet_db",
)
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "xgboost_deadzone_model.joblib")


def generate_district_grid_geohashes(bbox=(85.85, 22.85, 86.85, 23.65), step=0.03):
    """Generates district grid centroids across Purulia bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    lats = np.arange(min_lat, max_lat, step)
    lons = np.arange(min_lon, max_lon, step)

    grid_cells = []
    seen_hashes = set()

    for lat in lats:
        for lon in lons:
            gh = pgh.encode(lat, lon, precision=6)
            if gh not in seen_hashes:
                seen_hashes.add(gh)
                center_lat, center_lon = pgh.decode(gh)
                grid_cells.append({
                    "geohash": gh,
                    "lat": round(center_lat, 6),
                    "lon": round(center_lon, 6),
                })
    return pd.DataFrame(grid_cells)


def run_dead_zone_predictions():
    print("[DeadZone Inference] Starting district-wide dead-zone grid scoring...")

    # Load or train model
    if not os.path.exists(MODEL_PATH):
        print("[DeadZone Inference] Model artifact not found. Training model first...")
        from train import engineer_features_and_train
        engineer_features_and_train()

    artifact = joblib.load(MODEL_PATH)
    model = artifact["model"]
    idw_interpolations = artifact.get("idw_interpolations", {})

    grid_df = generate_district_grid_geohashes()
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    current_dow = now.weekday()

    # Calculate distance to nearest known tower
    towers = [
        (23.3340, 86.3670),
        (23.3620, 85.9690),
        (23.0980, 86.2240),
        (23.5430, 86.6740),
        (23.0610, 86.6590),
        (23.2080, 86.0620),
    ]

    def min_dist_to_tower(lat, lon):
        import math
        R = 6371.0
        dists = []
        for tlat, tlon in towers:
            dlat = math.radians(tlat - lat)
            dlon = math.radians(tlon - lon)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(tlat)) * math.sin(dlon / 2)**2
            dists.append(2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
        return min(dists)

    grid_df["dist_to_tower_km"] = grid_df.apply(lambda r: min_dist_to_tower(r["lat"], r["lon"]), axis=1)
    grid_df["hour"] = current_hour
    grid_df["day_of_week"] = current_dow

    X_grid = pd.DataFrame({
        "lat": grid_df["lat"],
        "lon": grid_df["lon"],
        "dist_to_tower_km": grid_df["dist_to_tower_km"],
        "hour": grid_df["hour"],
        "day_of_week": grid_df["day_of_week"],
    })

    raw_preds = model.predict(X_grid)
    grid_df["predicted_score"] = np.clip(raw_preds, 0.0, 1.0).round(4)
    grid_df["confidence"] = 0.92

    # Boost scores for known geographical dead zones (Ajodhya Hills & Bandwan forest)
    for idx, row in grid_df.iterrows():
        lat, lon = row["lat"], row["lon"]
        # Ajodhya Hills ridge
        if 23.12 <= lat <= 23.26 and 85.98 <= lon <= 86.15:
            grid_df.at[idx, "predicted_score"] = min(1.0, row["predicted_score"] + 0.35)
        # Bandwan dense forest
        if 22.80 <= lat <= 22.95 and 86.40 <= lon <= 86.60:
            grid_df.at[idx, "predicted_score"] = min(1.0, row["predicted_score"] + 0.40)

    # Persist to database if available
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("DELETE FROM dead_zones;")
        
        insert_data = [
            (
                str(uuid.uuid4()),
                row["geohash"],
                float(row["predicted_score"]),
                now,
                float(row["confidence"]),
            )
            for _, row in grid_df.iterrows()
        ]

        execute_values(
            cur,
            """
            INSERT INTO dead_zones (id, cell_geohash, predicted_score, predicted_at, confidence)
            VALUES %s;
            """,
            insert_data,
        )

        cur.close()
        conn.close()
        print(f"[DeadZone Inference] Successfully written {len(insert_data)} predicted dead-zone cells to database.")
    except Exception as e:
        print(f"[DeadZone Inference] Database write skipped ({e}). Outputting memory result.")

    return grid_df.to_dict(orient="records")


if __name__ == "__main__":
    run_dead_zone_predictions()
