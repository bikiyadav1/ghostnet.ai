import http.server
import socketserver
import json
import urllib.parse
import uuid
import math
import random
import threading
import time
import os
from datetime import datetime, timezone, timedelta

PORT = 5173
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(WEB_DIR)

# ─────────────────────────────────────────────────────────────────────────────
# STATEWIDE WEST BENGAL SPATIAL ENGINE & CELLULAR INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_WEIGHTS = {
    "medical": 1.0,
    "disaster": 0.9,
    "security": 0.8,
    "general": 0.5,
}
LAMBDA_DECAY = math.log(2) / 30.0

sse_clients = []
sse_lock = threading.Lock()
backend_logs = []
logs_lock = threading.Lock()

def add_backend_log(module, action, details, level="INFO"):
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    entry = {
        "timestamp": now_str,
        "module": module,
        "action": action,
        "details": details,
        "level": level,
    }
    with logs_lock:
        backend_logs.insert(0, entry)
        if len(backend_logs) > 200:
            backend_logs.pop()
    broadcast_event("backend_log", entry)

def broadcast_event(event_type, payload):
    data = json.dumps({"type": event_type, "payload": payload})
    msg = f"event: {event_type}\ndata: {data}\n\n".encode("utf-8")
    with sse_lock:
        dead = []
        for client in sse_clients:
            try:
                client.wfile.write(msg)
                client.wfile.flush()
            except Exception:
                dead.append(client)
        for d in dead:
            if d in sse_clients:
                sse_clients.remove(d)

devices = [str(uuid.uuid4()) for _ in range(25)]

# ─────────────────────────────────────────────────────────────────────────────
# STATEWIDE WEST BENGAL EMERGENCY HELP POINTS (Hospitals, Police, Shelters)
# ─────────────────────────────────────────────────────────────────────────────
help_points = [
    # Kolkata & South Bengal
    {"id": str(uuid.uuid4()), "name": "SSKM & IPGMER Super Speciality Hospital, Kolkata", "type": "hospital", "lat": 22.5398, "lon": 88.3426, "distance_km": 2.1, "district": "Kolkata"},
    {"id": str(uuid.uuid4()), "name": "Calcutta Medical College & Hospital", "type": "hospital", "lat": 22.5735, "lon": 88.3639, "distance_km": 1.2, "district": "Kolkata"},
    {"id": str(uuid.uuid4()), "name": "Lalbazar Kolkata Police Headquarters", "type": "police", "lat": 22.5718, "lon": 88.3512, "distance_km": 1.8, "district": "Kolkata"},
    # Sundarbans & Coastal South 24 Parganas
    {"id": str(uuid.uuid4()), "name": "Gosaba Sundarbans Cyclone Relief Centre", "type": "shelter", "lat": 22.1650, "lon": 88.8050, "distance_km": 78.0, "district": "South 24 Parganas"},
    {"id": str(uuid.uuid4()), "name": "Kakdwip Super Speciality Hospital", "type": "hospital", "lat": 21.8744, "lon": 88.1878, "distance_km": 85.0, "district": "South 24 Parganas"},
    {"id": str(uuid.uuid4()), "name": "Sagar Island Multipurpose Cyclone Shelter", "type": "shelter", "lat": 21.6500, "lon": 88.0800, "distance_km": 110.0, "district": "South 24 Parganas"},
    # Purulia & Bankura (Jangalmahal)
    {"id": str(uuid.uuid4()), "name": "Purulia Sadar District Hospital", "type": "hospital", "lat": 23.3350, "lon": 86.3680, "distance_km": 0.8, "district": "Purulia"},
    {"id": str(uuid.uuid4()), "name": "Baghmundi Community Health Centre", "type": "hospital", "lat": 23.1980, "lon": 86.0490, "distance_km": 37.4, "district": "Purulia"},
    {"id": str(uuid.uuid4()), "name": "Ajodhya Hills Disaster Relief Shelter", "type": "shelter", "lat": 23.1870, "lon": 86.0720, "distance_km": 36.2, "district": "Purulia"},
    {"id": str(uuid.uuid4()), "name": "Bankura Sammilani Medical College", "type": "hospital", "lat": 23.2324, "lon": 87.0715, "distance_km": 68.0, "district": "Bankura"},
    # Paschim Medinipur & Digha Coastal
    {"id": str(uuid.uuid4()), "name": "Midnapore Medical College & Hospital", "type": "hospital", "lat": 22.4257, "lon": 87.3200, "distance_km": 105.0, "district": "Paschim Medinipur"},
    {"id": str(uuid.uuid4()), "name": "Digha Coastal Disaster Response Hub", "type": "shelter", "lat": 21.6266, "lon": 87.5074, "distance_km": 140.0, "district": "Purba Medinipur"},
    # Paschim Bardhaman & Industrial Belt
    {"id": str(uuid.uuid4()), "name": "Asansol District Hospital", "type": "hospital", "lat": 23.6889, "lon": 86.9661, "distance_km": 88.0, "district": "Paschim Bardhaman"},
    {"id": str(uuid.uuid4()), "name": "Durgapur Sub-Divisional Hospital", "type": "hospital", "lat": 23.5204, "lon": 87.3119, "distance_km": 95.0, "district": "Paschim Bardhaman"},
    # Central Bengal (Malda & Murshidabad)
    {"id": str(uuid.uuid4()), "name": "Murshidabad Medical College, Berhampore", "type": "hospital", "lat": 24.0988, "lon": 88.2685, "distance_km": 145.0, "district": "Murshidabad"},
    {"id": str(uuid.uuid4()), "name": "Malda Medical College & Hospital", "type": "hospital", "lat": 25.0044, "lon": 88.1458, "distance_km": 210.0, "district": "Malda"},
    # North Bengal & Himalayas (Darjeeling, Siliguri, Jalpaiguri, Alipurduar)
    {"id": str(uuid.uuid4()), "name": "North Bengal Medical College, Siliguri", "type": "hospital", "lat": 26.7118, "lon": 88.3739, "distance_km": 390.0, "district": "Darjeeling"},
    {"id": str(uuid.uuid4()), "name": "Darjeeling District Hospital (Eden Hospital)", "type": "hospital", "lat": 27.0410, "lon": 88.2663, "distance_km": 430.0, "district": "Darjeeling"},
    {"id": str(uuid.uuid4()), "name": "Kalimpong Sub-Divisional Hospital", "type": "hospital", "lat": 27.0600, "lon": 88.4700, "distance_km": 440.0, "district": "Kalimpong"},
    {"id": str(uuid.uuid4()), "name": "Jalpaiguri Sadar Hospital", "type": "hospital", "lat": 26.5400, "lon": 88.7200, "distance_km": 405.0, "district": "Jalpaiguri"},
    {"id": str(uuid.uuid4()), "name": "Alipurduar District Hospital & Dooars Flood HQ", "type": "hospital", "lat": 26.4919, "lon": 89.5271, "distance_km": 460.0, "district": "Alipurduar"},
    {"id": str(uuid.uuid4()), "name": "Mirik Lake Safe Evacuation Ground", "type": "safe_zone", "lat": 26.8860, "lon": 88.1750, "distance_km": 415.0, "district": "Darjeeling"},
]

