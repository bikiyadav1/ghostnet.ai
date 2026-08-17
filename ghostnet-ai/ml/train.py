import os
import sys
import math
import joblib
import numpy as np
import pandas as pd
import pygeohash as pgh
from datetime import datetime, timezone
import psycopg2

try:
    from xgboost import XGBRegressor
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor as XGBRegressor

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_deadzone_model.joblib")
os.makedirs(MODEL_DIR, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ghostnet:ghostnet_secure_pass@localhost:5432/ghostnet_db",
)
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def haversine_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def compute_idw_fallback(target_lat, target_lon, dense_cells_df, power=2.0):
    """
    Inverse Distance Weighting (IDW) interpolation for cold-start sparse cells (<20 samples).
    Interpolates expected signal using weighted inverse distance from surrounding known cells.
    """
    if dense_cells_df.empty:
        return -95.0  # Default moderate-weak signal baseline

    distances = []
    values = []
    for _, row in dense_cells_df.iterrows():
        d = haversine_distance_km(target_lat, target_lon, row["lat"], row["lon"])
        d = max(0.1, d)  # Prevent division by zero
        distances.append(d)
        values.append(row["avg_signal"])

    weights = [1.0 / (d ** power) for d in distances]
    total_weight = sum(weights)
    if total_weight == 0:
        return -95.0

    weighted_signal = sum(w * v for w, v in zip(weights, values)) / total_weight
    return round(weighted_signal, 2)


def fetch_training_data_from_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Query readings with coordinates and distance to nearest tower
        query = """
            SELECT 
                r.id,
                ST_Y(r.location::geometry) AS lat,
                ST_X(r.location::geometry) AS lon,
                r.signal_dbm,
                r.network_type,
                r.recorded_at,
                COALESCE(
                    (
                        SELECT MIN(ST_Distance(r.location, t.location) / 1000.0)
                        FROM towers t
                    ),
                    15.0
                ) AS dist_to_tower_km
            FROM signal_readings r;
        """
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            print("[ML Train] No rows in DB. Generating synthetic baseline for training.")
            return generate_synthetic_training_data()

        df = pd.DataFrame(
            rows,
            columns=[
                "id",
                "lat",
                "lon",
                "signal_dbm",
                "network_type",
                "recorded_at",
                "dist_to_tower_km",
            ],
        )
        return df
    except Exception as e:
        print(f"[ML Train] Could not connect to DB ({e}). Using synthetic Purulia dataset.")
        return generate_synthetic_training_data()


def generate_synthetic_training_data():
    """Generates synthetic Purulia dataset for training when standalone or in container tests."""
    np.random.seed(42)
    n_samples = 300
    
    lats = np.random.uniform(22.9, 23.6, n_samples)
    lons = np.random.uniform(85.9, 86.8, n_samples)
    
    # Distance to town centers / towers
    town_centers = [(23.3322, 86.3652), (23.3644, 85.9682), (23.0965, 86.2228), (23.5417, 86.6719)]
    dist_to_tower_km = []
    signals = []

    for lat, lon in zip(lats, lons):
        min_d = min(haversine_distance_km(lat, lon, tlat, tlon) for tlat, tlon in town_centers)
        dist_to_tower_km.append(min_d)
        
        # Path loss model approximation: -55 dBm at 1km, attenuating with distance & terrain noise
        base_signal = -55.0 - (28.0 * np.log10(max(1.0, min_d * 2.0)))
        # Ajodhya hills dead zone penalty
        if 23.12 <= lat <= 23.26 and 85.98 <= lon <= 86.15:
            base_signal -= 25.0
        # Bandwan forest penalty
        if 22.80 <= lat <= 22.95 and 86.40 <= lon <= 86.60:
            base_signal -= 30.0

        signal = int(np.clip(base_signal + np.random.normal(0, 6), -135, -50))
        signals.append(signal)

    df = pd.DataFrame({
        "lat": lats,
        "lon": lons,
        "signal_dbm": signals,
        "dist_to_tower_km": dist_to_tower_km,
        "recorded_at": [datetime.now(timezone.utc) for _ in range(n_samples)],
    })
    return df


def engineer_features_and_train():
    print("═══════════════════════════════════════════════════════════════════")
    print("      GHOSTNET AI — DEAD-ZONE PREDICTION MODEL TRAINING            ")
    print("═══════════════════════════════════════════════════════════════════")

    df = fetch_training_data_from_db()
    print(f"Loaded {len(df)} signal readings for feature engineering.")

    # Geohash cell clustering (precision 6: ~1.2km x 0.6km)
    df["geohash"] = df.apply(lambda r: pgh.encode(r["lat"], r["lon"], precision=6), axis=1)
    df["hour"] = pd.to_datetime(df["recorded_at"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["recorded_at"]).dt.dayofweek

    # Calculate cell sample counts and historical averages
    cell_stats = (
        df.groupby("geohash")
        .agg(
            sample_count=("signal_dbm", "count"),
            avg_signal=("signal_dbm", "mean"),
            cell_lat=("lat", "mean"),
            cell_lon=("lon", "mean"),
        )
        .reset_index()
    )

    # Identify dense vs sparse cells (Threshold N=20 per SIH 2026 spec)
    dense_cells = cell_stats[cell_stats["sample_count"] >= 20].rename(
        columns={"cell_lat": "lat", "cell_lon": "lon"}
    )
    sparse_cells = cell_stats[cell_stats["sample_count"] < 20]

    print(f"Dense Cells (>=20 readings): {len(dense_cells)}")
    print(f"Sparse Cells (<20 readings, using IDW Cold-Start): {len(sparse_cells)}")

    # Apply IDW Cold-Start for sparse cells
    idw_interpolations = {}
    for _, sc in sparse_cells.iterrows():
        idw_val = compute_idw_fallback(sc["cell_lat"], sc["cell_lon"], dense_cells)
        idw_interpolations[sc["geohash"]] = idw_val

    print(f"Computed IDW fallback interpolations for {len(idw_interpolations)} sparse cells.")

    # Engineer Target: Dead Zone Risk Score (0.0 = Strong, 1.0 = Total Dead Zone)
    # Mapping: -60 dBm -> 0.0, -110 dBm -> 0.70, -130 dBm -> 1.0
    def signal_to_deadzone_score(dbm):
        if dbm >= -70:
            return 0.05
        if dbm <= -125:
            return 1.0
        # Linear normalized scale between -70 dBm and -125 dBm
        return round(float(np.clip((-dbm - 70.0) / 55.0, 0.0, 1.0)), 4)

    df["dead_zone_score"] = df["signal_dbm"].apply(signal_to_deadzone_score)

    # Feature Matrix
    X = pd.DataFrame({
        "lat": df["lat"],
        "lon": df["lon"],
        "dist_to_tower_km": df["dist_to_tower_km"],
        "hour": df["hour"],
        "day_of_week": df["day_of_week"],
    })
    y = df["dead_zone_score"]

    print("Training XGBoost Regressor for signal attenuation & dead-zone scoring...")
    model = XGBRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        random_state=42,
    )
    model.fit(X, y)

    # Save model artifact
    joblib.dump(
        {
            "model": model,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "dense_cells": dense_cells.to_dict(orient="records"),
            "idw_interpolations": idw_interpolations,
        },
        MODEL_PATH,
    )

    print(f"Model successfully trained and saved to: {MODEL_PATH}")
    print("═══════════════════════════════════════════════════════════════════")
    return model


if __name__ == "__main__":
    engineer_features_and_train()
