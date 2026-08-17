export type NetworkType = '2G' | '3G' | '4G' | '5G' | 'none';

export interface CoveragePoint {
  lat: number;
  lon: number;
  signal_dbm: number;
  network_type: NetworkType;
  recorded_at: string;
}

export interface HeatmapCell {
  geohash: string;
  avg_signal_dbm: number;
  sample_count: number;
  lat: number;
  lon: number;
}

export type HelpPointType = 'hospital' | 'police' | 'shelter' | 'safe_zone';

export interface HelpPoint {
  id: string;
  name: string;
  type: HelpPointType;
  lat: number;
  lon: number;
  distance_km?: number;
}

export type SosCategory = 'medical' | 'disaster' | 'security' | 'general';
export type SosStatus = 'queued' | 'sent' | 'acknowledged' | 'resolved';

export interface ScoreBreakdown {
  category_term: number;
  recency_term: number;
  corroboration_term: number;
  location_risk_term: number;
  raw_score: number;
  minutes_elapsed: number;
}

export interface SosAlert {
  id: string;
  device_id: string;
  lat: number;
  lon: number;
  category: SosCategory;
  message?: string;
  priority_score: number;
  status: SosStatus;
  created_at: string;
  sent_at: string;
  corroboration_count: number;
  is_relayed: boolean;
  breakdown?: ScoreBreakdown;
}

export interface DeadZone {
  geohash: string;
  predicted_score: number;
  confidence: number;
  lat: number;
  lon: number;
  predicted_at?: string;
}

export interface TowerRecommendation {
  name: string;
  lat: number;
  lon: number;
  justification: string;
  estimated_residents_covered: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface WsMessagePayload {
  id?: string;
  device_id?: string;
  lat?: number;
  lon?: number;
  signal_dbm?: number;
  network_type?: NetworkType;
  category?: SosCategory;
  message?: string;
  priority_score?: number;
  status?: string;
  created_at?: string;
  corroboration_count?: number;
  is_relayed?: boolean;
  breakdown?: ScoreBreakdown;
  task_id?: string;
  dead_zones_count?: number;
  tower_recommendations?: TowerRecommendation[];
}

export interface WsMessage {
  type: 'reading' | 'sos' | 'sos_update' | 'check_in' | 'prediction_update';
  payload: WsMessagePayload | any;
}
