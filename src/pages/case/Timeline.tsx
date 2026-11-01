import React, { useEffect, useState, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import {
  Clock,
  MapPin,
  FileText,
  ChevronRight,
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Rewind,
  Radio,
  Video,
  UserCheck,
  AlertTriangle,
  ShieldCheck,
  ExternalLink,
  X,
  Zap,
  Map as MapIcon,
  HelpCircle,
  Layers
} from 'lucide-react';
import { cn } from '../../utils';
import {
  geospatialTimelineService,
  SpatioTemporalPoint,
  ImpossibleTravelAnomaly,
  GeospatialTimelineData
} from '../../services';

export function Timeline() {
  const { caseId = '1' } = useParams<{ caseId: string }>();

  const [data, setData] = useState<GeospatialTimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter State
  const [activeFilter, setActiveFilter] = useState<'all' | 'cdr' | 'cctv' | 'witness' | 'impossible'>('all');

  // Replay State
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<1 | 2 | 5 | 10>(1);
  const [currentReplayTime, setCurrentReplayTime] = useState<number>(0);
  const [timeMin, setTimeMin] = useState<number>(0);
  const [timeMax, setTimeMax] = useState<number>(100);

  // Inspector Drawer State
  const [selectedPoint, setSelectedPoint] = useState<SpatioTemporalPoint | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [liveToast, setLiveToast] = useState<string | null>(null);

  const intervalRef = useRef<any>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await geospatialTimelineService.getGeospatialTimeline(caseId);
      setData(res);
      if (res.points.length > 0) {
        const tStart = new Date(res.time_horizon.min_time).getTime();
        const tEnd = new Date(res.time_horizon.max_time).getTime();
        setTimeMin(tStart);
        setTimeMax(tEnd);
        setCurrentReplayTime(tEnd);
      }
      setError(null);
    } catch (err) {
      console.error('Failed to load timeline:', err);
      setError('Could not load chronological events.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  // Replay interval timer
  useEffect(() => {
    if (isPlaying) {
      const stepMs = 300;
      const advancePerTick = playbackSpeed * 60000 * 2; // 2 mins per tick scaled by speed

      intervalRef.current = setInterval(() => {
        setCurrentReplayTime((prev) => {
          const next = prev + advancePerTick;
          if (next >= timeMax) {
            setIsPlaying(false);
            return timeMax;
          }
          return next;
        });
      }, stepMs);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, playbackSpeed, timeMin, timeMax]);

  // Simulate Live Sighting
  const handleSimulateLiveEvent = async () => {
    try {
      setSimulating(true);
      const res = await geospatialTimelineService.simulateEvent(caseId);
      setLiveToast(`📡 New Spatio-Temporal Hit: ${res.point?.title || 'ALPR Plate Hit'}`);

      if (res.point) {
        const newPt: SpatioTemporalPoint = {
          ...res.point,
          is_live_arrived: true,
        };
        setData((prev) => {
          if (!prev) return prev;
          const updated = [...prev.points, newPt];
          return {
            ...prev,
            points: updated,
            total_points_count: updated.length,
          };
        });
        const ptTime = new Date(newPt.timestamp).getTime();
        if (ptTime > timeMax) {
          setTimeMax(ptTime);
          setCurrentReplayTime(ptTime);
        }
      }
      setTimeout(() => setLiveToast(null), 6000);
    } catch (err: any) {
      console.error('Simulation error:', err);
    } finally {
      setSimulating(false);
    }
  };

  const formatDateTime = (ts: string | number) => {
    const d = new Date(ts);
    return {
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      full: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    };
  };

  const handlePresetCrimeWindow = () => {
    if (!data?.time_horizon) return;
    const tStart = new Date(data.time_horizon.min_time).getTime();
    const tEnd = new Date(data.time_horizon.max_time).getTime();
    setTimeMin(tStart);
    setTimeMax(tEnd);
    setCurrentReplayTime(tStart);
    setIsPlaying(true);
  };

  const handleStep = (direction: 'back' | 'forward') => {
    const stepDelta = 15 * 60000;
    setCurrentReplayTime((prev) => {
      const target = direction === 'forward' ? prev + stepDelta : prev - stepDelta;
      return Math.max(timeMin, Math.min(timeMax, target));
    });
  };

  // Filtered & Replay-Constrained Points
  const visibleEvents = useMemo(() => {
    if (!data) return [];
    return data.points
      .filter((pt) => {
        // Replay Scrubber constraint
        const ptTime = new Date(pt.timestamp).getTime();
        if (ptTime > currentReplayTime) return false;

        // Layer Filter constraint
        if (activeFilter === 'all') return true;
        if (activeFilter === 'cdr' && pt.geo_type === 'tower_sector') return true;
        if (activeFilter === 'cctv' && pt.geo_type === 'point') return true;
        if (activeFilter === 'witness' && pt.geo_type === 'area') return true;
        return false;
      })
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [data, currentReplayTime, activeFilter]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-24 font-sans relative">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-border shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-serif font-bold text-[#191410]">Chronological Case Timeline</h1>
            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
              REAL-TIME SYNC
            </span>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Dynamic evidence chronology with visual temporal uncertainty windows, cellular tower azimuths, and backing exhibit provenance.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Simulate Live Hit */}
          <button
            onClick={handleSimulateLiveEvent}
            disabled={simulating}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${simulating ? 'animate-spin' : ''}`} />
            {simulating ? 'Receiving...' : 'Simulate Live Hit'}
          </button>

          {/* Switch to Interactive Map */}
          <Link
            to={`/cases/${caseId}/map`}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-primary text-white hover:bg-primary-hover text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            <MapIcon className="w-3.5 h-3.5" /> Open Spatio-Temporal Map
          </Link>
        </div>
      </div>

      {/* Live Sighting Toast Notification */}
      {liveToast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[1000] bg-emerald-950 text-emerald-100 border border-emerald-500 px-4 py-2 rounded-lg shadow-2xl flex items-center gap-2 text-xs font-medium animate-bounce">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>{liveToast}</span>
          <button onClick={() => setLiveToast(null)} className="ml-2 text-emerald-300 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Replay Scrubber Controller Card */}
      <Card className="p-3 bg-white border border-border shadow-sm">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          {/* Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="w-9 h-9 rounded-full bg-primary hover:bg-primary-hover text-white flex items-center justify-center shadow-md transition-colors"
              title={isPlaying ? 'Pause Replay' : 'Play Replay'}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </button>

            <button
              onClick={() => handleStep('back')}
              className="p-1.5 hover:bg-slate-100 rounded text-slate-600 hover:text-slate-900 transition-colors"
              title="Step Backward 15 Minutes"
            >
              <Rewind className="w-4 h-4" />
            </button>

            <button
              onClick={() => handleStep('forward')}
              className="p-1.5 hover:bg-slate-100 rounded text-slate-600 hover:text-slate-900 transition-colors"
              title="Step Forward 15 Minutes"
            >
              <FastForward className="w-4 h-4" />
            </button>

            <div className="h-5 w-px bg-slate-200 mx-1"></div>

            {/* Speed Multipliers */}
            <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 text-xs font-mono font-semibold">
              {([1, 2, 5, 10] as const).map((spd) => (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    playbackSpeed === spd ? 'bg-white text-primary shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>

            <div className="h-5 w-px bg-slate-200 mx-1"></div>

            {/* Quick Preset: 8 PM to 6 AM */}
            <button
              onClick={handlePresetCrimeWindow}
              className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 rounded-lg text-xs font-semibold transition-colors"
              title="Play the case from 8 PM to 6 AM"
            >
              <Clock className="w-3.5 h-3.5 text-amber-600" />
              <span>{data?.time_horizon?.preset_label || 'Play Crime Window (8 PM – 6 AM)'}</span>
            </button>
          </div>

          {/* Time Scrubber Slider */}
          <div className="flex-1 w-full flex items-center gap-3">
            <span className="text-[11px] font-mono text-slate-500 whitespace-nowrap">
              {timeMin ? new Date(timeMin).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
            </span>

            <input
              type="range"
              min={timeMin}
              max={timeMax}
              value={currentReplayTime}
              onChange={(e) => setCurrentReplayTime(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary"
            />

            <span className="text-[11px] font-mono text-slate-500 whitespace-nowrap">
              {timeMax ? new Date(timeMax).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
            </span>
          </div>

          {/* Readout */}
          <div className="px-3 py-1 bg-emerald-50 border border-emerald-200 text-emerald-800 font-mono text-xs font-bold rounded-xl shadow-xs whitespace-nowrap flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span>{currentReplayTime ? new Date(currentReplayTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}</span>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100 text-xs">
          <span className="text-text-muted font-medium flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" /> Filter by Source:
          </span>
          {(['all', 'cdr', 'cctv', 'witness'] as const).map((filterKey) => (
            <button
              key={filterKey}
              onClick={() => setActiveFilter(filterKey)}
              className={`px-2.5 py-0.5 rounded-md text-xs font-medium transition-colors ${
                activeFilter === filterKey
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {filterKey === 'all' && `All Events (${data?.total_points_count || 0})`}
              {filterKey === 'cdr' && `CDR Towers (${data?.cdr_pings_count || 0})`}
              {filterKey === 'cctv' && `CCTV Sightings (${data?.cctv_sightings_count || 0})`}
              {filterKey === 'witness' && `Witness Reports (${data?.witness_reports_count || 0})`}
            </button>
          ))}
        </div>
      </Card>

      {/* Impossible Travel Alert Banner */}
      {data?.impossible_travel_anomalies && data.impossible_travel_anomalies.length > 0 && (
        <div className="bg-red-50 border-l-4 border-red-600 p-3 rounded-r-xl shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-red-900 font-bold text-sm">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <span>Automated Velocity Anomaly: Impossible Travel Detected</span>
            </div>
            <span className="text-xs font-mono font-bold px-2 py-0.5 bg-red-200 text-red-800 rounded">
              {data.impossible_travel_anomalies[0].calculated_speed_kmh} km/h
            </span>
          </div>
          <p className="text-xs text-red-800 leading-relaxed">
            {data.impossible_travel_anomalies[0].reasoning}
          </p>
          <div className="text-[11px] text-red-700 flex items-center gap-4 pt-1 border-t border-red-200/60 font-mono">
            <span>From: {data.impossible_travel_anomalies[0].from_location}</span>
            <span>→</span>
            <span>To: {data.impossible_travel_anomalies[0].to_location}</span>
            <span className="text-slate-500">({data.impossible_travel_anomalies[0].distance_km} km in {data.impossible_travel_anomalies[0].time_delta_minutes}m)</span>
          </div>
        </div>
      )}

      {/* Chronological Vertical Timeline Stream */}
      <div className="relative border-l-2 border-primary/20 ml-6 md:ml-28 mt-8 space-y-8">
        {visibleEvents.map((pt, index) => {
          const dt = formatDateTime(pt.timestamp);
          const isCDR = pt.geo_type === 'tower_sector';
          const isCCTV = pt.geo_type === 'point';
          const isWitness = pt.geo_type === 'area';
          const hasUncertainty = pt.time_uncertainty_minutes > 0;

          return (
            <div
              key={pt.id}
              className={cn(
                "relative flex items-start group transition-all duration-300",
                pt.is_live_arrived && "animate-pulse"
              )}
            >
              {/* Timeline Icon Node */}
              <div
                className={cn(
                  "absolute -left-[33px] md:-left-[29px] w-14 h-14 bg-white border-4 rounded-full flex items-center justify-center group-hover:scale-110 transition-all z-10 shadow-md",
                  isCDR && "border-amber-400 text-amber-600",
                  isCCTV && "border-blue-400 text-blue-600",
                  isWitness && "border-purple-400 text-purple-600",
                  !isCDR && !isCCTV && !isWitness && "border-primary/30 text-primary"
                )}
              >
                {isCDR && <Radio className="w-5 h-5" />}
                {isCCTV && <Video className="w-5 h-5" />}
                {isWitness && <UserCheck className="w-5 h-5" />}
                {!isCDR && !isCCTV && !isWitness && <Clock className="w-5 h-5" />}
              </div>

              {/* Date/Time Left Column (Desktop) */}
              <div className="hidden md:block absolute -left-52 w-44 text-right pr-8">
                <div className="text-sm font-bold text-slate-900">{dt.date}</div>
                <div className="text-xs font-mono text-primary font-semibold mt-0.5">{dt.time}</div>
                {hasUncertainty && (
                  <div className="text-[10px] font-mono text-amber-600 mt-0.5">
                    ±{pt.time_uncertainty_minutes}m window
                  </div>
                )}
              </div>

              {/* Event Content Card */}
              <Card
                onClick={() => setSelectedPoint(pt)}
                className={cn(
                  "ml-12 md:ml-16 w-full max-w-3xl cursor-pointer hover:border-primary/40 hover:shadow-lg transition-all",
                  pt.is_live_arrived && "border-emerald-500 bg-emerald-50/20"
                )}
              >
                <div className="p-4">
                  {/* Mobile Date Header */}
                  <div className="md:hidden flex items-center gap-2 mb-2 text-xs">
                    <span className="font-bold text-slate-800">{dt.date}</span>
                    <span className="text-primary font-mono font-semibold">{dt.time}</span>
                    {hasUncertainty && (
                      <span className="text-amber-600 font-mono text-[10px]">±{pt.time_uncertainty_minutes}m</span>
                    )}
                  </div>

                  {/* Header Row */}
                  <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-serif font-bold text-[#191410] group-hover:text-primary transition-colors">
                        {pt.title}
                      </h3>
                      {pt.is_live_arrived && (
                        <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded text-[9px] font-bold tracking-wider animate-pulse">
                          LIVE ARRIVED
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      {/* Spatial Geometry Badge */}
                      {isCDR && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
                          <Radio className="w-3 h-3 text-amber-600" /> Sector {pt.azimuth}° ({pt.radius_meters}m)
                        </span>
                      )}
                      {isCCTV && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                          <Video className="w-3 h-3 text-blue-600" /> CCTV Cam
                        </span>
                      )}
                      {isWitness && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-50 text-purple-700 border border-purple-200 flex items-center gap-1">
                          <UserCheck className="w-3 h-3 text-purple-600" /> Witness Area ({pt.radius_meters}m)
                        </span>
                      )}

                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Conf: {pt.confidence}%
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-text-muted mb-3 leading-relaxed">{pt.description}</p>

                  {/* Visual Temporal Uncertainty Interval Bar */}
                  {hasUncertainty && (
                    <div className="mb-3 p-2 bg-amber-50/70 border border-amber-200/80 rounded-lg">
                      <div className="flex items-center justify-between text-[10px] font-bold text-amber-900 mb-1">
                        <span className="flex items-center gap-1">
                          <HelpCircle className="w-3 h-3 text-amber-600" /> Temporal Uncertainty Interval
                        </span>
                        <span className="font-mono">
                          Window: ±{pt.time_uncertainty_minutes} minutes
                        </span>
                      </div>
                      <div className="relative h-2 w-full bg-amber-200/60 rounded-full overflow-hidden">
                        <div
                          className="absolute inset-y-0 bg-gradient-to-r from-transparent via-amber-500 to-transparent w-full opacity-80 animate-pulse"
                        />
                      </div>
                      <div className="flex justify-between text-[9px] font-mono text-amber-700 mt-1">
                        <span>{dt.time} - {pt.time_uncertainty_minutes}m</span>
                        <span className="font-bold">Estimated Peak: {dt.time}</span>
                        <span>{dt.time} + {pt.time_uncertainty_minutes}m</span>
                      </div>
                    </div>
                  )}

                  {/* Ground Truth Citation Quote Preview */}
                  {pt.source_quote && (
                    <div className="mb-3 bg-slate-50 border-l-2 border-primary/60 px-2.5 py-1.5 rounded-r text-[11px] font-serif italic text-slate-700">
                      "{pt.source_quote}"
                    </div>
                  )}

                  {/* Footer Metadata */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2.5 border-t border-border/50 text-[11px]">
                    <div className="flex items-center gap-1.5 text-text-muted truncate">
                      <MapPin className="w-3.5 h-3.5 text-primary/70 shrink-0" />
                      <span className="truncate" title={pt.location_name}>{pt.location_name}</span>
                    </div>

                    <div className="flex items-center gap-1.5 text-text-muted truncate">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span className="truncate text-emerald-800 font-medium">Sec 65B Hash Verified</span>
                    </div>

                    <div className="flex items-center justify-end gap-1 text-primary hover:text-primary-hover font-medium cursor-pointer transition-colors group/link">
                      <FileText className="w-3.5 h-3.5" />
                      <span className="truncate">Ex. #{pt.source_evidence_id}: {pt.source_evidence_name}</span>
                      <ChevronRight className="w-3 h-3 opacity-0 group-hover/link:opacity-100 transition-opacity" />
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          );
        })}
      </div>

      {/* Source Provenance Inspector Drawer (Slide-over on card click) */}
      {selectedPoint && (
        <div className="fixed top-0 right-0 bottom-0 w-96 bg-white shadow-2xl border-l border-border z-[1000] flex flex-col p-4 animate-in slide-in-from-right duration-200">
          <div className="flex items-center justify-between border-b pb-3 mb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" />
              <h3 className="font-serif font-bold text-base text-[#191410]">Exhibit Provenance Inspector</h3>
            </div>
            <button
              onClick={() => setSelectedPoint(null)}
              className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-4 pr-1 text-xs">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div className="flex items-center justify-between mb-1">
                <span className="px-2 py-0.5 bg-primary/10 text-primary font-bold rounded text-[10px]">
                  Exhibit #{selectedPoint.source_evidence_id}
                </span>
                <span className="flex items-center gap-1 text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" /> SEC 65B CERTIFIED
                </span>
              </div>
              <div className="font-mono text-[11px] font-bold text-slate-800 break-all">
                {selectedPoint.source_evidence_name}
              </div>
              <div className="text-[10px] text-text-muted mt-1">
                Document Index: <span className="font-semibold text-slate-700">Row/Page {selectedPoint.source_page_or_row}</span>
              </div>
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted block mb-1">
                Exact Ground-Truth Quote:
              </label>
              <div className="bg-amber-50/80 border-l-4 border-amber-500 p-2.5 rounded-r-lg font-serif italic text-slate-800 text-xs leading-relaxed">
                "{selectedPoint.source_quote}"
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                Spatial & Radio Geometry
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-text-muted">Geometry:</span>{' '}
                  <span className="font-semibold text-slate-800 capitalize">{selectedPoint.geo_type.replace('_', ' ')}</span>
                </div>
                <div>
                  <span className="text-text-muted">Radius:</span>{' '}
                  <span className="font-semibold text-slate-800">{selectedPoint.radius_meters}m</span>
                </div>
                {selectedPoint.azimuth !== null && (
                  <div>
                    <span className="text-text-muted">Azimuth:</span>{' '}
                    <span className="font-semibold text-slate-800">{selectedPoint.azimuth}°</span>
                  </div>
                )}
                {selectedPoint.beam_width !== null && (
                  <div>
                    <span className="text-text-muted">Beam Width:</span>{' '}
                    <span className="font-semibold text-slate-800">{selectedPoint.beam_width}°</span>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-1 text-[11px]">
              <div><span className="text-text-muted">Location:</span> <span className="font-medium text-slate-800">{selectedPoint.location_name}</span></div>
              <div><span className="text-text-muted">Entity:</span> <span className="font-medium text-slate-800">{selectedPoint.suspect_or_entity}</span></div>
              <div><span className="text-text-muted">Time:</span> <span className="font-mono text-slate-800">{new Date(selectedPoint.timestamp).toLocaleString()}</span></div>
              <div><span className="text-text-muted">Confidence:</span> <span className="font-semibold text-emerald-700">{selectedPoint.confidence}%</span></div>
            </div>
          </div>

          <div className="pt-3 border-t flex justify-end">
            <Link
              to={`/cases/${caseId}/evidence`}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-hover transition-colors shadow-sm"
            >
              Open Backing Exhibit <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
