// ═══════════════════════════════════════════════════════════════════════════
// GHOSTNET AI — STATEWIDE NETWORK COVERAGE MAP & MOCKUP ENGINE
// ═══════════════════════════════════════════════════════════════════════════

let map;
let tileLayer;
let currentTheme = localStorage.getItem('ghostnet_theme') || 'light';
let currentWorkspaceMode = 'split';
let currentRegion = 'all';

let layerCoverageZones = L.featureGroup();
let layerCellularNodes = L.featureGroup();
let layerDeadZones = L.featureGroup();
let layerSos = L.featureGroup();
let layerMesh = L.featureGroup();
let layerHelpPoints = L.featureGroup();
let heatLayer = null;

let coverageZonesData = [];
let cellularNodesData = [];
let readingsData = [];
let sosData = [];
let deadZonesData = [];
let towerData = [];
let helpPointsData = [];
let meshData = [];
let backendLogsData = [];

let livePacketCount = 0;
let isAirplaneMode = false;
let mobileLanguage = 'en';
let selectedMobileCategory = 'medical';
let localOfflineQueue = [];

// Strict West Bengal State Geographical Boundary
const WB_BOUNDS = L.latLngBounds([21.4, 85.7], [27.4, 89.9]);

// Regional Metadata for In-Map Header Card (Matched to User Reference Image)
const REGION_METADATA = {
  kolkata: {
    city: 'KOLKATA',
    overall: '88.5%',
    avail5g: '62% (+1.5%)',
    volte: '94%',
    latency: '18ms',
    center: [22.5850, 88.3750],
    zoom: 12.2,
  },
  sundarbans: {
    city: 'SUNDARBANS DELTA',
    overall: '42.0%',
    avail5g: '14% (Solar Hub)',
    volte: '68%',
    latency: '54ms',
    center: [21.9800, 88.8500],
    zoom: 10.5,
  },
  darjeeling: {
    city: 'DARJEELING HIMALAYAS',
    overall: '64.5%',
    avail5g: '38% (Town Core)',
    volte: '82%',
    latency: '42ms',
    center: [27.0600, 88.2600],
    zoom: 11.2,
  },
  purulia: {
    city: 'PURULIA DISTRICT',
    overall: '71.2%',
    avail5g: '45% (Sadar BTS)',
    volte: '86%',
    latency: '32ms',
    center: [23.2500, 86.4000],
    zoom: 10.5,
  },
  all: {
    city: 'WEST BENGAL STATE',
    overall: '76.4%',
    avail5g: '52% (+2.1%)',
    volte: '89%',
    latency: '24ms',
    center: [23.6000, 87.8000],
    zoom: 7.8,
  },
};

const DICT = {
  en: {
    appTitle: 'GhostNet Mobile',
    holdTap: 'HOLD / TAP',
    sos: 'SOS',
    safeBtn: "✅ I'm Safe (One-Tap Check-In)",
    catMedical: 'Medical',
    catDisaster: 'Disaster',
    catSecurity: 'Security',
    catGeneral: 'General',
    onlineBanner: '🟢 Online Mode: Connected to GhostNet Gateway.',
    offlineBanner: '✈️ Offline Mode: Drift SQLite Active. Auto-sync on reconnect.',
    safeToast: "Marked 'I am Safe' — Logged & synced.",
    offlineQueuedToast: 'Offline: SOS saved in local SQLite queue.',
    onlineDispatchedToast: 'Online: SOS dispatched directly to emergency queue!',
    airplaneOn: '✈️ Airplane: ON',
    airplaneOff: '✈️ Airplane: OFF',
  },
  hi: {
    appTitle: 'घोस्टनेट मोबाइल',
    holdTap: 'दबाएं या स्पर्श करें',
    sos: 'एसओएस',
    safeBtn: '✅ मैं सुरक्षित हूं (वन-टैप चेक-इन)',
    catMedical: 'चिकित्सा',
    catDisaster: 'आपदा / बाढ़',
    catSecurity: 'सुरक्षा',
    catGeneral: 'सामान्य',
    onlineBanner: '🟢 ऑनलाइन मोड: घोस्टनेट गेटवे से जुड़ा है।',
    offlineBanner: '✈️ ऑफ़लाइन मोड: ड्रिफ्ट एसक्यूलाइट सक्रिय। नेटवर्क आने पर ऑटो-सिंक होगा।',
    safeToast: 'सुरक्षित दर्ज किया गया — रिकॉर्ड सिंक हुआ।',
    offlineQueuedToast: 'ऑफलाइन: एसओएस स्थानीय एसक्यूलाइट में सुरक्षित हुआ।',
    onlineDispatchedToast: 'ऑनलाइन: एसओएस आपातकालीन नियंत्रण कक्ष को भेजा गया!',
    airplaneOn: '✈️ हवाई जहाज मोड: चालू',
    airplaneOff: '✈️ हवाई जहाज मोड: बंद',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  applyTheme(currentTheme);
  initMap();
  loadAllData();
  setupSSE();

  window.addEventListener('resize', () => {
    if (map) map.invalidateSize();
  });
  setTimeout(() => {
    if (map) {
      switchMapRegion('all');
      map.invalidateSize();
    }
  }, 400);
});

