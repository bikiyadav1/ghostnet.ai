import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { LiveTelemetryStats } from './components/LiveTelemetryStats';
import { LiveCoverageMap } from './components/LiveCoverageMap';
import { HelpPointsList } from './components/HelpPointsList';
import { SosResponderFeed } from './components/SosResponderFeed';
import {
  fetchCoverage,
  fetchHeatmap,
  fetchHelpPoints,
  fetchSosAlerts,
  fetchDeadZones,
  fetchTowerRecommendations,
} from './services/api';
import { wsClient } from './services/websocket';
import {
  CoveragePoint,
  HeatmapCell,
  HelpPoint,
  WsMessagePayload,
  SosAlert,
  DeadZone,
  TowerRecommendation,
} from './types';
import { RefreshCw, Radio, AlertCircle, ShieldAlert, Cpu, Sparkles } from 'lucide-react';

export const App: React.FC = () => {
  const [coveragePoints, setCoveragePoints] = useState<CoveragePoint[]>([]);
  const [heatmapCells, setHeatmapCells] = useState<HeatmapCell[]>([]);
  const [helpPoints, setHelpPoints] = useState<HelpPoint[]>([]);
  const [sosAlerts, setSosAlerts] = useState<SosAlert[]>([]);
  const [deadZones, setDeadZones] = useState<DeadZone[]>([]);
  const [towerRecommendations, setTowerRecommendations] = useState<TowerRecommendation[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(true);
  const [latestReading, setLatestReading] = useState<WsMessagePayload | null>(null);
  const [recentTelemetry, setRecentTelemetry] = useState<WsMessagePayload[]>([]);
  const [liveReadingsCount, setLiveReadingsCount] = useState<number>(0);
  const [mlNotification, setMlNotification] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load all initial district data
  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [coverage, heatmap, hp, sos, dz, towers] = await Promise.all([
        fetchCoverage(),
        fetchHeatmap(),
        fetchHelpPoints(23.3322, 86.3652, 60),
        fetchSosAlerts(),
        fetchDeadZones(0.4),
        fetchTowerRecommendations(),
      ]);
      setCoveragePoints(coverage);
      setHeatmapCells(heatmap);
      setHelpPoints(hp);
      setSosAlerts(sos);
      setDeadZones(dz);
      setTowerRecommendations(towers);
    } catch (err: any) {
      console.error('Error loading initial data:', err);
      setError('Unable to reach backend API. If running locally, verify docker-compose is active.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();

    // Start WebSocket
    wsClient.connect();
    const unsubscribe = wsClient.subscribe((msg) => {
      if (msg.type === 'reading') {
        const payload = msg.payload as WsMessagePayload;
        setLatestReading(payload);
        setLiveReadingsCount((prev) => prev + 1);
        setRecentTelemetry((prev) => [payload, ...prev.slice(0, 19)]);
        setCoveragePoints((prev) => [
          {
            lat: payload.lat || 23.3322,
            lon: payload.lon || 86.3652,
            signal_dbm: payload.signal_dbm || -80,
            network_type: payload.network_type || '4G',
            recorded_at: payload.recorded_at || new Date().toISOString(),
          },
          ...prev,
        ]);
      } else if (msg.type === 'sos') {
        const payload = msg.payload as any;
        setSosAlerts((prev) => {
          const filtered = prev.filter((a) => a.id !== payload.id);
          const newAlert: SosAlert = {
            id: payload.id,
            device_id: payload.device_id,
            lat: payload.lat,
            lon: payload.lon,
            category: payload.category,
            message: payload.message,
            priority_score: payload.priority_score,
            status: payload.status,
            created_at: payload.created_at,
            sent_at: payload.created_at,
            corroboration_count: payload.corroboration_count || 0,
            is_relayed: payload.is_relayed || false,
            breakdown: payload.breakdown,
          };
          const updatedList = [newAlert, ...filtered];
          return updatedList.sort((a, b) => b.priority_score - a.priority_score);
        });
      } else if (msg.type === 'sos_update') {
        const payload = msg.payload;
        setSosAlerts((prev) =>
          prev.map((a) => (a.id === payload.id ? { ...a, status: payload.status } : a))
        );
      } else if (msg.type === 'prediction_update') {
        // Real-time ML update broadcasted from Celery/async worker
        const payload = msg.payload;
        setMlNotification(
          `AI Dead-Zone Model Recomputed: Scored ${payload.dead_zones_count || 'grid'} cells and updated top 5 tower candidate sites!`
        );
        if (payload.tower_recommendations) {
          setTowerRecommendations(payload.tower_recommendations);
        }
        // Refresh dead zones from backend
        fetchDeadZones(0.4).then(setDeadZones).catch(console.error);

        setTimeout(() => setMlNotification(null), 6000);
      }
    });

    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
  }, [loadData]);

  const activeSosCount = sosAlerts.filter((a) => a.status !== 'resolved').length;

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col font-sans text-slate-100 selection:bg-cyan-500 selection:text-dark-900">
      
      {/* Header Bar */}
      <Navbar
        wsConnected={wsConnected}
        totalReadings={coveragePoints.length}
        activeSosCount={activeSosCount}
        onRefresh={loadData}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* ML Notification Toast */}
        {mlNotification && (
          <div className="p-3.5 rounded-xl bg-gradient-to-r from-indigo-950 to-cyan-950 border border-cyan-500/50 text-cyan-200 text-xs flex items-center justify-between gap-3 shadow-glow-cyan animate-pulse">
            <div className="flex items-center gap-2.5">
              <Cpu className="w-4 h-4 text-ghost-cyan shrink-0" />
              <span className="font-semibold">{mlNotification}</span>
            </div>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-900 text-cyan-300">
              Live AI Diff Applied
            </span>
          </div>
        )}

        {/* Error Alert if any */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-200 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>{error}</span>
            <button
              onClick={loadData}
              className="ml-auto px-3 py-1 rounded bg-rose-800 hover:bg-rose-700 text-white font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {/* Telemetry Metrics Header */}
        <LiveTelemetryStats
          coveragePoints={coveragePoints}
          heatmapCells={heatmapCells}
          liveReadingsCount={liveReadingsCount}
          recentTelemetry={recentTelemetry}
        />

        {/* Layout Grid: Coverage Map & Overlays (Left) + SOS Responder Feed (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Map Column (7 spans) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <Radio className="w-5 h-5 text-ghost-cyan" />
                  Spatial Signal Map & AI Predictions
                </h2>
                <p className="text-xs text-slate-400">
                  Heatmap, AI dead-zone blackout predictions, and demographic tower recommendations
                </p>
              </div>
              
              <button
                onClick={loadData}
                disabled={isLoading}
                className="p-2 rounded-xl bg-dark-800 hover:bg-dark-700 border border-white/10 text-slate-300 hover:text-white transition-colors"
                title="Refresh Map Data"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-ghost-cyan' : ''}`} />
              </button>
            </div>

            {/* Map Component */}
            <LiveCoverageMap
              coveragePoints={coveragePoints}
              heatmapCells={heatmapCells}
              helpPoints={helpPoints}
              sosAlerts={sosAlerts}
              deadZones={deadZones}
              towerRecommendations={towerRecommendations}
              latestReading={latestReading}
            />

            {/* Help Points Accordion / Drawer */}
            <HelpPointsList helpPoints={helpPoints} />
          </div>

          {/* Responder Feed Column (5 spans) */}
          <div className="lg:col-span-5 h-full">
            <SosResponderFeed
              alerts={sosAlerts}
              onRefresh={loadData}
            />
          </div>

        </div>

      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 px-6 text-center text-xs text-slate-500">
        <p>
          GhostNet AI &copy; 2026 · Smart India Hackathon Prototype · Offline-First Emergency & AI Connectivity Intelligence
        </p>
      </footer>

    </div>
  );
};
