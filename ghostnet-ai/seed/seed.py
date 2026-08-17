import os
import sys
import uuid
import random
import math
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ghostnet:ghostnet_secure_pass@localhost:5432/ghostnet_db",
)
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def connect_db():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def seed_database():
    conn = connect_db()
    cur = conn.cursor()

    print("Ensuring PostGIS extension and database tables exist...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    
    # Create enum types if not exist
    cur.execute("""
    DO $$ BEGIN
        CREATE TYPE network_type_enum AS ENUM ('2G', '3G', '4G', '5G', 'none');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    DO $$ BEGIN
        CREATE TYPE tower_source_enum AS ENUM ('official', 'inferred');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    DO $$ BEGIN
        CREATE TYPE help_point_type_enum AS ENUM ('hospital', 'police', 'shelter', 'safe_zone');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    DO $$ BEGIN
        CREATE TYPE sos_category_enum AS ENUM ('medical', 'disaster', 'security', 'general');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    DO $$ BEGIN
        CREATE TYPE sos_status_enum AS ENUM ('queued', 'sent', 'acknowledged', 'resolved');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    DO $$ BEGIN
        CREATE TYPE checkin_status_enum AS ENUM ('safe', 'needs_help');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    # Create tables if not exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        app_version VARCHAR(50) DEFAULT '2.0.0'
    );

    CREATE TABLE IF NOT EXISTS signal_readings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES devices(id),
        location GEOGRAPHY(Point, 4326) NOT NULL,
        network_type network_type_enum NOT NULL,
        signal_dbm INT NOT NULL,
        download_mbps FLOAT DEFAULT 0.0,
        upload_mbps FLOAT DEFAULT 0.0,
        latency_ms INT DEFAULT 0,
        recorded_at TIMESTAMPTZ NOT NULL,
        is_verified BOOL DEFAULT false
    );

    CREATE TABLE IF NOT EXISTS towers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        location GEOGRAPHY(Point, 4326) NOT NULL,
        operator VARCHAR(100) NOT NULL,
        source tower_source_enum NOT NULL DEFAULT 'official'
    );

    CREATE TABLE IF NOT EXISTS dead_zones (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        cell_geohash VARCHAR(12) NOT NULL,
        predicted_score FLOAT NOT NULL,
        predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        confidence FLOAT NOT NULL DEFAULT 1.0
    );

    CREATE TABLE IF NOT EXISTS help_points (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        type help_point_type_enum NOT NULL,
        location GEOGRAPHY(Point, 4326) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sos_alerts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES devices(id),
        location GEOGRAPHY(Point, 4326) NOT NULL,
        message TEXT,
        category sos_category_enum NOT NULL DEFAULT 'general',
        priority_score FLOAT NOT NULL DEFAULT 0.5,
        status sos_status_enum NOT NULL DEFAULT 'sent',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        corroboration_count INT NOT NULL DEFAULT 0,
        is_relayed BOOL NOT NULL DEFAULT false
    );

    CREATE TABLE IF NOT EXISTS check_ins (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        device_id UUID NOT NULL REFERENCES devices(id),
        location GEOGRAPHY(Point, 4326) NOT NULL,
        status checkin_status_enum NOT NULL DEFAULT 'safe',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_signal_readings_location_gist ON signal_readings USING GIST (location);
    CREATE INDEX IF NOT EXISTS idx_towers_location_gist ON towers USING GIST (location);
    CREATE INDEX IF NOT EXISTS idx_help_points_location_gist ON help_points USING GIST (location);
    CREATE INDEX IF NOT EXISTS idx_sos_alerts_location_gist ON sos_alerts USING GIST (location);
    CREATE INDEX IF NOT EXISTS idx_sos_alerts_priority ON sos_alerts (priority_score);
    CREATE INDEX IF NOT EXISTS idx_check_ins_location_gist ON check_ins USING GIST (location);
    """)

    print("Seeding demo devices...")
    device_ids = [str(uuid.uuid4()) for _ in range(8)]
    cur.execute("DELETE FROM sos_alerts;")
    cur.execute("DELETE FROM check_ins;")
    cur.execute("DELETE FROM signal_readings;")
    cur.execute("DELETE FROM devices;")
    for d_id in device_ids:
        cur.execute(
            "INSERT INTO devices (id, created_at, app_version) VALUES (%s, %s, %s);",
            (d_id, datetime.now(timezone.utc), "2.0.0"),
        )

    print("Seeding emergency help points across Purulia district...")
    cur.execute("DELETE FROM help_points;")
    help_points_data = [
        ("Purulia Sadar District Hospital", "hospital", 23.3350, 86.3680),
        ("Jhalda Rural Hospital", "hospital", 23.3610, 85.9720),
        ("Balarampur Block Primary Health Centre", "hospital", 23.1020, 86.2200),
        ("Baghmundi Community Health Centre", "hospital", 23.1980, 86.0490),
        ("Manbazar Rural Hospital", "hospital", 23.0640, 86.6620),
        ("Raghunathpur Super Speciality Hospital", "hospital", 23.5450, 86.6780),
        ("Purulia Town Police Station", "police", 23.3310, 86.3620),
        ("Baghmundi Police Station", "police", 23.1920, 86.0440),
        ("Bandwan Police Station", "police", 22.8750, 86.5020),
        ("Jhalda Police Station", "police", 23.3660, 85.9660),
        ("Ajodhya Hills Disaster Relief & Shelter", "shelter", 23.1870, 86.0720),
        ("Sirkabad Cyclone & Flood Relief Centre", "shelter", 23.2850, 86.1520),
        ("Kangsabati Dam Emergency Safe Zone", "safe_zone", 23.0420, 86.6910),
        ("Joychandi Hill Safe Assembly Ground", "safe_zone", 23.5120, 86.6850),
    ]

    for name, hp_type, lat, lon in help_points_data:
        cur.execute(
            """
            INSERT INTO help_points (id, name, type, location)
            VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography);
            """,
            (str(uuid.uuid4()), name, hp_type, lon, lat),
        )

    print("Seeding cellular telecom towers in Purulia...")
    cur.execute("DELETE FROM towers;")
    towers_data = [
        ("Purulia Sadar Master BSNL Tower", 23.3340, 86.3670, "BSNL", "official"),
        ("Jhalda Town Airtel Cell Tower", 23.3620, 85.9690, "Airtel", "official"),
        ("Balarampur Main Jio Tower", 23.0980, 86.2240, "Jio", "official"),
        ("Raghunathpur Central Vi Tower", 23.5430, 86.6740, "Vi", "official"),
        ("Manbazar BSNL Telehub", 23.0610, 86.6590, "BSNL", "official"),
        ("Baghmundi Foothills Inferred Tower", 23.2080, 86.0620, "Jio", "inferred"),
    ]

    for name, lat, lon, operator, source in towers_data:
        cur.execute(
            """
            INSERT INTO towers (id, name, location, operator, source)
            VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s);
            """,
            (str(uuid.uuid4()), name, lon, lat, operator, source),
        )

    print("Generating ~220 realistic signal telemetry readings across Purulia district...")
    now = datetime.now(timezone.utc)
    readings = []

    towns = [
        ("Purulia Sadar", 23.3322, 86.3652, -68, "5G", 45.0, 15.0, 24),
        ("Jhalda", 23.3644, 85.9682, -74, "4G", 28.0, 8.5, 32),
        ("Balarampur", 23.0965, 86.2228, -78, "4G", 20.0, 6.0, 40),
        ("Raghunathpur", 23.5417, 86.6719, -70, "5G", 40.0, 12.0, 26),
        ("Manbazar", 23.0601, 86.6578, -82, "4G", 14.0, 4.2, 48),
    ]

    for name, c_lat, c_lon, base_dbm, net, dl, ul, lat_ms in towns:
        for _ in range(25):
            lat = c_lat + random.uniform(-0.03, 0.03)
            lon = c_lon + random.uniform(-0.03, 0.03)
            dbm = int(base_dbm + random.uniform(-8, 8))
            rec_at = now - timedelta(minutes=random.randint(1, 180))
            dev_id = random.choice(device_ids)
            readings.append((
                str(uuid.uuid4()), dev_id, lon, lat, net, dbm,
                max(0.1, dl + random.uniform(-5, 5)),
                max(0.1, ul + random.uniform(-2, 2)),
                max(15, int(lat_ms + random.uniform(-10, 15))),
                rec_at, True
            ))

    for _ in range(45):
        t = random.random()
        lat = 23.3322 * (1 - t) + 23.0965 * t + random.uniform(-0.015, 0.015)
        lon = 86.3652 * (1 - t) + 86.2228 * t + random.uniform(-0.015, 0.015)
        dbm = int(-88 + random.uniform(-10, 6))
        net = random.choice(["4G", "3G"])
        rec_at = now - timedelta(minutes=random.randint(5, 240))
        readings.append((
            str(uuid.uuid4()), random.choice(device_ids), lon, lat, net, dbm,
            random.uniform(2.0, 12.0), random.uniform(0.5, 3.0),
            random.randint(50, 120), rec_at, True
        ))

    dead_clusters = [
        ("Ajodhya Hills Ridge", 23.1950, 86.0468, -118),
        ("Bandwan Forest Belt", 22.8732, 86.5050, -124),
        ("Kashipur Remote Hills", 23.4150, 86.5820, -112),
    ]

    for name, c_lat, c_lon, base_dbm in dead_clusters:
        for _ in range(18):
            lat = c_lat + random.uniform(-0.04, 0.04)
            lon = c_lon + random.uniform(-0.04, 0.04)
            dbm = int(base_dbm + random.uniform(-10, 6))
            net = "none" if dbm < -120 else "2G"
            rec_at = now - timedelta(minutes=random.randint(10, 300))
            readings.append((
                str(uuid.uuid4()), random.choice(device_ids), lon, lat, net, dbm,
                0.0 if net == "none" else random.uniform(0.01, 0.15),
                0.0 if net == "none" else random.uniform(0.01, 0.08),
                999 if net == "none" else random.randint(300, 850),
                rec_at, True
            ))

    readings.append((
        str(uuid.uuid4()), random.choice(device_ids), 86.8200, 23.6100, "2G", -106,
        0.05, 0.02, 450, now - timedelta(minutes=45), True
    ))

    execute_values(
        cur,
        """
        INSERT INTO signal_readings (
            id, device_id, location, network_type, signal_dbm, download_mbps, upload_mbps, latency_ms, recorded_at, is_verified
        ) VALUES %s;
        """,
        [
            (r[0], r[1], f"SRID=4326;POINT({r[2]} {r[3]})", r[4], r[5], r[6], r[7], r[8], r[9], r[10])
            for r in readings
        ],
        template="(%s, %s, ST_GeogFromText(%s), %s, %s, %s, %s, %s, %s, %s)",
    )

    # Seed Initial SOS Alerts with priority scoring
    print("Seeding initial emergency SOS alerts in Purulia...")
    sos_seeds = [
        (
            device_ids[0], 23.1960, 86.0480,
            "Flash flood water rising rapidly near Ajodhya Lower Dam. Family stranded.",
            "disaster", 0.88, "sent", now - timedelta(minutes=6), 2, True
        ),
        (
            device_ids[1], 23.1970, 86.0510,
            "Severe medical emergency: cardiac patient requiring oxygen cylinder.",
            "medical", 0.94, "sent", now - timedelta(minutes=4), 2, False
        ),
        (
            device_ids[2], 22.8740, 86.5040,
            "Fallen tree blocking single evacuation road in Bandwan forest zone.",
            "security", 0.76, "acknowledged", now - timedelta(minutes=25), 1, False
        ),
        (
            device_ids[3], 23.4160, 86.5830,
            "Transformer explosion and localized fire near Kashipur block.",
            "disaster", 0.72, "sent", now - timedelta(minutes=42), 0, False
        ),
    ]

    for dev_id, lat, lon, msg, cat, p_score, st, c_at, corrob, relayed in sos_seeds:
        cur.execute(
            """
            INSERT INTO sos_alerts (
                id, device_id, location, message, category, priority_score, status, created_at, sent_at, corroboration_count, is_relayed
            ) VALUES (
                %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s, %s, %s, %s, %s, %s, %s
            );
            """,
            (str(uuid.uuid4()), dev_id, lon, lat, msg, cat, p_score, st, c_at, c_at, corrob, relayed),
        )

    # Seed check-in
    cur.execute(
        """
        INSERT INTO check_ins (id, device_id, location, status, created_at)
        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(86.3652, 23.3322), 4326)::geography, 'safe', NOW());
        """,
        (str(uuid.uuid4()), device_ids[4]),
    )

    cur.execute("SELECT COUNT(*) FROM signal_readings;")
    count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sos_alerts;")
    sos_count = cur.fetchone()[0]
    print(f"Successfully seeded {count} signal readings and {sos_count} emergency SOS alerts!")

    cur.close()
    conn.close()


if __name__ == "__main__":
    try:
        seed_database()
    except Exception as e:
        print(f"Error seeding database: {e}")
        sys.exit(1)