// ─────────────────────────────────────────────────────────────────────────────
// MAP INITIALIZATION (High-Definition Clean Voyager / Positron Carto Canvas)
// ─────────────────────────────────────────────────────────────────────────────

function initMap() {
  const meta = REGION_METADATA[currentRegion] || REGION_METADATA.kolkata;

  map = L.map('map', {
    center: meta.center,
    zoom: meta.zoom,
    minZoom: 6.8,
    maxZoom: 18,
    maxBounds: WB_BOUNDS,
    maxBoundsViscosity: 0.9,
    zoomControl: false,
    preferCanvas: true,
  });

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  updateMapTiles();

  layerCoverageZones.addTo(map);
  layerCellularNodes.addTo(map);
  layerDeadZones.addTo(map);
  layerSos.addTo(map);
  layerMesh.addTo(map);
  layerHelpPoints.addTo(map);
}

function updateMapTiles() {
  if (!map) return;
  if (tileLayer) map.removeLayer(tileLayer);

  // Use clean, high-clarity street tiles matching the mockup design
  const tileUrl =
    currentTheme === 'dark'
      ? 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
      : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

  tileLayer = L.tileLayer(tileUrl, {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
    subdomains: 'abcd',
    maxZoom: 19,
    crossOrigin: true,
  }).addTo(map);

  if (heatLayer && map.hasLayer(heatLayer)) {
    heatLayer.bringToFront();
  }
  layerCoverageZones.bringToFront();
  layerCellularNodes.bringToFront();
  layerDeadZones.bringToFront();
  layerSos.bringToFront();
}

function switchMapRegion(regionKey) {
  currentRegion = regionKey;
  const meta = REGION_METADATA[regionKey] || REGION_METADATA.kolkata;

  // 1. Update In-Map Top Header Card
  document.getElementById('covHeaderCity').innerText = meta.city;
  document.getElementById('covHeaderOverall').innerHTML = `Overall Network Coverage: <strong>${meta.overall}</strong>`;
  document.getElementById('cov5gAvail').innerText = meta.avail5g;
  document.getElementById('covVolteQuality').innerText = meta.volte;
  document.getElementById('covLatencyAvg').innerText = meta.latency;

  const sel = document.getElementById('regionSelect');
  if (sel && sel.value !== regionKey) sel.value = regionKey;

  // 2. Smoothly fly map to coordinates
  if (map) {
    map.flyTo(meta.center, meta.zoom, { duration: 1.2 });
  }
}

function setWorkspaceMode(mode) {
  currentWorkspaceMode = mode;
  const container = document.getElementById('workspaceContainer');
  const winSpatial = document.getElementById('windowSpatial');
  const winBackend = document.getElementById('windowBackend');

  ['tabSpatial', 'tabBackend', 'tabSplit'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });

  if (mode === 'spatial') {
    document.getElementById('tabSpatial').classList.add('active');
    container.className = 'workspace-grid single-mode';
    winSpatial.style.display = 'flex';
    winBackend.style.display = 'none';
  } else if (mode === 'backend') {
    document.getElementById('tabBackend').classList.add('active');
    container.className = 'workspace-grid single-mode';
    winSpatial.style.display = 'none';
    winBackend.style.display = 'flex';
  } else {
    document.getElementById('tabSplit').classList.add('active');
    container.className = 'workspace-grid split-mode';
    winSpatial.style.display = 'flex';
    winBackend.style.display = 'flex';
  }

  setTimeout(() => {
    if (map) map.invalidateSize();
  }, 200);
}