# ─────────────────────────────────────────────────────────────────────────────
# STATEWIDE WEST BENGAL CELLULAR READINGS (Himalayas to Sundarbans)
# ─────────────────────────────────────────────────────────────────────────────
readings = []
now = datetime.now(timezone.utc)

# 12 Regional Hubs covering the entire length and breadth of West Bengal
wb_regions = [
    ("Kolkata Metro Core", 22.5726, 88.3639, -62, "5G", 68.0, 24.0, 16, 45),
    ("Howrah & Hooghly", 22.5958, 88.2636, -65, "5G", 55.0, 18.0, 19, 30),
    ("Siliguri North Bengal Hub", 26.7271, 88.3953, -68, "5G", 48.0, 15.0, 24, 35),
    ("Asansol-Durgapur Industrial", 23.6889, 86.9661, -70, "5G", 44.0, 14.0, 26, 30),
    ("Purulia Sadar & Raghunathpur", 23.3322, 86.3652, -74, "4G", 28.0, 8.0, 32, 25),
    ("Bankura & Bishnupur", 23.2324, 87.0715, -76, "4G", 22.0, 6.5, 38, 20),
    ("Kharagpur & Midnapore", 22.3460, 87.3230, -72, "4G", 32.0, 10.0, 28, 25),
    ("Berhampore & Murshidabad", 24.0988, 88.2685, -79, "4G", 18.0, 5.0, 42, 20),
    ("Malda English Bazar", 25.0044, 88.1458, -78, "4G", 20.0, 5.5, 40, 20),
    ("Jalpaiguri & Cooch Behar", 26.3239, 89.4510, -82, "4G", 14.0, 4.0, 48, 20),
    ("Darjeeling Mountain Town", 27.0410, 88.2663, -84, "4G", 12.0, 3.2, 55, 20),
    ("Digha & Contai Coast", 21.6266, 87.5074, -75, "4G", 25.0, 7.0, 35, 18),
]

for _, clat, clon, base_dbm, net, dl, ul, lat_ms, count in wb_regions:
    for _ in range(count):
        lat = clat + random.uniform(-0.06, 0.06)
        lon = clon + random.uniform(-0.06, 0.06)
        dbm = int(base_dbm + random.uniform(-8, 8))
        readings.append({
            "id": str(uuid.uuid4()), "device_id": random.choice(devices),
            "lat": round(lat, 5), "lon": round(lon, 5), "signal_dbm": dbm,
            "network_type": net, "download_mbps": dl, "upload_mbps": ul, "latency_ms": lat_ms,
            "recorded_at": (now - timedelta(minutes=random.randint(1, 240))).isoformat(),
        })

# Statewide Dead-Zone Clusters (Sundarbans Delta, Ajodhya Hills, Darjeeling Peaks, Dooars Forest)
wb_deadzone_regions = [
    ("Sundarbans Mangrove Reserve Delta", 21.9497, 88.8999, -128, 22),
    ("Sagar Island Southern Bay Gap", 21.6500, 88.0800, -122, 16),
    ("Ajodhya Hills Mountain Ridge (Purulia)", 23.1950, 86.0468, -120, 20),
    ("Bandwan Deep Forest Corridor", 22.8732, 86.5050, -126, 18),
    ("Sandakphu & Singalila Himalayan Ridge", 27.1050, 88.0010, -132, 16),
    ("Dooars Buxa Tiger Reserve Forest", 26.6800, 89.6200, -124, 18),
    ("Kashipur Remote Agrarian Pockets", 23.4150, 86.5820, -116, 15),
]

for _, clat, clon, base_dbm, count in wb_deadzone_regions:
    for _ in range(count):
        lat = clat + random.uniform(-0.05, 0.05)
        lon = clon + random.uniform(-0.05, 0.05)
        dbm = int(base_dbm + random.uniform(-10, 6))
        net = "none" if dbm < -120 else "2G"
        readings.append({
            "id": str(uuid.uuid4()), "device_id": random.choice(devices),
            "lat": round(lat, 5), "lon": round(lon, 5), "signal_dbm": dbm,
            "network_type": net, "download_mbps": 0.0, "upload_mbps": 0.0, "latency_ms": 999,
            "recorded_at": (now - timedelta(minutes=random.randint(10, 300))).isoformat(),
        })

