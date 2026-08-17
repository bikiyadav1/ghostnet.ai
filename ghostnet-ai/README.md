# GhostNet AI — SIH 2026

**Autonomous Offline-First Emergency Mesh & AI Connectivity Intelligence Platform**

Built for rural disaster scenarios with intermittent or zero cellular connectivity. Delivers real-time signal telemetry maps, AI-driven dead-zone predictions, tower placement recommendations, offline-first emergency SOS auto-sync, and simulated/BLE peer-to-peer mesh relay.

---

## 1. Quickstart (Under 10 Minutes)

### Step 1: Clone and Configure
```bash
git clone https://github.com/ghostnet-ai/ghostnet-ai.git
cd ghostnet-ai
cp .env.example .env
```

### Step 2: Start All Services via Docker
```bash
docker-compose up --build -d
```

All 6 core services will start with automated health checks:
1. **`postgres`** (`:5432`): PostGIS spatial database for high-performance GIST-indexed spatial queries.
2. **`redis`** (`:6379`): In-memory broker & result backend for asynchronous ML workers.
3. **`backend`** (`:8000`): FastAPI async backend serving `/api/v1/*` and `/ws/live` WebSockets.
4. **`celery-worker`**: Distributed worker running ML dead-zone predictions & tower clustering.
5. **`celery-beat`**: Periodic task scheduler for background district inference.
6. **`dashboard`** (`:5173`): React + Vite + TailwindCSS admin dashboard with live Leaflet heatmap & responder feed.

### Step 3: Seed Realistic District Telemetry
```bash
docker-compose exec backend python /seed/seed.py
```
*Populates ~220 realistic cellular readings, emergency help points (hospitals, police, shelters), and cell towers across the demo district (**Purulia, West Bengal**).*

### Step 4: Open Admin Dashboard
Open your browser and navigate to:
👉 **`http://localhost:5173`**

---

## 2. Running Mobile App (`/mobile`)

### Android Emulator Setup (Recommended for Demo)
1. Open an Android emulator in Android Studio or VS Code.
2. The app automatically connects to the backend at `http://10.0.2.2:8000/api/v1`.
3. Run:
```bash
cd mobile
flutter pub get
flutter run
```

### Physical Android Phone Setup (Same Wi-Fi Network)
1. Find your laptop's local IP address (`ipconfig` or `ifconfig`, e.g., `192.168.1.45`).
2. Update `ApiClient.baseUrl` in `mobile/lib/src/core/network/api_client.dart` to `http://<YOUR_LOCAL_IP>:8000/api/v1`.
3. Run:
```bash
flutter run -d <device-id>
```

---

## 3. Core API Endpoints (`/api/v1`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/readings` | Ingests batch of signal telemetry; broadcasts over `/ws/live` |
| `GET` | `/coverage?bbox=...` | Retrieves raw signal readings within bounding box |
| `GET` | `/coverage/heatmap?bbox=...` | Retrieves Geohash-aggregated signal strength grid (<300ms) |
| `GET` | `/help-points?lat=&lon=` | Finds nearest hospitals, police stations, shelters using PostGIS `ST_DWithin` |
| `WS` | `/ws/live` | Real-time WebSocket connection for live telemetry & alerts |

---

## 4. Architectural Highlights
- **Anonymous Device Privacy**: Devices use locally generated UUIDs; zero PII collected.
- **Offline First Resilience**: Telemetry & SOS alerts persist to Drift SQLite immediately and auto-sync on network reconnect without manual retry.
- **Spatial Indexing**: All geospatial queries leverage PostGIS `GIST` indexes on `geography(Point, 4326)` for sub-second responsiveness.
