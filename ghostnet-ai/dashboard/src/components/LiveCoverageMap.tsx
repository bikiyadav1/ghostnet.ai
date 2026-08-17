import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import {
  CoveragePoint,
  HeatmapCell,
  HelpPoint,
  WsMessagePayload,
  SosAlert,
  DeadZone,
  TowerRecommendation,
} from '../types';
import {
  Layers,
  Shield,
  Hospital,
  Home,
  Flag,
  Signal,
  Radio,
  AlertCircle,
  Activity,
  Flame,
  TowerControl as TowerIcon,
  Sparkles,
} from 'lucide-react';

const createCustomIcon = (iconHtml: string, bgClass: string) => {
  return L.divIcon({
    html: `<div class="w-8 h-8 rounded-full flex items-center justify-center ${bgClass} border-2 border-white/80 shadow-lg text-white">${iconHtml}</div>`,
    className: 'custom-leaflet-icon',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
};

const createSosIcon = (category: string, score: number) => {
  const bg = score >= 0.8 ? 'bg-rose-600 animate-pulse' : score >= 0.6 ? 'bg-amber-600' : 'bg-blue-600';
  return L.divIcon({
    html: `<div class="relative flex items-center justify-center w-9 h-9 rounded-full ${bg} border-2 border-white shadow-glow-rose text-white">
      <svg class="w-5 h-5 animate-bounce" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
    </div>`,
    className: 'custom-sos-icon',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
};

const createTowerRecIcon = () => {
  return L.divIcon({
    html: `<div class="relative flex items-center justify-center w-9 h-9 rounded-full bg-gradient-to-tr from-cyan-600 to-indigo-600 border-2 border-white shadow-glow-cyan text-white animate-pulse">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 2v20m-7-5l7-7 7 7M5 8l7 7 7-7"/></svg>
    </div>`,
    className: 'custom-tower-icon',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
};

const hospitalIcon = createCustomIcon(
  '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>',
  'bg-rose-600'
);

const policeIcon = createCustomIcon(
  '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  'bg-blue-600'
);

const shelterIcon = createCustomIcon(
  '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>',
  'bg-amber-600'
);

const safeZoneIcon = createCustomIcon(
  '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7"/></svg>',
  'bg-emerald-600'
);

interface LiveCoverageMapProps {
  coveragePoints: CoveragePoint[];
  heatmapCells: HeatmapCell[];
  helpPoints: HelpPoint[];
  sosAlerts?: SosAlert[];
  deadZones?: DeadZone[];
  towerRecommendations?: TowerRecommendation[];
  latestReading: WsMessagePayload | null;
}

export const LiveCoverageMap: React.FC<LiveCoverageMapProps> = ({
  coveragePoints,
  heatmapCells,
  helpPoints,
  sosAlerts = [],
  deadZones = [],
  towerRecommendations = [],
  latestReading,
}) => {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showHelpPoints, setShowHelpPoints] = useState(true);
  const [showRawPoints, setShowRawPoints] = useState(false);
  const [showSosAlerts, setShowSosAlerts] = useState(true);
  const [showDeadZones, setShowDeadZones] = useState(true);
  const [showTowers, setShowTowers] = useState(true);

  const getSignalColor = (dbm: number) => {
    if (dbm >= -80) return '#10B981';
    if (dbm >= -100) return '#F59E0B';
    return '#F43F5E';
  };

  const getHelpPointIcon = (type: string) => {
    switch (type) {
      case 'hospital':
        return hospitalIcon;
      case 'police':
        return policeIcon;
      case 'shelter':
        return shelterIcon;
      case 'safe_zone':
      default:
        return safeZoneIcon;
    }
  };

  return (
    <div className="relative w-full h-[580px] rounded-2xl overflow-hidden glass-panel border border-white/10 shadow-2xl">
      
      {/* Map Control Bar Overlay */}
      <div className="absolute top-4 right-4 z-[400] flex items-center gap-1.5 bg-dark-900/95 backdrop-blur-md px-3 py-2 rounded-xl border border-white/10 shadow-xl flex-wrap">
        <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 mr-2">
          <Layers className="w-3.5 h-3.5 text-ghost-cyan" /> Layers:
        </span>
        
        <button
          onClick={() => setShowDeadZones(!showDeadZones)}
          className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
            showDeadZones ? 'bg-red-500/25 text-red-300 border border-red-500/60 shadow-glow-rose' : 'text-slate-400 hover:text-white'
          }`}
        >
          AI Dead Zones ({deadZones.length})
        </button>

        <button
          onClick={() => setShowTowers(!showTowers)}
          className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
            showTowers ? 'bg-indigo-500/25 text-indigo-300 border border-indigo-500/60 shadow-glow-cyan' : 'text-slate-400 hover:text-white'
          }`}
        >
          Recommended Towers ({towerRecommendations.length})
        </button>

        <button
          onClick={() => setShowSosAlerts(!showSosAlerts)}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
            showSosAlerts ? 'bg-rose-500/20 text-rose-300 border border-rose-500/50' : 'text-slate-400 hover:text-white'
          }`}
        >
          SOS ({sosAlerts.filter(a => a.status !== 'resolved').length})
        </button>

        <button
          onClick={() => setShowHeatmap(!showHeatmap)}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
            showHeatmap ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50' : 'text-slate-400 hover:text-white'
          }`}
        >
          Signal Heatmap
        </button>

        <button
          onClick={() => setShowHelpPoints(!showHelpPoints)}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
            showHelpPoints ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50' : 'text-slate-400 hover:text-white'
          }`}
        >
          Help Points
        </button>
      </div>

      {/* Map Legend */}
      <div className="absolute bottom-4 left-4 z-[400] bg-dark-900/90 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-white/10 shadow-xl text-xs">
        <p className="font-semibold text-slate-200 mb-1.5 flex items-center gap-1">
          <Signal className="w-3.5 h-3.5 text-ghost-cyan" /> Map Layers Legend
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-600 shadow-glow-rose" />
            <span className="text-slate-300">Predicted Dead Zones</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-indigo-500 shadow-glow-cyan" />
            <span className="text-slate-300">Tower Recommendations</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-slate-300">&gt; -80 dBm (Strong)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-slate-300">-80 to -100 dBm</span>
          </div>
        </div>
      </div>

      {/* Map Container */}
      <MapContainer
        center={[23.3322, 86.3652]}
        zoom={10}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          maxZoom={19}
        />

        {/* Heatmap Grid Cells */}
        {showHeatmap &&
          heatmapCells.map((cell) => {
            const color = getSignalColor(cell.avg_signal_dbm);
            return (
              <CircleMarker
                key={cell.geohash}
                center={[cell.lat, cell.lon]}
                radius={16}
                pathOptions={{
                  fillColor: color,
                  fillOpacity: 0.3,
                  color: color,
                  weight: 1,
                  opacity: 0.5,
                }}
              >
                <Popup>
                  <div className="p-1 text-xs">
                    <p className="font-bold text-white mb-0.5">Geohash: {cell.geohash}</p>
                    <p className="text-slate-300">Avg Signal: <span className="font-mono font-semibold text-ghost-cyan">{cell.avg_signal_dbm} dBm</span></p>
                    <p className="text-slate-400">Samples: {cell.sample_count}</p>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* ML Predicted Dead-Zone Polygons / Markers */}
        {showDeadZones &&
          deadZones.map((dz) => {
            const riskPercent = (dz.predicted_score * 100).toFixed(0);
            return (
              <CircleMarker
                key={`dz-${dz.geohash}`}
                center={[dz.lat, dz.lon]}
                radius={22}
                pathOptions={{
                  fillColor: '#EF4444',
                  fillOpacity: Math.min(0.55, dz.predicted_score * 0.55),
                  color: '#DC2626',
                  weight: 1.5,
                  dashArray: '3, 4',
                }}
              >
                <Popup>
                  <div className="p-1.5 text-xs max-w-xs">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800">
                      AI Dead-Zone Prediction
                    </span>
                    <h4 className="font-bold text-white mt-1">Geohash: {dz.geohash}</h4>
                    <p className="text-red-400 font-mono font-bold mt-1 text-sm">
                      Blackout Risk: {riskPercent}%
                    </p>
                    <p className="text-slate-400 text-[11px] mt-1">
                      Model Confidence: {(dz.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* Recommended Tower Sites */}
        {showTowers &&
          towerRecommendations.map((tower, idx) => (
            <Marker
              key={`tower-${idx}`}
              position={[tower.lat, tower.lon]}
              icon={createTowerRecIcon()}
            >
              <Popup>
                <div className="p-2 text-xs max-w-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                      Recommended Tower Site
                    </span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      {tower.priority} PRIORITY
                    </span>
                  </div>
                  <h4 className="font-bold text-white mt-1.5 text-sm">{tower.name}</h4>
                  <p className="text-slate-200 mt-1 text-xs">{tower.justification}</p>
                  <div className="mt-2 p-1.5 rounded-lg bg-dark-900 border border-white/10 flex items-center justify-between font-mono text-[11px]">
                    <span className="text-slate-400">Residents Covered:</span>
                    <span className="text-emerald-400 font-bold">~{tower.estimated_residents_covered.toLocaleString()}</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Live SOS Alerts Pins */}
        {showSosAlerts &&
          sosAlerts.map((sos) => (
            <Marker
              key={sos.id}
              position={[sos.lat, sos.lon]}
              icon={createSosIcon(sos.category, sos.priority_score)}
            >
              <Popup>
                <div className="p-1.5 text-xs max-w-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                      {sos.category} EMERGENCY
                    </span>
                    <span className="font-mono font-bold text-rose-400">
                      Priority: {(sos.priority_score * 100).toFixed(0)}/100
                    </span>
                  </div>
                  <h4 className="font-bold text-white mt-1.5 text-sm">{sos.message || 'Emergency SOS broadcast'}</h4>
                  {sos.corroboration_count > 0 && (
                    <p className="text-amber-400 font-semibold text-[11px] mt-1 flex items-center gap-1">
                      <Flame className="w-3 h-3" /> +{sos.corroboration_count} Nearby Corroborations
                    </p>
                  )}
                  <p className="text-slate-400 text-[10px] mt-1 font-mono">
                    Time: {new Date(sos.created_at).toLocaleTimeString()}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Live Incoming Reading Marker */}
        {latestReading && (
          <CircleMarker
            center={[latestReading.lat || 23.3322, latestReading.lon || 86.3652]}
            radius={14}
            pathOptions={{
              fillColor: '#00F0FF',
              fillOpacity: 0.7,
              color: '#ffffff',
              weight: 2,
            }}
          />
        )}

        {/* Help Points Markers */}
        {showHelpPoints &&
          helpPoints.map((hp) => (
            <Marker
              key={hp.id}
              position={[hp.lat, hp.lon]}
              icon={getHelpPointIcon(hp.type)}
            >
              <Popup>
                <div className="p-1.5 text-xs">
                  <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-cyan-800/40">
                    {hp.type.replace('_', ' ')}
                  </span>
                  <h4 className="font-bold text-white mt-1 text-sm">{hp.name}</h4>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Lat: {hp.lat.toFixed(4)}, Lon: {hp.lon.toFixed(4)}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}
      </MapContainer>

    </div>
  );
};