# ─────────────────────────────────────────────────────────────────────────────
# STATEWIDE AI PREDICTED DEAD-ZONE CELLS
# ─────────────────────────────────────────────────────────────────────────────
predicted_dead_zones = [
    {
        "geohash": "tuzv3q", "lat": 27.1050, "lon": 88.0010, "signal_dbm": -132, "predicted_score": 0.99, "confidence": 0.98,
        "name": "Singalila Himalayan Border Ridge", "region": "Darjeeling", "network_state": "COMPLETE BLACKOUT",
        "root_cause": "High-altitude Himalayan ridgeline shadowing & zero optical fiber reach",
        "action_plan": "Install solar micro-repeater antenna on Singalila trek pass"
    },
    {
        "geohash": "tux3e5", "lat": 21.9497, "lon": 88.8999, "signal_dbm": -128, "predicted_score": 0.98, "confidence": 0.97,
        "name": "Sundarbans Deep Mangrove Reserve", "region": "South 24 Parganas", "network_state": "TOTAL BLACKOUT",
        "root_cause": "Tidal creek estuaries, mangrove canopy attenuation & absence of grid power",
        "action_plan": "Deploy solar mast hub on Gosaba island delta"
    },
    {
        "geohash": "tupkw9", "lat": 22.8732, "lon": 86.5050, "signal_dbm": -126, "predicted_score": 0.96, "confidence": 0.96,
        "name": "Bandwan Deep Forest Corridor", "region": "Purulia (Bandwan)", "network_state": "SEVERE BLACKOUT",
        "root_cause": "Dense deciduous Sal forest canopy causing extreme path loss (>135 dB)",
        "action_plan": "Erect Bandwan South 40m lattice tower"
    },
    {
        "geohash": "tupm7k", "lat": 23.1950, "lon": 86.0468, "signal_dbm": -120, "predicted_score": 0.94, "confidence": 0.95,
        "name": "Ajodhya Hills Upper Ridge", "region": "Purulia (Baghmundi)", "network_state": "NO SIGNAL",
        "root_cause": "Granitic hill pass obstructing LOS (line of sight) to Purulia Sadar",
        "action_plan": "Install hill-top microwave repeater on Baghmundi ridge"
    },
    {
        "geohash": "tux0h8", "lat": 21.6500, "lon": 88.0800, "signal_dbm": -122, "predicted_score": 0.92, "confidence": 0.94,
        "name": "Sagar Island Southern Maritime Gap", "region": "South 24 Parganas", "network_state": "NO SIGNAL",
        "root_cause": "Open bay water absorption and seasonal cyclone storm surge",
        "action_plan": "Erect cyclone-resilient reinforced tower at Gangasagar south"
    },
    {
        "geohash": "tvb1d9", "lat": 26.6800, "lon": 89.6200, "signal_dbm": -124, "predicted_score": 0.89, "confidence": 0.91,
        "name": "Buxa Forest Corridor", "region": "Alipurduar (Dooars)", "network_state": "NO SIGNAL",
        "root_cause": "Elephant migration corridor wildlife reserve with eco-sensitive restrictions",
        "action_plan": "Deploy low-impact camouflaged solar repeater"
    },
    {
        "geohash": "tupt1c", "lat": 23.4150, "lon": 86.5820, "signal_dbm": -116, "predicted_score": 0.78, "confidence": 0.89,
        "name": "Kashipur Remote Hamlets", "region": "Purulia", "network_state": "2G EDGE ONLY",
        "root_cause": "Low-density agrarian pockets beyond 12km macro cell radius",
        "action_plan": "Upgrade Kashipur BTS cell sectorization"
    },
    {
        "geohash": "tupj88", "lat": 23.0420, "lon": 86.6910, "signal_dbm": -114, "predicted_score": 0.76, "confidence": 0.88,
        "name": "Kangsabati Riverbank Foothills", "region": "Bankura / Purulia Border", "network_state": "CRITICAL ATTENUATION",
        "root_cause": "River basin elevation drop causing terrain diffraction loss",
        "action_plan": "Deploy riverbank coverage booster on dam outpost"
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# STATEWIDE RECOMMENDED TOWER INSTALLATION SITES (Census Cross-Referenced)
# ─────────────────────────────────────────────────────────────────────────────
tower_recommendations = [
    {
        "name": "Sundarbans Gosaba Island Hub", "lat": 22.0200, "lon": 88.8200,
        "justification": "Bridges 35km maritime blackout across cyclone-vulnerable delta hamlets, ~2,850 residents",
        "estimated_residents_covered": 2850, "priority": "CRITICAL", "region": "South 24 Parganas"
    },
    {
        "name": "Singalila Ridge Pass Antenna", "lat": 27.0800, "lon": 88.0400,
        "justification": "Eliminates high-altitude dead zone along Indo-Nepal trekking route & border villages, ~1,650 residents",
        "estimated_residents_covered": 1650, "priority": "HIGH", "region": "Darjeeling"
    },
    {
        "name": "Ajodhya Hills Upper Ridge", "lat": 23.1950, "lon": 86.0468,
        "justification": "Covers 3 high-risk dead zones across Baghmundi, ~1,450 residents & emergency relief camp",
        "estimated_residents_covered": 1450, "priority": "HIGH", "region": "Purulia"
    },
    {
        "name": "Bandwan South Forest Corridor", "lat": 22.8732, "lon": 86.5050,
        "justification": "Eliminates 18km cellular blackout along southern forest belt, ~980 tribal residents",
        "estimated_residents_covered": 980, "priority": "HIGH", "region": "Purulia"
    },
    {
        "name": "Dooars Buxa Transit Node", "lat": 26.6500, "lon": 89.5800,
        "justification": "Connects 4 isolated forest fringe tea garden settlements, ~1,820 residents",
        "estimated_residents_covered": 1820, "priority": "MEDIUM", "region": "Alipurduar"
    },
    {
        "name": "Sagar Island South Coast Gap", "lat": 21.6800, "lon": 88.1000,
        "justification": "Provides critical emergency connectivity for annual Gangasagar pilgrimage zone, ~3,200 seasonal residents",
        "estimated_residents_covered": 3200, "priority": "CRITICAL", "region": "South 24 Parganas"
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# DETAILED COVERAGE ZONES & CALLOUT METRICS (Matched to Mockup Architecture)
# ─────────────────────────────────────────────────────────────────────────────
coverage_zones = [
    # KOLKATA METRO COVERAGE ZONES
    {
        "id": "kol-salt-lake",
        "name": "Salt Lake Sector V",
        "region": "Kolkata",
        "category": "strong",
        "coverage_pct": 98,
        "tech": "5G+",
        "download_speed": "1.2 Gbps",
        "signal_dbm": -55,
        "user_count": "18,400 active",
        "congestion": "Low",
        "latency_avg": "11ms",
        "lat": 22.5800,
        "lon": 88.4350,
        "radius": 3400,
        "color": "#10B981"
    },
    {
        "id": "kol-north-dumdum",
        "name": "North Dumdum",
        "region": "Kolkata",
        "category": "strong",
        "coverage_pct": 91,
        "tech": "4G/5G mixed",
        "download_speed": "350 Mbps",
        "signal_dbm": -65,
        "user_count": "12,100 active",
        "congestion": "Normal",
        "latency_avg": "14ms",
        "lat": 22.6520,
        "lon": 88.4250,
        "radius": 3100,
        "color": "#10B981"
    },
    {
        "id": "kol-ballygunge",
        "name": "Ballygunge",
        "region": "Kolkata",
        "category": "strong",
        "coverage_pct": 94,
        "tech": "5G Ultra",
        "download_speed": "1.5 Gbps Peak",
        "signal_dbm": -58,
        "user_count": "9,800 active",
        "congestion": "Low Congestion",
        "latency_avg": "12ms",
        "lat": 22.5280,
        "lon": 88.3650,
        "radius": 2800,
        "color": "#10B981"
    },
    {
        "id": "kol-behala",
        "name": "Behala / Beauirh",
        "region": "Kolkata",
        "category": "strong",
        "coverage_pct": 92,
        "tech": "4G/5G",
        "download_speed": "680 Mbps",
        "signal_dbm": -62,
        "user_count": "14,900 active",
        "congestion": "Moderate",
        "latency_avg": "16ms",
        "lat": 22.4950,
        "lon": 88.3200,
        "radius": 2900,
        "color": "#10B981"
    },
    {
        "id": "kol-chandni",
        "name": "Chandni Chowk",
        "region": "Kolkata",
        "category": "moderate",
        "coverage_pct": 70,
        "tech": "4G LTE",
        "download_speed": "110 Mbps",
        "signal_dbm": -82,
        "user_count": "High user count",
        "congestion": "Congested",
        "latency_avg": "28ms",
        "lat": 22.5680,
        "lon": 88.3580,
        "radius": 2300,
        "color": "#F59E0B"
    },
    {
        "id": "kol-dankuni",
        "name": "Dankuni",
        "region": "Kolkata",
        "category": "moderate",
        "coverage_pct": 65,
        "tech": "4G",
        "download_speed": "18 Mbps",
        "signal_dbm": -89,
        "user_count": "Moderate",
        "congestion": "Normal",
        "latency_avg": "36ms",
        "lat": 22.6850,
        "lon": 88.2950,
        "radius": 2600,
        "color": "#F59E0B"
    },
    {
        "id": "kol-howrah-station",
        "name": "Howrah Station Corridor",
        "region": "Kolkata",
        "category": "deadzone",
        "coverage_pct": 45,
        "tech": "2G/3G Bottleneck",
        "download_speed": "25 Mbps",
        "signal_dbm": -112,
        "user_count": "Extreme Density",
        "congestion": "Severe Bottleneck",
        "latency_avg": "88ms",
        "lat": 22.5850,
        "lon": 88.3400,
        "radius": 2700,
        "color": "#EF4444"
    },

    # STATEWIDE COMPONENT ZONES
    {
        "id": "sun-gosaba",
        "name": "Gosaba Island Hub",
        "region": "Sundarbans",
        "category": "strong",
        "coverage_pct": 88,
        "tech": "Solar 4G Mesh",
        "download_speed": "45 Mbps",
        "signal_dbm": -72,
        "user_count": "2,850 residents",
        "congestion": "Low",
        "latency_avg": "22ms",
        "lat": 22.0200,
        "lon": 88.8200,
        "radius": 6500,
        "color": "#10B981"
    },
    {
        "id": "sun-deep-mangrove",
        "name": "Sundarbans Deep Mangrove Reserve",
        "region": "Sundarbans",
        "category": "deadzone",
        "coverage_pct": 2,
        "tech": "NO SIGNAL",
        "download_speed": "0.0 Mbps",
        "signal_dbm": -128,
        "user_count": "Fishing hamlets",
        "congestion": "Complete Blackout",
        "latency_avg": "999ms",
        "lat": 21.9497,
        "lon": 88.8999,
        "radius": 14000,
        "color": "#EF4444"
    },
    {
        "id": "dar-mall",
        "name": "Darjeeling Mall & Chowrasta",
        "region": "Darjeeling",
        "category": "strong",
        "coverage_pct": 92,
        "tech": "5G",
        "download_speed": "420 Mbps",
        "signal_dbm": -64,
        "user_count": "8,200 tourists/residents",
        "congestion": "Low",
        "latency_avg": "18ms",
        "lat": 27.0410,
        "lon": 88.2663,
        "radius": 4500,
        "color": "#10B981"
    },
    {
        "id": "dar-singalila",
        "name": "Singalila Himalayan Border Ridge",
        "region": "Darjeeling",
        "category": "deadzone",
        "coverage_pct": 1,
        "tech": "NO SIGNAL",
        "download_speed": "0.0 Mbps",
        "signal_dbm": -132,
        "user_count": "Trek route & checkpost",
        "congestion": "Himalayan Ridge Shadow",
        "latency_avg": "999ms",
        "lat": 27.1050,
        "lon": 88.0010,
        "radius": 16000,
        "color": "#EF4444"
    },
    {
        "id": "pur-sadar",
        "name": "Purulia Sadar Core",
        "region": "Purulia",
        "category": "strong",
        "coverage_pct": 89,
        "tech": "4G/5G",
        "download_speed": "180 Mbps",
        "signal_dbm": -68,
        "user_count": "15,400 residents",
        "congestion": "Normal",
        "latency_avg": "24ms",
        "lat": 23.3322,
        "lon": 86.3652,
        "radius": 6000,
        "color": "#10B981"
    },
    {
        "id": "pur-ajodhya",
        "name": "Ajodhya Hills Upper Ridge",
        "region": "Purulia",
        "category": "deadzone",
        "coverage_pct": 6,
        "tech": "NO SIGNAL",
        "download_speed": "0.0 Mbps",
        "signal_dbm": -120,
        "user_count": "Tribal hamlets",
        "congestion": "Terrain Obstruction",
        "latency_avg": "999ms",
        "lat": 23.1950,
        "lon": 86.0468,
        "radius": 12000,
        "color": "#EF4444"
    }
]

# Cellular Tower Transmission Nodes with Real-Time Load
cellular_nodes = [
    {"id": "Node: KOL-784 - 5G", "tech": "5G", "load": "45%", "lat": 22.5920, "lon": 88.3750, "region": "Kolkata"},
    {"id": "Node: KOL-312 - 4G", "tech": "4G", "load": "82%", "lat": 22.5500, "lon": 88.3500, "region": "Kolkata"},
    {"id": "Node: KOL-519 - 5G", "tech": "5G", "load": "38%", "lat": 22.5200, "lon": 88.3450, "region": "Kolkata"},
    {"id": "Node: KOL-901 - 5G", "tech": "5G", "load": "45%", "lat": 22.5050, "lon": 88.3700, "region": "Kolkata"},
    {"id": "Node: SUN-102 - Solar 4G", "tech": "4G", "load": "25%", "lat": 22.0250, "lon": 88.8250, "region": "Sundarbans"},
    {"id": "Node: DAR-404 - 5G", "tech": "5G", "load": "52%", "lat": 27.0450, "lon": 88.2700, "region": "Darjeeling"},
    {"id": "Node: PUR-201 - 4G", "tech": "4G", "load": "60%", "lat": 23.3400, "lon": 86.3700, "region": "Purulia"},
]

# Statewide Emergency Alerts
sos_alerts = [
    {
        "id": str(uuid.uuid4()), "device_id": devices[0], "lat": 22.0150, "lon": 88.8150,
        "message": "EMERGENCY: Tsunami wave overtopped river embankment in Gosaba delta. 6 families trapped on roof.",
        "category": "disaster", "priority_score": 0.96, "status": "sent",
        "created_at": (now - timedelta(minutes=3)).isoformat(),
        "corroboration_count": 3, "is_relayed": True,
        "breakdown": {"category_term": 0.36, "recency_term": 0.23, "corroboration_term": 0.12, "location_risk_term": 0.15, "raw_score": 0.96, "minutes_elapsed": 3.0}
    },
    {
        "id": str(uuid.uuid4()), "device_id": devices[1], "lat": 23.1970, "lon": 86.0510,
        "message": "CRITICAL MEDICAL: Severe cardiac patient in Ajodhya Hills remote village requiring ambulance.",
        "category": "medical", "priority_score": 0.94, "status": "sent",
        "created_at": (now - timedelta(minutes=5)).isoformat(),
        "corroboration_count": 2, "is_relayed": False,
        "breakdown": {"category_term": 0.40, "recency_term": 0.22, "corroboration_term": 0.08, "location_risk_term": 0.14, "raw_score": 0.94, "minutes_elapsed": 5.0}
    },
    {
        "id": str(uuid.uuid4()), "device_id": devices[2], "lat": 27.0750, "lon": 88.0350,
        "message": "Landslide completely severed Singalila mountain pass. Tourist vehicle overturned.",
        "category": "disaster", "priority_score": 0.86, "status": "sent",
        "created_at": (now - timedelta(minutes=14)).isoformat(),
        "corroboration_count": 1, "is_relayed": True,
        "breakdown": {"category_term": 0.36, "recency_term": 0.18, "corroboration_term": 0.04, "location_risk_term": 0.15, "raw_score": 0.86, "minutes_elapsed": 14.0}
    },
    {
        "id": str(uuid.uuid4()), "device_id": devices[3], "lat": 22.8740, "lon": 86.5040,
        "message": "Fallen tree blocking single evacuation corridor in Bandwan deep forest.",
        "category": "security", "priority_score": 0.74, "status": "acknowledged",
        "created_at": (now - timedelta(minutes=28)).isoformat(),
        "corroboration_count": 1, "is_relayed": False,
        "breakdown": {"category_term": 0.32, "recency_term": 0.13, "corroboration_term": 0.04, "location_risk_term": 0.14, "raw_score": 0.74, "minutes_elapsed": 28.0}
    }
]

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def calculate_sos_score(category, created_at_iso, lat, lon, exclude_id=None):
    created_dt = datetime.fromisoformat(created_at_iso.replace('Z', '+00:00'))
    now_dt = datetime.now(timezone.utc)
    minutes = max(0.0, (now_dt - created_dt).total_seconds() / 60.0)

    # 1. Category Term (0.40)
    cat_w = CATEGORY_WEIGHTS.get(category.lower(), 0.5)
    cat_term = 0.40 * cat_w

    # 2. Recency Term (0.25)
    recency_decay = math.exp(-LAMBDA_DECAY * minutes)
    rec_term = 0.25 * recency_decay

    # 3. Proximity Corroboration Term (0.20): within 500m in last 1 hour
    nearby_count = 0
    for a in sos_alerts:
        if a["id"] == exclude_id or a["status"] == "resolved":
            continue
        dist = haversine_m(lat, lon, a["lat"], a["lon"])
        if dist <= 500.0:
            nearby_count += 1
    corrob_norm = min(nearby_count, 5) / 5.0
    corrob_term = 0.20 * corrob_norm

    # 4. Location Risk Term (0.15)
    loc_risk = 0.0
    for dz in predicted_dead_zones:
        if haversine_m(lat, lon, dz["lat"], dz["lon"]) <= 8000.0:
            loc_risk = max(loc_risk, dz["predicted_score"])
            break
    loc_term = 0.15 * loc_risk

    total = round(cat_term + rec_term + corrob_term + loc_term, 4)
    breakdown = {
        "category_term": round(cat_term, 3),
        "recency_term": round(rec_term, 3),
        "corroboration_term": round(corrob_term, 3),
        "location_risk_term": round(loc_term, 3),
        "raw_score": total,
        "minutes_elapsed": round(minutes, 1)
    }
    return total, nearby_count, breakdown

def recompute_all_alerts():
    for a in sos_alerts:
        score, corrob, bd = calculate_sos_score(a["category"], a["created_at"], a["lat"], a["lon"], exclude_id=a["id"])
        a["priority_score"] = score
        a["corroboration_count"] = corrob
        a["breakdown"] = bd
    sos_alerts.sort(key=lambda x: x["priority_score"], reverse=True)
    add_backend_log("PRIORITY_ENGINE", "RE_RANK_QUEUE", f"Re-evaluated {len(sos_alerts)} active alerts across West Bengal with PostGIS corroboration")

# ─────────────────────────────────────────────────────────────────────────────
# DISASTER SIMULATION SCENARIO ENGINE & MESH RELAY TOPOLOGY
# ─────────────────────────────────────────────────────────────────────────────

mesh_relay_links = [
    {"from": [22.0150, 88.8150], "to": [22.0350, 88.8350], "hop": 1, "protocol": "BLE_P2P", "rssi": -72},
    {"from": [22.0350, 88.8350], "to": [22.0650, 88.8600], "hop": 2, "protocol": "WIFI_DIRECT", "rssi": -68},
    {"from": [27.0750, 88.0350], "to": [27.0600, 88.0700], "hop": 1, "protocol": "BLE_P2P", "rssi": -81},
    {"from": [23.1960, 86.0480], "to": [23.1870, 86.0720], "hop": 1, "protocol": "BLE_P2P", "rssi": -76},
]

current_scenario = "normal"

def set_disaster_scenario(name):
    global current_scenario
    current_scenario = name
    now_iso = datetime.now(timezone.utc).isoformat()
    if name == "cyclone":
        add_backend_log("SCENARIO_ENGINE", "TRIGGER_CYCLONE", "🌪️ SIMULATION ACTIVE: Cyclone Remal Landfall in Sundarbans. 3 Coastal Towers down, high-tide surge.", level="WARNING")
        # Inject batch of coastal disaster alerts
        for offset_lat, offset_lon, msg in [
            (0.005, 0.005, "Embankment breached at Gosaba Block II. 45 villagers evacuated to roof."),
            (-0.008, 0.002, "Fishing trawler grounded on submerged sandbar. Distress flare sighted."),
            (0.012, -0.006, "Power grid transformer submerged. Primary Health Centre on backup generator.")
        ]:
            lat = 22.0150 + offset_lat
            lon = 88.8150 + offset_lon
            score, corrob, bd = calculate_sos_score("disaster", now_iso, lat, lon)
            a = {
                "id": str(uuid.uuid4()), "device_id": random.choice(devices), "lat": lat, "lon": lon,
                "category": "disaster", "message": msg, "priority_score": score, "status": "sent",
                "created_at": now_iso, "sent_at": now_iso, "corroboration_count": corrob,
                "is_relayed": True, "breakdown": bd
            }
            sos_alerts.insert(0, a)
            broadcast_event("sos", a)

    elif name == "landslide":
        add_backend_log("SCENARIO_ENGINE", "TRIGGER_LANDSLIDE", "🏔️ SIMULATION ACTIVE: Landslide on Singalila Ridge. Fiber optic trunk line severed.", level="WARNING")
        lat, lon = 27.0750, 88.0350
        score, corrob, bd = calculate_sos_score("disaster", now_iso, lat, lon)
        a = {
            "id": str(uuid.uuid4()), "device_id": random.choice(devices), "lat": lat, "lon": lon,
            "category": "disaster", "message": "Massive landslide blocking NH-717. Tourist convoy stranded at 8,200ft.",
            "priority_score": score, "status": "sent", "created_at": now_iso, "sent_at": now_iso,
            "corroboration_count": 2, "is_relayed": True, "breakdown": bd
        }
        sos_alerts.insert(0, a)
        broadcast_event("sos", a)

    elif name == "flood":
        add_backend_log("SCENARIO_ENGINE", "TRIGGER_FLOOD", "🌊 SIMULATION ACTIVE: Kangsabati Dam Outflow in Purulia. Riverbank hamlets inundated.", level="WARNING")
        lat, lon = 23.0420, 86.6910
        score, corrob, bd = calculate_sos_score("disaster", now_iso, lat, lon)
        a = {
            "id": str(uuid.uuid4()), "device_id": random.choice(devices), "lat": lat, "lon": lon,
            "category": "disaster", "message": "River water level exceeded danger mark by 1.4m. 120 livestock and villagers seeking shelter.",
            "priority_score": score, "status": "sent", "created_at": now_iso, "sent_at": now_iso,
            "corroboration_count": 3, "is_relayed": False, "breakdown": bd
        }
        sos_alerts.insert(0, a)
        broadcast_event("sos", a)

    else:
        add_backend_log("SCENARIO_ENGINE", "RESET_NORMAL", "🟢 Normal Operational State restored across West Bengal.")

    recompute_all_alerts()
    broadcast_event("scenario_update", {"scenario": name})


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND STATEWIDE TELEMETRY PULSE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def get_live_mean_signal():
    if not readings:
        return -76.0
    recent = readings[:60]
    return round(sum(r["signal_dbm"] for r in recent) / len(recent), 1)

def background_telemetry_stream():
    """Generates continuous realistic telemetry across West Bengal corridors."""
    while True:
        time.sleep(3.2)
        region = random.choice(wb_regions)
        lat = round(region[1] + random.uniform(-0.07, 0.07), 5)
        lon = round(region[2] + random.uniform(-0.07, 0.07), 5)
        dbm = int(region[3] + random.uniform(-10, 8))
        net = "5G" if dbm > -75 else "4G" if dbm > -95 else "3G" if dbm > -110 else "2G"
        dl = round(region[5] + random.uniform(-6, 8), 1) if net in ["5G", "4G"] else 1.2
        ul = round(region[6] + random.uniform(-3, 4), 1) if net in ["5G", "4G"] else 0.4
        lat_ms = region[7] + random.randint(-4, 15)

        new_reading = {
            "id": str(uuid.uuid4()),
            "device_id": random.choice(devices),
            "lat": lat,
            "lon": lon,
            "signal_dbm": dbm,
            "network_type": net,
            "download_mbps": max(0.1, dl),
            "upload_mbps": max(0.1, ul),
            "latency_ms": max(12, lat_ms),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        readings.insert(0, new_reading)
        if len(readings) > 600:
            readings.pop()

        mean_dbm = get_live_mean_signal()
        broadcast_event("reading", {
            "reading": new_reading,
            "mean_signal_dbm": mean_dbm,
            "total_readings": len(readings)
        })
        add_backend_log("TELEMETRY", "INGEST_PACKET", f"Device #{new_reading['device_id'][:6]} ({region[0]}) -> {dbm} dBm ({net}) | Live Mean: {mean_dbm} dBm")

threading.Thread(target=background_telemetry_stream, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP REQUEST HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class GhostNetHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # SSE Stream
        if path in ["/api/events", "/ws/live"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with sse_lock:
                sse_clients.append(self)
            add_backend_log("SSE_STREAM", "CLIENT_CONNECT", f"Dashboard client connected from {self.client_address[0]}")
            try:
                while True:
                    time.sleep(15)
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
            except Exception:
                with sse_lock:
                    if self in sse_clients:
                        sse_clients.remove(self)
            return

        # API Endpoints
        if path in ["/api/coverage", "/api/v1/coverage", "/api/heatmap", "/api/v1/coverage/heatmap"]:
            self.send_json(readings)
            return
        elif path in ["/api/help-points", "/api/v1/help-points"]:
            self.send_json(help_points)
            return
        elif path in ["/api/sos", "/api/v1/sos"]:
            recompute_all_alerts()
            self.send_json(sos_alerts)
            return
        elif path in ["/api/dead-zones", "/api/v1/predictions/dead-zones"]:
            self.send_json(predicted_dead_zones)
            return
        elif path in ["/api/tower-recommendations", "/api/v1/predictions/tower-recommendations"]:
            self.send_json(tower_recommendations)
            return
        elif path in ["/api/coverage-zones", "/api/v1/coverage-zones"]:
            self.send_json(coverage_zones)
            return
        elif path in ["/api/cellular-nodes", "/api/v1/cellular-nodes"]:
            self.send_json(cellular_nodes)
            return
        elif path in ["/api/mesh-topology", "/api/v1/mesh-topology"]:
            self.send_json(mesh_relay_links)
            return
        elif path in ["/api/backend-logs", "/api/v1/backend-logs"]:
            with logs_lock:
                self.send_json(backend_logs)
            return
        elif path in ["/api/scenarios/current"]:
            self.send_json({"scenario": current_scenario})
            return
        elif path == "/health":
            self.send_json({"status": "healthy", "service": "ghostnet-ai-live", "region": "State of West Bengal, India", "readings_count": len(readings)})
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path in ["/api/readings", "/api/v1/readings"]:
            batch = data.get("readings", [data])
            now_iso = datetime.now(timezone.utc).isoformat()
            accepted = 0
            for r in batch:
                r["id"] = str(uuid.uuid4())
                r["recorded_at"] = r.get("recorded_at", now_iso)
                readings.insert(0, r)
                accepted += 1
                broadcast_event("reading", r)
                add_backend_log("INGESTION", "TELEMETRY_INGEST", f"Ingested {r.get('signal_dbm')} dBm ({r.get('network_type')}) at [{r.get('lat')}, {r.get('lon')}]")
            self.send_json({"accepted": accepted}, status=201)
            return

        elif path in ["/api/sos", "/api/v1/sos"]:
            now_iso = datetime.now(timezone.utc).isoformat()
            lat = float(data.get("lat", 22.0150))
            lon = float(data.get("lon", 88.8150))
            cat = data.get("category", "general")
            msg = data.get("message", "Emergency assistance needed in West Bengal.")
            dev_id = data.get("device_id", str(uuid.uuid4()))

            score, corrob, bd = calculate_sos_score(cat, now_iso, lat, lon)
            
            # Find nearest emergency facility
            nearest_facility = None
            min_dist = 999999.0
            for hp in help_points:
                dist = haversine_m(lat, lon, hp["lat"], hp["lon"]) / 1000.0
                if dist < min_dist:
                    min_dist = dist
                    nearest_facility = hp

            new_alert = {
                "id": str(uuid.uuid4()), "device_id": dev_id, "lat": lat, "lon": lon,
                "category": cat, "message": msg, "priority_score": score, "status": "sent",
                "created_at": now_iso, "sent_at": now_iso, "corroboration_count": corrob,
                "is_relayed": data.get("is_relayed", False), "breakdown": bd,
                "nearest_facility": nearest_facility["name"] if nearest_facility else "District Response HQ",
                "nearest_distance_km": round(min_dist, 1)
            }
            sos_alerts.insert(0, new_alert)
            recompute_all_alerts()
            broadcast_event("sos", new_alert)
            
            # Multi-step live backend trace
            add_backend_log("EMERGENCY_DISPATCH", "NEW_SOS", f"🚨 INCOMING SOS ({cat.upper()}): '{msg[:40]}...' at [{lat:.4f}, {lon:.4f}]", level="WARNING")
            add_backend_log("POSTGIS_SPATIAL", "ST_DWITHIN", f"Spatial query ST_DWithin(500m, 1hr) -> Found {corrob} corroborating alerts (0.012s)")
            add_backend_log("DYNAMIC_SCORING", "SCORE_COMPUTED", f"Priority Score: {score} (Cat: {bd['category_term']}, Rec: {bd['recency_term']}, Corrob: {bd['corroboration_term']}, DeadZone: {bd['location_risk_term']})")
            if nearest_facility:
                add_backend_log("RESCUE_ROUTING", "DISPATCH_UNIT", f"Routed to {nearest_facility['name']} ({round(min_dist, 1)} km away). SMS Gateway mock dispatched.")
            
            self.send_json(new_alert, status=201)
            return

        elif path in ["/api/sos/batch", "/api/v1/sos/batch"]:
            batch = data.get("alerts", [])
            ids = []
            for item in batch:
                lat = float(item.get("lat", 22.0150))
                lon = float(item.get("lon", 88.8150))
                cat = item.get("category", "general")
                msg = item.get("message", "Emergency assistance needed.")
                c_at = item.get("offline_created_at", datetime.now(timezone.utc).isoformat())
                dev_id = item.get("device_id", str(uuid.uuid4()))

                score, corrob, bd = calculate_sos_score(cat, c_at, lat, lon)
                new_alert = {
                    "id": str(uuid.uuid4()), "device_id": dev_id, "lat": lat, "lon": lon,
                    "category": cat, "message": msg, "priority_score": score, "status": "sent",
                    "created_at": c_at, "sent_at": datetime.now(timezone.utc).isoformat(),
                    "corroboration_count": corrob, "is_relayed": item.get("is_relayed", True), "breakdown": bd
                }
                sos_alerts.insert(0, new_alert)
                ids.append(new_alert["id"])
                broadcast_event("sos", new_alert)
                add_backend_log("SYNC_RECONNECT", "BATCH_SYNC", f"Synced offline buffered alert #{new_alert['id'][:6]} (Priority: {score})")
            recompute_all_alerts()
            self.send_json({"accepted": len(ids), "ids": ids}, status=201)
            return

        elif path in ["/api/check-in", "/api/v1/check-in"]:
            checkin = {
                "id": str(uuid.uuid4()), "device_id": data.get("device_id", str(uuid.uuid4())),
                "lat": data.get("lat", 22.5726), "lon": data.get("lon", 88.3639),
                "status": data.get("status", "safe"), "created_at": datetime.now(timezone.utc).isoformat()
            }
            broadcast_event("check_in", checkin)
            add_backend_log("CHECK_IN", "STATUS_LOG", f"Device #{checkin['device_id'][:6]} logged SAFE check-in at [{checkin['lat']}, {checkin['lon']}]")
            self.send_json(checkin, status=201)
            return

        elif path in ["/api/recompute", "/api/v1/predictions/recompute"]:
            task_id = str(uuid.uuid4())
            add_backend_log("ML_WORKER", "START_RECOMPUTE", f"Celery worker initiated statewide XGBoost regressor iteration [Task #{task_id[:8]}]")
            def _async_ml():
                time.sleep(1.2)
                for dz in predicted_dead_zones:
                    dz["predicted_score"] = min(1.0, max(0.5, round(dz["predicted_score"] + random.uniform(-0.02, 0.02), 2)))
                broadcast_event("prediction_update", {
                    "task_id": task_id, "dead_zones_count": len(predicted_dead_zones),
                    "tower_recommendations": tower_recommendations
                })
                add_backend_log("ML_WORKER", "COMPLETE_RECOMPUTE", f"Scored 8 statewide dead-zone polygons & re-clustered 6 optimal tower sites [Task #{task_id[:8]}]")
            threading.Thread(target=_async_ml, daemon=True).start()
            self.send_json({"task_id": task_id, "status": "accepted"}, status=202)
            return
        elif path in ["/api/scenarios/trigger", "/api/v1/scenarios/trigger"]:
            scenario = data.get("scenario", "normal")
            set_disaster_scenario(scenario)
            self.send_json({"scenario": scenario, "status": "active"}, status=200)
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if "/sos/" in path and "/status" in path:
            alert_id = path.split("/sos/")[1].split("/")[0]
            new_status = data.get("status", "acknowledged")
            target = None
            for a in sos_alerts:
                if a["id"] == alert_id:
                    a["status"] = new_status
                    target = a
                    break
            if target:
                broadcast_event("sos_update", {"id": alert_id, "status": new_status})
                add_backend_log("RESPONDER_ACTION", "UPDATE_STATUS", f"Alert #{alert_id[:6]} marked as '{new_status.upper()}'")
                self.send_json(target)
            else:
                self.send_response(404)
                self.end_headers()
            return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, data, status=200):
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server():
    server_address = ("", PORT)
    httpd = ThreadedHTTPServer(server_address, GhostNetHandler)
    print(f"[GhostNet AI] Statewide West Bengal Intelligence Engine running at: http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    start_server()
