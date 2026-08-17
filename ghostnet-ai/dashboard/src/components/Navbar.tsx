import React, { useState, useEffect } from 'react';
import {
  Radio,
  Activity,
  ShieldAlert,
  Sparkles,
  MapPin,
  AlertCircle,
  Flame,
  Cpu,
  RefreshCw,
} from 'lucide-react';
import {
  submitSimulatedReading,
  submitSimulatedSos,
  triggerRecomputePredictions,
} from '../services/api';

interface NavbarProps {
  wsConnected: boolean;
  totalReadings: number;
  activeSosCount: number;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  wsConnected,
  totalReadings,
  activeSosCount,
  onRefresh,
}) => {
  const [isSimulatingReading, setIsSimulatingReading] = useState(false);
  const [isSimulatingSos, setIsSimulatingSos] = useState(false);
  const [isSimulatingCorrob, setIsSimulatingCorrob] = useState(false);
  const [isRecomputingMl, setIsRecomputingMl] = useState(false);
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleTriggerSimulatedReading = async () => {
    setIsSimulatingReading(true);
    try {
      const randomLat = 23.3322 + (Math.random() - 0.5) * 0.15;
      const randomLon = 86.3652 + (Math.random() - 0.5) * 0.15;
      const signalDbm = Math.floor(-115 + Math.random() * 65);
      const network = signalDbm > -85 ? '5G' : signalDbm > -100 ? '4G' : signalDbm > -115 ? '3G' : '2G';

      await submitSimulatedReading({
        device_id: '11111111-2222-3333-4444-555555555555',
        lat: Number(randomLat.toFixed(5)),
        lon: Number(randomLon.toFixed(5)),
        network_type: network,
        signal_dbm: signalDbm,
        download_mbps: network === '5G' ? 45.2 : 12.4,
        upload_mbps: network === '5G' ? 18.1 : 4.2,
        latency_ms: network === '5G' ? 22 : 68,
        recorded_at: new Date().toISOString(),
      });
      onRefresh();
    } catch (err) {
      console.error('Error injecting simulation reading:', err);
    } finally {
      setTimeout(() => setIsSimulatingReading(false), 500);
    }
  };

  const handleTriggerMedicalSos = async () => {
    setIsSimulatingSos(true);
    try {
      await submitSimulatedSos({
        device_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        lat: 23.1950,
        lon: 86.0470,
        category: 'medical',
        message: 'CRITICAL: Severe asthma attack in remote hilly hamlet. Immediate medical evacuation needed.',
      });
      onRefresh();
    } catch (err) {
      console.error('Error triggering simulated SOS:', err);
    } finally {
      setTimeout(() => setIsSimulatingSos(false), 600);
    }
  };

  const handleTriggerCorroboratingSos = async () => {
    setIsSimulatingCorrob(true);
    try {
      await submitSimulatedSos({
        device_id: 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
        lat: 23.1962,
        lon: 86.0482,
        category: 'disaster',
        message: 'CORROBORATING ALERT: Landslide blocked path to the medical patient above. Urgent team required.',
      });
      onRefresh();
    } catch (err) {
      console.error('Error triggering corroborating SOS:', err);
    } finally {
      setTimeout(() => setIsSimulatingCorrob(false), 600);
    }
  };

  const handleRecomputePredictions = async () => {
    setIsRecomputingMl(true);
    try {
      await triggerRecomputePredictions();
      // Keep spinner active while background worker recomputes
      setTimeout(() => {
        setIsRecomputingMl(false);
        onRefresh();
      }, 1800);
    } catch (err) {
      console.error('Failed to trigger prediction recompute:', err);
      setIsRecomputingMl(false);
    }
  };

  return (
    <header className="glass-panel sticky top-0 z-50 border-b border-white/10 px-6 py-3">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-4">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 shadow-glow-cyan">
            <Radio className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white font-sans flex items-center gap-1.5">
                GhostNet <span className="text-ghost-cyan">AI</span>
              </h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/60 uppercase tracking-wider">
                SIH 2026
              </span>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <MapPin className="w-3 h-3 text-ghost-cyan" />
              Demo District: <span className="text-slate-200 font-medium">Purulia, West Bengal</span>
            </p>
          </div>
        </div>

        {/* Live Status Indicators & Demo Controls */}
        <div className="flex items-center gap-2.5 flex-wrap justify-center lg:justify-end">
          
          {/* Active SOS Count Pill */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-xs text-rose-300">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
            <span className="font-bold">{activeSosCount}</span> Active SOS
          </div>

          {/* WebSocket Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-dark-800 border border-white/5 text-xs">
            <span className={`w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-glow-emerald animate-ping' : 'bg-rose-500'}`} />
            <span className="text-slate-300 font-mono">
              {wsConnected ? 'LIVE FEED ACTIVE' : 'RECONNECTING'}
            </span>
          </div>

          {/* Judge Demo Simulator Actions */}
          <div className="flex items-center gap-1.5 bg-dark-900/90 p-1 rounded-xl border border-white/10 flex-wrap">
            
            {/* Recompute ML Predictions Button */}
            <button
              onClick={handleRecomputePredictions}
              disabled={isRecomputingMl}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold shadow-glow-cyan transition-all transform active:scale-95 disabled:opacity-50"
              title="Trigger XGBoost dead-zone regressor and demographic tower clustering live on stage"
            >
              <Cpu className={`w-3.5 h-3.5 ${isRecomputingMl ? 'animate-spin' : ''}`} />
              <span>{isRecomputingMl ? 'Recomputing AI...' : 'Recompute Predictions'}</span>
            </button>

            <button
              onClick={handleTriggerMedicalSos}
              disabled={isSimulatingSos}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-600/30 hover:bg-rose-600 text-rose-200 hover:text-white text-xs font-semibold border border-rose-500/40 shadow-glow-rose transition-all disabled:opacity-50"
              title="Trigger high-priority Medical SOS"
            >
              <AlertCircle className="w-3 h-3" />
              <span>+Medical SOS</span>
            </button>

            <button
              onClick={handleTriggerCorroboratingSos}
              disabled={isSimulatingCorrob}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-600/30 hover:bg-amber-600 text-amber-200 hover:text-white text-xs font-semibold border border-amber-500/40 transition-all disabled:opacity-50"
              title="Trigger second nearby SOS within 500m to showcase priority re-ranking live"
            >
              <Flame className="w-3 h-3 text-amber-400" />
              <span>+Corroborate (500m)</span>
            </button>

            <button
              onClick={handleTriggerSimulatedReading}
              disabled={isSimulatingReading}
              className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-dark-800 hover:bg-dark-700 text-slate-200 text-xs font-medium border border-white/5 transition-all disabled:opacity-50"
              title="Inject random signal telemetry point"
            >
              <Sparkles className="w-3 h-3 text-cyan-400" />
              <span>+Telemetry</span>
            </button>

          </div>

        </div>

      </div>
    </header>
  );
};
