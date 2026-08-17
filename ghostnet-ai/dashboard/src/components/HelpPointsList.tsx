import React, { useState } from 'react';
import { HelpPoint, HelpPointType } from '../types';
import { Hospital, Shield, Home, Flag, MapPin, Navigation, Search } from 'lucide-react';

interface HelpPointsListProps {
  helpPoints: HelpPoint[];
}

export const HelpPointsList: React.FC<HelpPointsListProps> = ({ helpPoints }) => {
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState<string>('');

  const filteredPoints = helpPoints.filter((hp) => {
    const matchesFilter = filter === 'all' || hp.type === filter;
    const matchesSearch = hp.name.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getIcon = (type: HelpPointType) => {
    switch (type) {
      case 'hospital':
        return <Hospital className="w-4 h-4 text-rose-400" />;
      case 'police':
        return <Shield className="w-4 h-4 text-blue-400" />;
      case 'shelter':
        return <Home className="w-4 h-4 text-amber-400" />;
      case 'safe_zone':
      default:
        return <Flag className="w-4 h-4 text-emerald-400" />;
    }
  };

  const getBadgeStyle = (type: HelpPointType) => {
    switch (type) {
      case 'hospital':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'police':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'shelter':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'safe_zone':
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-5 border border-white/10 flex flex-col h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Navigation className="w-4 h-4 text-ghost-cyan" />
            Purulia Emergency Help Points
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Pre-cached offline safety points in the district
          </p>
        </div>
        <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-lg bg-dark-800 border border-white/10 text-cyan-400">
          {filteredPoints.length} Found
        </span>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search hospital, police, shelter..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-dark-800/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0">
          {['all', 'hospital', 'police', 'shelter', 'safe_zone'].map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize whitespace-nowrap transition-all ${
                filter === t
                  ? 'bg-cyan-500 text-dark-900 font-bold shadow-glow-cyan'
                  : 'bg-dark-800 text-slate-400 hover:text-white border border-white/5'
              }`}
            >
              {t.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="space-y-2.5 overflow-y-auto max-h-[380px] pr-1">
        {filteredPoints.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No help points matching current filter.
          </div>
        ) : (
          filteredPoints.map((hp) => (
            <div
              key={hp.id}
              className="p-3 rounded-xl bg-dark-800/60 hover:bg-dark-700/60 border border-white/5 hover:border-cyan-500/30 transition-all flex items-center justify-between gap-3 group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-dark-900 border border-white/10 group-hover:scale-105 transition-transform">
                  {getIcon(hp.type)}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200 group-hover:text-white transition-colors">
                    {hp.name}
                  </h4>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${getBadgeStyle(hp.type)}`}>
                      {hp.type.replace('_', ' ')}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {hp.lat.toFixed(4)}, {hp.lon.toFixed(4)}
                    </span>
                  </div>
                </div>
              </div>

              {hp.distance_km !== undefined && (
                <div className="text-right">
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    {hp.distance_km} km
                  </span>
                  <p className="text-[10px] text-slate-500">from Sadar</p>
                </div>
              )}
            </div>
          ))
        )}
      </div>

    </div>
  );
};
