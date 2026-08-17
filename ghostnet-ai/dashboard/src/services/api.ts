import {
  CoveragePoint,
  HeatmapCell,
  HelpPoint,
  SosAlert,
  SosStatus,
  DeadZone,
  TowerRecommendation,
} from '../types';

const API_BASE = '/api/v1';

export async function fetchCoverage(bbox?: string): Promise<CoveragePoint[]> {
  const url = bbox ? `${API_BASE}/coverage?bbox=${encodeURIComponent(bbox)}` : `${API_BASE}/coverage`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch coverage: ${res.statusText}`);
  return res.json();
}

export async function fetchHeatmap(bbox?: string, precision = 6): Promise<HeatmapCell[]> {
  const url = bbox
    ? `${API_BASE}/coverage/heatmap?bbox=${encodeURIComponent(bbox)}&precision=${precision}`
    : `${API_BASE}/coverage/heatmap?precision=${precision}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch heatmap: ${res.statusText}`);
  return res.json();
}

export async function fetchHelpPoints(lat = 23.3322, lon = 86.3652, radiusKm = 50): Promise<HelpPoint[]> {
  const url = `${API_BASE}/help-points?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch help points: ${res.statusText}`);
  return res.json();
}

export async function fetchSosAlerts(statusFilter?: string): Promise<SosAlert[]> {
  const url = statusFilter ? `${API_BASE}/sos?status=${statusFilter}` : `${API_BASE}/sos`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch SOS alerts: ${res.statusText}`);
  return res.json();
}

export async function updateSosStatus(alertId: string, status: SosStatus): Promise<SosAlert> {
  const res = await fetch(`${API_BASE}/sos/${alertId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error(`Failed to update SOS status: ${res.statusText}`);
  return res.json();
}

export async function fetchDeadZones(minScore = 0.4): Promise<DeadZone[]> {
  const url = `${API_BASE}/predictions/dead-zones?min_score=${minScore}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch dead zones: ${res.statusText}`);
  return res.json();
}

export async function fetchTowerRecommendations(): Promise<TowerRecommendation[]> {
  const url = `${API_BASE}/predictions/tower-recommendations`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch tower recommendations: ${res.statusText}`);
  return res.json();
}

export async function triggerRecomputePredictions(): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/predictions/recompute`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to trigger prediction recompute: ${res.statusText}`);
  return res.json();
}

export async function submitSimulatedReading(reading: {
  device_id: string;
  lat: number;
  lon: number;
  network_type: string;
  signal_dbm: number;
  download_mbps: number;
  upload_mbps: number;
  latency_ms: number;
  recorded_at: string;
}) {
  const res = await fetch(`${API_BASE}/readings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ readings: [reading] }),
  });
  if (!res.ok) throw new Error(`Failed to submit reading: ${res.statusText}`);
  return res.json();
}

export async function submitSimulatedSos(alert: {
  device_id: string;
  lat: number;
  lon: number;
  category: string;
  message: string;
}): Promise<SosAlert> {
  const res = await fetch(`${API_BASE}/sos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(alert),
  });
  if (!res.ok) throw new Error(`Failed to submit SOS alert: ${res.statusText}`);
  return res.json();
}
