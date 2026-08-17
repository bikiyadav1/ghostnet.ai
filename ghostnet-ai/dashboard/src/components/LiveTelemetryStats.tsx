import React from 'react';
import { CoveragePoint, HeatmapCell, WsMessagePayload } from '../types';
import { Signal, Radio, AlertTriangle, Zap, Server, ArrowDownUp } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

interface LiveTelemetryStatsProps {
  coveragePoints: CoveragePoint[];
  heatmapCells: HeatmapCell[];
  liveReadingsCount: number;
  recentTelemetry: WsMessagePayload[];
}

export const LiveTelemetryStats: React.FC<LiveTelemetryStatsProps> = ({
  coveragePoints,
  heatmapCells,
  liveReadingsCount,
  recentTelemetry,
}) => {
  const totalReadings = coveragePoints.length;
  
  // Calculate average signal
  const avgDbm = totalReadings > 0
    ? Math.round(coveragePoints.reduce((acc, p) => acc + p.signal_dbm, 0) / totalReadings)
    : -85;

  // Dead zone cells count
  const deadZoneCellsCount = heatmapCells.filter((c) => c.avg_signal_dbm < -100).length;

  // Network distribution
  const networkCounts: Record<string, number> = { '5G': 0, '4G': 0, '3G': 0, '2G': 0, 'none': 0 };
  coveragePoints.forEach((p) => {
    if (networkCounts[p.network_type] !== undefined) {
      networkCounts[p.network_type]++;
    }
  });

  const chartData = [
    { name: '5G', count: networkCounts['5G'], color: '#00F0FF' },
    { name: '4G', count: networkCounts['4G'], color: '#10B981' },
    { name: '3G', count: networkCounts['3G'], color: '#F59E0B' },
    { name: '2G', count: networkCounts['2G'], color: '#F97316' },
    { name: 'None', count: networkCounts['none'], color: '#F43F5E' },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      
      {/* Metric 1: Total Telemetry Readings */}
      <div className="glass-panel p-4 rounded-xl border border-white/10 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Total Telemetry
          </span>
          <div className="p-2 rounded-lg bg-cyan-500/10 text-ghost-cyan">
            <Radio className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-white tracking-tight">
            {totalReadings.toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <span className="text-emerald-400 font-semibold font-mono">+{liveReadingsCount}</span> live stream packets
          </p>
        </div>
        <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-cyan-500/10 rounded-full blur-xl pointer-events-none" />
      </div>

      {/* Metric 2: Mean Signal dBm */}
      <div className="glass-panel p-4 rounded-xl border border-white/10 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Avg District Signal
          </span>
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Signal className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
            {avgDbm} <span className="text-sm font-sans font-normal text-slate-400">dBm</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            GIST Spatial Indexed Grid
          </p>
        </div>
        <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-emerald-500/10 rounded-full blur-xl pointer-events-none" />
      </div>

      {/* Metric 3: Detected Dead Zones */}
      <div className="glass-panel p-4 rounded-xl border border-white/10 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Dead-Zone Cells
          </span>
          <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-rose-400 tracking-tight">
            {deadZoneCellsCount} <span className="text-sm font-sans font-normal text-slate-400">cells</span>
          </div>
          <p className="text-[11px] text-rose-300/80 mt-1">
            Signal &lt; -100 dBm (Offline risk)
          </p>
        </div>
        <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-rose-500/10 rounded-full blur-xl pointer-events-none" />
      </div>

      {/* Metric 4: Live Telemetry Distribution Chart */}
      <div className="glass-panel p-4 rounded-xl border border-white/10 relative flex flex-col justify-between">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Network Types
          </span>
          <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400">
            <Zap className="w-3.5 h-3.5" />
          </div>
        </div>
        
        <div className="h-16 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 0, right: 0, left: -25, bottom: -10 }}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip
                contentStyle={{ background: '#111827', borderColor: '#374151', borderRadius: '8px', fontSize: '11px' }}
                itemStyle={{ color: '#00F0FF' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};
