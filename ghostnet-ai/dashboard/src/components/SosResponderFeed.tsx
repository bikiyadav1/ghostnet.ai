import React, { useState } from 'react';
import { SosAlert, SosStatus } from '../types';
import {
  AlertCircle,
  Clock,
  Radio,
  CheckCircle2,
  Eye,
  ShieldAlert,
  Flame,
  Activity,
  Sparkles,
  Layers,
  HelpCircle,
} from 'lucide-react';
import { updateSosStatus } from '../services/api';

interface SosResponderFeedProps {
  alerts: SosAlert[];
  onRefresh: () => void;
}

export const SosResponderFeed: React.FC<SosResponderFeedProps> = ({ alerts, onRefresh }) => {
  const [filter, setFilter] = useState<string>('active');
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'active') return a.status === 'sent' || a.status === 'queued';
    if (filter === 'acknowledged') return a.status === 'acknowledged';
    if (filter === 'resolved') return a.status === 'resolved';
    return true;
  });

  const handleStatusChange = async (alertId: string, newStatus: SosStatus) => {
    setUpdatingId(alertId);
    try {
      await updateSosStatus(alertId, newStatus);
      onRefresh();
    } catch (err) {
      console.error('Failed to update alert status:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'medical':
        return {
          label: 'Medical Emergency',
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/50',
          icon: <Activity className="w-3.5 h-3.5 text-rose-400" />,
        };
      case 'disaster':
        return {
          label: 'Natural Disaster',
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/50',
          icon: <Flame className="w-3.5 h-3.5 text-amber-400" />,
        };
      case 'security':
        return {
          label: 'Security / Safety',
          bg: 'bg-blue-500/20 text-blue-300 border-blue-500/50',
          icon: <ShieldAlert className="w-3.5 h-3.5 text-blue-400" />,
        };
      case 'general':
      default:
        return {
          label: 'General Assistance',
          bg: 'bg-slate-700/60 text-slate-300 border-slate-600',
          icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
        };
    }
  };

  const getPriorityColor = (score: number) => {
    if (score >= 0.8) return 'text-rose-400 bg-rose-500';
    if (score >= 0.6) return 'text-amber-400 bg-amber-500';
    return 'text-cyan-400 bg-cyan-500';
  };

  return (
    <div className="glass-panel rounded-2xl p-5 border border-white/10 flex flex-col h-full">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white flex items-center gap-2 font-sans">
              <AlertCircle className="w-5 h-5 text-rose-400 animate-pulse" />
              Live Emergency SOS Responder Queue
            </h3>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-800/60">
              Priority Ranked
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Dynamic scoring based on Category (40%) · Recency Decay (25%) · Proximity Corroboration (20%) · Dead-Zone Risk (15%)
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-1 bg-dark-900/80 p-1 rounded-xl border border-white/10 self-start sm:self-auto">
          {['active', 'acknowledged', 'resolved', 'all'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition-all ${
                filter === tab
                  ? 'bg-cyan-500 text-dark-900 shadow-glow-cyan'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Alert Feed List */}
      <div className="space-y-3 overflow-y-auto max-h-[560px] pr-1">
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No emergency alerts matching current filter.
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const catBadge = getCategoryBadge(alert.category);
            const isExpanded = selectedAlertId === alert.id;
            const priorityColor = getPriorityColor(alert.priority_score);

            return (
              <div
                key={alert.id}
                className={`p-4 rounded-xl border transition-all ${
                  alert.status === 'resolved'
                    ? 'bg-dark-900/50 border-white/5 opacity-60'
                    : alert.priority_score >= 0.8
                    ? 'bg-rose-950/20 border-rose-500/30 hover:border-rose-500/60 shadow-glow-rose'
                    : 'bg-dark-800/60 border-white/10 hover:border-cyan-500/30'
                }`}
              >
                {/* Top Row: Category + Priority Score + Status */}
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg border ${catBadge.bg}`}
                    >
                      {catBadge.icon}
                      {catBadge.label}
                    </span>

                    {/* Corroboration Badge */}
                    {alert.corroboration_count > 0 && (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                        <Flame className="w-3 h-3 text-amber-400" />
                        +{alert.corroboration_count} Nearby Corroborations
                      </span>
                    )}

                    {/* Mesh Relay Tag */}
                    {alert.is_relayed && (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center gap-1">
                        <Radio className="w-3 h-3 text-purple-400" />
                        Relayed via Mesh Peer
                      </span>
                    )}
                  </div>

                  {/* Priority Gauge */}
                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-400 font-mono font-semibold">Priority:</span>
                      <span className="text-sm font-mono font-bold text-white">
                        {(alert.priority_score * 100).toFixed(0)}
                        <span className="text-[10px] text-slate-400">/100</span>
                      </span>
                    </div>
                    {/* Progress Bar */}
                    <div className="w-24 h-1.5 bg-dark-900 rounded-full overflow-hidden mt-1 border border-white/5">
                      <div
                        className={`h-full ${priorityColor.split(' ')[1]} transition-all duration-500`}
                        style={{ width: `${Math.min(100, alert.priority_score * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Message / Details */}
                <div className="mt-3">
                  <p className="text-sm font-medium text-slate-100">
                    {alert.message || 'Emergency assistance requested at this location.'}
                  </p>
                </div>

                {/* Metadata & Coordinates */}
                <div className="mt-3 flex items-center justify-between text-xs text-slate-400 flex-wrap gap-2 pt-2 border-t border-white/5">
                  <div className="flex items-center gap-3 font-mono text-[11px]">
                    <span>Lat: {alert.lat.toFixed(4)}, Lon: {alert.lon.toFixed(4)}</span>
                    <span className="text-slate-600">•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {new Date(alert.created_at).toLocaleTimeString()}
                    </span>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedAlertId(isExpanded ? null : alert.id)}
                      className="px-2.5 py-1 rounded-lg bg-dark-900 hover:bg-dark-700 border border-white/10 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1 transition-colors"
                    >
                      <Eye className="w-3 h-3" />
                      {isExpanded ? 'Hide Math' : 'Inspect Score'}
                    </button>

                    {alert.status !== 'acknowledged' && alert.status !== 'resolved' && (
                      <button
                        onClick={() => handleStatusChange(alert.id, 'acknowledged')}
                        disabled={updatingId === alert.id}
                        className="px-3 py-1 rounded-lg bg-blue-600/30 hover:bg-blue-600 text-blue-200 hover:text-white border border-blue-500/50 text-xs font-semibold transition-all disabled:opacity-50"
                      >
                        Acknowledge
                      </button>
                    )}

                    {alert.status !== 'resolved' && (
                      <button
                        onClick={() => handleStatusChange(alert.id, 'resolved')}
                        disabled={updatingId === alert.id}
                        className="px-3 py-1 rounded-lg bg-emerald-600/30 hover:bg-emerald-600 text-emerald-200 hover:text-white border border-emerald-500/50 text-xs font-semibold transition-all disabled:opacity-50"
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                </div>

                {/* Inspectable Formula Breakdown Panel */}
                {isExpanded && (
                  <div className="mt-3 p-3 rounded-xl bg-dark-900/90 border border-cyan-500/30 text-xs space-y-2">
                    <div className="flex items-center justify-between text-ghost-cyan font-semibold">
                      <span>Formula Inspection (Score: {alert.priority_score})</span>
                      <span className="font-mono text-[11px] text-slate-400">SIH 2026 Transparent Ranking</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
                      <div className="p-2 rounded bg-dark-800 border border-white/5">
                        <span className="text-slate-400 block text-[10px]">Category (40%)</span>
                        <span className="text-rose-400 font-bold">
                          +{alert.category === 'medical' ? '0.400' : alert.category === 'disaster' ? '0.360' : alert.category === 'security' ? '0.320' : '0.200'}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-dark-800 border border-white/5">
                        <span className="text-slate-400 block text-[10px]">Recency (25%)</span>
                        <span className="text-amber-400 font-bold">
                          +{alert.breakdown?.recency_term || '0.245'}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-dark-800 border border-white/5">
                        <span className="text-slate-400 block text-[10px]">Corroboration (20%)</span>
                        <span className="text-emerald-400 font-bold">
                          +{Math.min(alert.corroboration_count, 5) * 0.04}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-dark-800 border border-white/5">
                        <span className="text-slate-400 block text-[10px]">Dead-Zone Risk (15%)</span>
                        <span className="text-cyan-400 font-bold">
                          +{alert.breakdown?.location_risk_term || '0.120'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