function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('ghostnet_theme', currentTheme);
  applyTheme(currentTheme);
  updateMapTiles();
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const icon = document.getElementById('themeIcon');
  if (icon) {
    icon.innerText = theme === 'light' ? '🌙' : '☀️';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// DATA INGESTION & INITIAL LOAD
// ─────────────────────────────────────────────────────────────────────────────

async function loadAllData() {
  try {
    const [covRes, nodesRes, sosRes, dzRes, towersRes, hpRes, meshRes, logsRes, readingsRes] = await Promise.all([
      fetch('/api/coverage-zones').then((r) => r.json()).catch(() => []),
      fetch('/api/cellular-nodes').then((r) => r.json()).catch(() => []),
      fetch('/api/sos').then((r) => r.json()).catch(() => []),
      fetch('/api/dead-zones').then((r) => r.json()).catch(() => []),
      fetch('/api/tower-recommendations').then((r) => r.json()).catch(() => []),
      fetch('/api/help-points').then((r) => r.json()).catch(() => []),
      fetch('/api/mesh-topology').then((r) => r.json()).catch(() => []),
      fetch('/api/backend-logs').then((r) => r.json()).catch(() => []),
      fetch('/api/coverage').then((r) => r.json()).catch(() => []),
    ]);

    coverageZonesData = covRes;
    cellularNodesData = nodesRes;
    sosData = sosRes;
    deadZonesData = dzRes;
    towerData = towersRes;
    helpPointsData = hpRes;
    meshData = meshRes;
    backendLogsData = logsRes;
    readingsData = readingsRes;

    console.log('[GhostNet] Data loaded:', {
      coverageZones: coverageZonesData.length,
      cellularNodes: cellularNodesData.length,
      deadZones: deadZonesData.length,
      readings: readingsData.length,
      sos: sosData.length,
    });

    renderHeatmapLayer();
    renderCoverageZonesAndCallouts();
    renderCellularNodesLayer();
    renderMapDeadZonesLayer();
    renderMapSosLayer();
    renderSosFeed();
    renderHelpPointsList();
    renderTowerTable();
    renderTerminalLogs();
  } catch (err) {
    console.error('Error loading initial data:', err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// SIGNAL STRENGTH HEATMAP (Leaflet.heat — always-on, no toggle)
// ─────────────────────────────────────────────────────────────────────────────

function renderHeatmapLayer() {
  if (!map || !readingsData || readingsData.length === 0) return;

  // Convert readings to heatmap points: [lat, lng, intensity 0-1]
  const points = readingsData.map((r) => {
    // Normalize dBm: -50 = strong (1.0), -140 = dead (0.0)
    const intensity = Math.max(0, Math.min(1, (r.signal_dbm + 140) / 90));
    return [r.lat, r.lon, intensity];
  });

  if (heatLayer && map.hasLayer(heatLayer)) {
    map.removeLayer(heatLayer);
  }

  heatLayer = L.heatLayer(points, {
    radius: 28,
    blur: 22,
    maxZoom: 14,
    max: 1.0,
    gradient: {
      0.0: '#1a0533',  // Very weak — deep purple
      0.15: '#FF2A55', // Dead zone — crimson
      0.3: '#FF6B35',  // Weak — orange
      0.5: '#FFB020',  // Moderate — amber
      0.7: '#00D4AA',  // Good — teal
      0.85: '#00E599', // Strong — emerald
      1.0: '#00F0FF',  // Excellent — cyan
    },
  }).addTo(map);

  // Keep dead zone layer on top
  if (layerDeadZones) layerDeadZones.bringToFront();
  if (layerSos) layerSos.bringToFront();
}

// ─────────────────────────────────────────────────────────────────────────────
// RENDER COVERAGE ZONES & RICH CALLOUT CARDS (Matched to User Reference Image)
// ─────────────────────────────────────────────────────────────────────────────

function renderCoverageZonesAndCallouts() {
  layerCoverageZones.clearLayers();

  coverageZonesData.forEach((zone) => {
    const isStrong = zone.category === 'strong';
    const isModerate = zone.category === 'moderate';
    const isDead = zone.category === 'deadzone';

    const color = isStrong ? '#16A34A' : isModerate ? '#F59E0B' : '#DC2626';
    const fillColor = isStrong ? '#10B981' : isModerate ? '#FBBF24' : '#EF4444';
    const fillOpacity = isStrong ? 0.35 : isModerate ? 0.38 : 0.42;

    // 1. Shaded Coverage Blob / Polygon
    const circle = L.circle([zone.lat, zone.lon], {
      radius: zone.radius,
      fillColor: fillColor,
      fillOpacity: fillOpacity,
      color: color,
      weight: 2,
      dashArray: isDead ? '6, 6' : null,
    });
    circle.addTo(layerCoverageZones);

    // 2. Rich In-Map Callout Card (Matching User Mockup Layout)
    const pinColor = isStrong ? '🟢' : isModerate ? '🟡' : '🔴';
    const cardClass = zone.category;

    let detailsHtml = '';
    if (isStrong) {
      detailsHtml = `
        <div>Coverage: <strong>${zone.coverage_pct}% (${zone.tech})</strong></div>
        <div>Avg Download: <strong>${zone.download_speed}</strong></div>
        ${zone.signal_dbm ? `<div>Signal strength: <strong>${zone.signal_dbm}dBm.</strong></div>` : ''}
        ${zone.congestion ? `<div>Status: <strong>${zone.congestion}</strong></div>` : ''}
      `;
    } else if (isModerate) {
      detailsHtml = `
        <div>Coverage: <strong>${zone.coverage_pct}% (Moderate)</strong></div>
        <div>4G Download: <strong>${zone.download_speed}</strong></div>
        <div>5G signal available.</div>
        ${zone.user_count ? `<div>${zone.user_count}</div>` : ''}
      `;
    } else {
      detailsHtml = `
        <div>Coverage: <strong>${zone.coverage_pct}% (Dead Zone)</strong></div>
        <div>4G Download: <strong>${zone.download_speed}</strong></div>
        <div>Signal Strength: <strong>${zone.signal_dbm} dBm</strong></div>
        <div>Congestion Status: <strong>${zone.congestion}</strong></div>
        <div>Latency (Avg): <strong>${zone.latency_avg}</strong></div>
      `;
    }

    const calloutIcon = L.divIcon({
      html: `
        <div class="callout-box ${cardClass}" onclick="map.setView([${zone.lat}, ${zone.lon}], 14)">
          <div class="callout-title">
            <span>${pinColor}</span>
            <span>${zone.name}</span>
          </div>
          <div style="font-size:10px; line-height:1.35;">
            ${detailsHtml}
          </div>
        </div>
      `,
      className: 'custom-callout-pin-wrapper',
      iconSize: [210, 85],
      iconAnchor: [105, 42],
    });

    L.marker([zone.lat, zone.lon], { icon: calloutIcon, zIndexOffset: isDead ? 1000 : 500 })
      .addTo(layerCoverageZones);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// AI DEAD ZONE MARKERS — Custom Icons + dBm Signal Strength
// ─────────────────────────────────────────────────────────────────────────────

function renderMapDeadZonesLayer() {
  layerDeadZones.clearLayers();
  console.log('[GhostNet] renderMapDeadZonesLayer called, data count:', deadZonesData ? deadZonesData.length : 'null');
  if (!deadZonesData || deadZonesData.length === 0) return;

  deadZonesData.forEach((dz) => {
    const pct = (dz.predicted_score * 100).toFixed(0);
    const dbm = dz.signal_dbm !== undefined ? dz.signal_dbm : -125;
    const netState = dz.network_state || 'NO SIGNAL';
    const rootCause = dz.root_cause || 'Terrain / infrastructure gap';
    const actionPlan = dz.action_plan || 'Deploy solar micro-repeater';
    const conf = dz.confidence !== undefined ? (dz.confidence * 100).toFixed(0) : '—';
    const region = dz.region || 'Unknown';
    const name = dz.name || 'Dead Zone';

    // Color by severity
    let col;
    if (dbm <= -126)      col = '#FF2A55';
    else if (dbm <= -120) col = '#FF6B35';
    else                  col = '#FFB020';

    // 1. LARGE SHADED ZONE — always visible at any zoom
    L.circle([dz.lat, dz.lon], {
      radius: 18000,
      fillColor: col,
      fillOpacity: 0.15,
      color: col,
      weight: 2.5,
      dashArray: '12 8',
    }).addTo(layerDeadZones);

    // 2. SOLID INNER CORE — darker fill
    L.circle([dz.lat, dz.lon], {
      radius: 7000,
      fillColor: col,
      fillOpacity: 0.35,
      color: col,
      weight: 3,
    }).addTo(layerDeadZones);

    // 3. CENTER DOT (circleMarker = pixel-size, always visible even zoomed out)
    const centerDot = L.circleMarker([dz.lat, dz.lon], {
      radius: 8,
      fillColor: col,
      fillOpacity: 1,
      color: '#FFFFFF',
      weight: 3,
    }).addTo(layerDeadZones);

    // 4. PERMANENT TOOLTIP — name + signal dBm (always shown, no hover needed)
    centerDot.bindTooltip(
      `<b>📵 ${name}</b><br/><span style="color:${col};font-weight:900;">${dbm} dBm</span> · ${netState}`,
      {
        permanent: true,
        direction: 'top',
        offset: [0, -12],
        className: 'dz-tooltip',
      }
    );

    // 5. POPUP on click — full detail card
    centerDot.bindPopup(
      `<div style="font-family:sans-serif;padding:8px;min-width:220px;font-size:12px;line-height:1.5;">
        <div style="font-weight:900;font-size:14px;color:${col};margin-bottom:6px;">📵 ${name}</div>
        <table style="width:100%;border-collapse:collapse;font-size:11px;">
          <tr><td style="color:#666;padding:2px 6px 2px 0;">Region</td><td><b>${region}</b></td></tr>
          <tr><td style="color:#666;padding:2px 6px 2px 0;">Signal</td><td><b style="color:${col};">${dbm} dBm</b></td></tr>
          <tr><td style="color:#666;padding:2px 6px 2px 0;">State</td><td><b style="color:${col};">${netState}</b></td></tr>
          <tr><td style="color:#666;padding:2px 6px 2px 0;">AI Risk</td><td><b>${pct}%</b> (Conf: ${conf}%)</td></tr>
          <tr><td style="color:#666;padding:2px 6px 2px 0;vertical-align:top;">Cause</td><td style="font-size:10px;">${rootCause}</td></tr>
          <tr><td style="color:#666;padding:2px 6px 2px 0;vertical-align:top;">Fix</td><td style="color:#059669;font-size:10px;">${actionPlan}</td></tr>
        </table>
      </div>`,
      { maxWidth: 280 }
    );
  });

  layerDeadZones.bringToFront();
}



// ─────────────────────────────────────────────────────────────────────────────
// CELLULAR TRANSMISSION NODES
// ─────────────────────────────────────────────────────────────────────────────

function renderCellularNodesLayer() {
  layerCellularNodes.clearLayers();

  cellularNodesData.forEach((node) => {
    const nodeIcon = L.divIcon({
      html: `
        <div class="node-tower-pill">
          <span>📡</span>
          <span>${node.id}, Load: ${node.load}</span>
        </div>
      `,
      className: 'custom-callout-pin-wrapper',
      iconSize: [160, 24],
      iconAnchor: [80, 12],
    });

    L.marker([node.lat, node.lon], { icon: nodeIcon, zIndexOffset: 200 })
      .addTo(layerCellularNodes);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// REAL-TIME SERVER-SENT EVENTS (SSE)
// ─────────────────────────────────────────────────────────────────────────────

function setupSSE() {
  const eventSource = new EventSource('/api/events');

  eventSource.onopen = () => {
    const statusEl = document.getElementById('streamStatus');
    if (statusEl) {
      statusEl.innerText = 'LIVE STREAM';
      statusEl.style.color = '#00E599';
    }
  };

  eventSource.addEventListener('reading', (e) => {
    const data = JSON.parse(e.data).payload;
    const reading = data.reading || data;
    readingsData.unshift(reading);
    if (readingsData.length > 600) readingsData.pop();
    livePacketCount++;

    // Update total packet count display
    const pktEl = document.getElementById('valLivePackets');
    if (pktEl) pktEl.innerText = `+${livePacketCount} live stream`;

    if (data.mean_signal_dbm !== undefined) {
      updateLiveMeanSignalDisplay(data.mean_signal_dbm);
    }

    // Live-update heatmap: add new point without full re-render
    if (heatLayer && reading.lat && reading.lon) {
      const intensity = Math.max(0, Math.min(1, (reading.signal_dbm + 140) / 90));
      heatLayer.addLatLng([reading.lat, reading.lon, intensity]);
    }
  });

  eventSource.addEventListener('sos', (e) => {
    const newSos = JSON.parse(e.data).payload;
    const idx = sosData.findIndex((a) => a.id === newSos.id);
    if (idx >= 0) sosData[idx] = newSos;
    else sosData.unshift(newSos);

    sosData.sort((a, b) => b.priority_score - a.priority_score);
    renderMapSosLayer();
    renderSosFeed();
    triggerSosShockwave(newSos.lat, newSos.lon, newSos);
  });

  eventSource.addEventListener('backend_log', (e) => {
    const log = JSON.parse(e.data).payload;
    backendLogsData.unshift(log);
    appendLogToTerminal(log);
  });
}

function updateLiveMeanSignalDisplay(meanDbm) {
  const el = document.getElementById('valMeanSignal');
  if (!el) return;
  el.innerHTML = `${meanDbm.toFixed(1)} <span style="font-size:0.85rem; color:var(--text-secondary);">dBm</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// SOS SHOCKWAVE & RESCUE DISPATCH MODAL
// ─────────────────────────────────────────────────────────────────────────────

function triggerSosShockwave(lat, lon, sosObj) {
  if (!map) return;
  map.flyTo([lat, lon], 13, { duration: 1.0 });

  const shockwave = L.circle([lat, lon], {
    radius: 300,
    fillColor: '#FF2A55',
    fillOpacity: 0.6,
    color: '#FF2A55',
    weight: 3,
  }).addTo(map);

  let currentRadius = 300;
  const interval = setInterval(() => {
    currentRadius += 400;
    shockwave.setRadius(currentRadius);
    const opacity = Math.max(0, 0.6 - currentRadius / 4000);
    shockwave.setStyle({ fillOpacity: opacity, opacity: opacity });
    if (currentRadius > 3500) {
      clearInterval(interval);
      map.removeLayer(shockwave);
    }
  }, 60);

  const banner = document.getElementById('inmapRescueAlert');
  const titleEl = document.getElementById('rescueAlertTitle');
  const msgEl = document.getElementById('rescueAlertMsg');
  if (banner && titleEl && msgEl) {
    titleEl.innerText = `🚨 EMERGENCY DISPATCH: ${sosObj.category.toUpperCase()} (${(sosObj.priority_score * 100).toFixed(0)}/100)`;
    msgEl.innerText = `${sosObj.message} — Unit dispatched from ${sosObj.nearest_facility || 'District Response HQ'}. ETA: 7 mins.`;
    banner.style.display = 'flex';
  }
}

async function injectLiveSos(cat, lat, lon, msg) {
  try {
    await fetch('/api/sos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: lat || 22.5850,
        lon: lon || 88.3400,
        category: cat || 'medical',
        message: msg || 'Emergency assistance needed in Howrah Station Corridor.',
      }),
    });
  } catch (e) {
    console.error(e);
  }
}

function renderMapSosLayer() {
  layerSos.clearLayers();
  sosData.forEach((sos) => {
    if (sos.status === 'resolved') return;
    const isUrgent = sos.priority_score >= 0.8;
    const bg = isUrgent ? '#FF2A55' : '#FFB020';
    const icon = L.divIcon({
      html: `<div style="width:34px; height:34px; border-radius:50%; background:${bg}; border:2px solid #fff; box-shadow:0 0 20px ${bg}; display:flex; align-items:center; justify-content:center; color:#fff; font-size:15px;">🚨</div>`,
      className: 'custom-sos-pin',
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });

    L.marker([sos.lat, sos.lon], { icon, zIndexOffset: 3000 })
      .bindPopup(`<div style="padding:6px; font-size:12px; font-family:var(--font-sans);">
        <strong style="color:#FF2A55;">🚨 EMERGENCY ALERT</strong><br/>
        ${sos.message}<br/>
        Priority: ${(sos.priority_score * 100).toFixed(0)}/100
      </div>`)
      .addTo(layerSos);
  });
}

function renderSosFeed() {
  const container = document.getElementById('sosFeedList');
  if (!container) return;
  if (!sosData.length) {
    container.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--text-muted);">No active alerts.</div>';
    return;
  }

  container.innerHTML = sosData
    .map((sos) => {
      const isUrgent = sos.priority_score >= 0.8;
      const pct = Math.min(100, Math.round(sos.priority_score * 100));
      return `
      <div class="clay-btn-surface" style="padding:0.85rem; border-radius:0.85rem; margin-bottom:0.5rem; border:1px solid ${isUrgent ? 'rgba(255,42,85,0.4)' : 'var(--border-subtle)'};">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="sih-tag" style="background:${isUrgent ? 'rgba(255,42,85,0.2)' : 'rgba(255,176,32,0.2)'}; color:${isUrgent ? '#FF2A55' : '#FFB020'};">${sos.category.toUpperCase()}</span>
          <strong style="font-family:var(--font-mono); font-size:0.75rem;">${pct}/100</strong>
        </div>
        <div style="font-size:0.8rem; font-weight:700; margin:0.4rem 0; color:var(--text-primary);">${sos.message}</div>
        <div style="font-size:0.68rem; color:var(--text-secondary); display:flex; justify-content:space-between;">
          <span>Lat: ${sos.lat.toFixed(4)}, Lon: ${sos.lon.toFixed(4)}</span>
          ${sos.nearest_facility ? `<span style="color:var(--accent-emerald);">🏥 ${sos.nearest_facility}</span>` : ''}
        </div>
      </div>
    `;
    })
    .join('');
}

function renderHelpPointsList() {
  const container = document.getElementById('helpPointsList');
  if (!container) return;
  container.innerHTML = helpPointsData
    .map(
      (hp) => `
    <div class="clay-btn-surface" style="padding:8px 10px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <div style="font-size:0.75rem; font-weight:700; color:var(--text-primary);">${hp.name}</div>
        <div style="font-size:0.65rem; color:var(--text-secondary); text-transform:uppercase;">${hp.type.replace('_', ' ')} · ${hp.district || 'West Bengal'}</div>
      </div>
      <span style="font-family:var(--font-mono); font-size:0.72rem; color:var(--accent-emerald); font-weight:800;">${hp.distance_km} km</span>
    </div>
  `
    )
    .join('');
}

function renderTowerTable() {
  const container = document.getElementById('towerTableBody');
  if (!container) return;
  container.innerHTML = towerData
    .map(
      (t) => `
    <tr>
      <td style="font-weight:700; color:var(--text-primary);">${t.name} <br/><small style="color:var(--text-secondary); font-size:0.65rem;">${t.region || 'West Bengal'}</small></td>
      <td style="color:var(--text-secondary); font-size:0.7rem;">${t.justification}</td>
      <td style="font-family:var(--font-mono); color:var(--accent-emerald); font-weight:800;">~${t.estimated_residents_covered.toLocaleString()}</td>
      <td><span class="sih-tag" style="background:${t.priority === 'CRITICAL' ? 'rgba(255,42,85,0.2)' : 'rgba(0,240,255,0.15)'}; color:${t.priority === 'CRITICAL' ? 'var(--accent-rose)' : 'var(--accent-cyan)'}; border-color:${t.priority === 'CRITICAL' ? 'var(--accent-rose)' : 'var(--accent-cyan)'};">${t.priority}</span></td>
    </tr>
  `).join('');
}

function renderTerminalLogs() {
  const feed = document.getElementById('terminalFeed');
  if (!feed) return;
  if (!backendLogsData || backendLogsData.length === 0) {
    const nowTime = new Date().toLocaleTimeString();
    backendLogsData = [
      { timestamp: nowTime, module: "KERNEL", action: "INITIALIZE", details: "GhostNet AI Network Coverage & Spatial Engine active", level: "INFO" },
      { timestamp: nowTime, module: "COVERAGE", action: "LOAD_ZONES", details: "Loaded 12 coverage polygons & cellular nodes for Kolkata Metro & West Bengal", level: "INFO" }
    ];
  }
  feed.innerHTML = backendLogsData.map((l) => formatLogRow(l)).join('');
}

setInterval(async () => {
  try {
    const logs = await fetch('/api/backend-logs').then(r => r.json());
    if (logs && logs.length > 0) {
      backendLogsData = logs;
      renderTerminalLogs();
    }
  } catch (e) {}
}, 2500);

function appendLogToTerminal(log) {
  const feed = document.getElementById('terminalFeed');
  if (!feed) return;
  const rowHtml = formatLogRow(log);
  feed.insertAdjacentHTML('afterbegin', rowHtml);
}

function formatLogRow(l) {
  const isWarn = l.level === 'WARNING' || l.module === 'EMERGENCY_DISPATCH';
  return `
    <div class="log-row ${isWarn ? 'warning' : ''}">
      <span class="log-time">[${l.timestamp}]</span>
      <span class="log-mod">[${l.module}]</span>
      <span class="log-action">${l.action}:</span>
      <span class="log-msg">${l.details}</span>
    </div>
  `;
}

async function triggerRecompute() {
  showToast('🤖 AI Analysis Triggered: Computing 5G carrier aggregation & traffic load...');
  try {
    await fetch('/api/recompute', { method: 'POST' });
  } catch (e) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// MOBILE SIMULATOR
// ─────────────────────────────────────────────────────────────────────────────

function toggleAirplaneMode() {
  isAirplaneMode = !isAirplaneMode;
  const btn = document.getElementById('btnAirplane');
  const banner = document.getElementById('mobBanner');
  const badge = document.getElementById('mobSignalBadge');

  if (isAirplaneMode) {
    btn.innerText = DICT[mobileLanguage].airplaneOn;
    btn.style.color = 'var(--accent-amber)';
    banner.innerText = DICT[mobileLanguage].offlineBanner;
    banner.style.background = 'rgba(255, 42, 85, 0.15)';
    badge.innerText = 'NO SIGNAL (✈️)';
    badge.style.color = 'var(--accent-rose)';
    showToast('📱 Airplane Mode: Drift SQLite activated.');
  } else {
    btn.innerText = DICT[mobileLanguage].airplaneOff;
    btn.style.color = 'var(--text-primary)';
    banner.innerText = DICT[mobileLanguage].onlineBanner;
    banner.style.background = 'var(--bg-app)';
    badge.innerText = '-78 dBm (4G)';
    badge.style.color = 'var(--accent-emerald)';
  }
}

function toggleMobileLanguage() {
  mobileLanguage = mobileLanguage === 'en' ? 'hi' : 'en';
  const btn = document.getElementById('btnLang');
  btn.innerText = mobileLanguage === 'en' ? '🌐 हिन्दी' : '🌐 English';

  const d = DICT[mobileLanguage];
  document.getElementById('mobAppTitle').innerText = d.appTitle;
  document.getElementById('mobHoldTap').innerText = d.holdTap;
  document.getElementById('mobSosText').innerText = d.sos;
  document.getElementById('btnMobSafe').innerText = d.safeBtn;
  document.getElementById('lblCatMedical').innerText = d.catMedical;
  document.getElementById('lblCatDisaster').innerText = d.catDisaster;
  document.getElementById('lblCatSecurity').innerText = d.catSecurity;
  document.getElementById('lblCatGeneral').innerText = d.catGeneral;
}

function setMobileCategory(cat) {
  selectedMobileCategory = cat;
  ['Medical', 'Disaster', 'Security', 'General'].forEach((c) => {
    const el = document.getElementById(`catBtn${c}`);
    if (el) el.style.borderColor = c.toLowerCase() === cat ? 'var(--accent-cyan)' : 'var(--border-subtle)';
  });
}

async function triggerMobileSos() {
  const d = DICT[mobileLanguage];
  const payload = {
    lat: 22.5850,
    lon: 88.3400,
    category: selectedMobileCategory,
    message: `Kolkata Emergency SOS (${selectedMobileCategory.toUpperCase()}): Howrah corridor assistance requested.`,
  };

  if (isAirplaneMode) {
    localOfflineQueue.push(payload);
    showToast(d.offlineQueuedToast);
  } else {
    await injectLiveSos(selectedMobileCategory, 22.5850, 88.3400, payload.message);
    showToast(d.onlineDispatchedToast);
  }
}

async function triggerMobileCheckIn() {
  const d = DICT[mobileLanguage];
  showToast(d.safeToast);
}

function showToast(msg) {
  const existing = document.querySelector('.clay-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'clay-toast';
  toast.innerText = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
