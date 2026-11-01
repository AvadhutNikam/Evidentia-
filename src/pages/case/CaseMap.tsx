import React, { useEffect, useRef, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Card } from '../../components/ui/Card';
import {
  Map as MapIcon,
  Filter,
  Layers,
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
  FileText,
  Clock,
  Compass,
  Zap,
  ExternalLink,
  ChevronRight,
  X,
  Eye,
  Info
} from 'lucide-react';
import {
  geospatialTimelineService,
  SpatioTemporalPoint,
  ImpossibleTravelAnomaly,
  GeospatialTimelineData
} from '../../services';

// Helper to calculate geodesic points along an azimuth arc (cellular sector polygon cone)
function computeSectorPolygon(
  lat: number,
  lon: number,
  radiusMeters: number,
  azimuthDeg: number,
  beamWidthDeg: number
): [number, number][] {
  const points: [number, number][] = [[lat, lon]];
  const startAngle = azimuthDeg - beamWidthDeg / 2;
  const endAngle = azimuthDeg + beamWidthDeg / 2;
  const steps = 18;
  const earthRadius = 6378137; // meters

  for (let i = 0; i <= steps; i++) {
    const angle = (startAngle + (endAngle - startAngle) * (i / steps)) * (Math.PI / 180);
    const d = radiusMeters / earthRadius;
    const latRad = lat * (Math.PI / 180);
    const lonRad = lon * (Math.PI / 180);

    const pLat = Math.asin(
      Math.sin(latRad) * Math.cos(d) + Math.cos(latRad) * Math.sin(d) * Math.cos(angle)
    );
    const pLon =
      lonRad +
      Math.atan2(
        Math.sin(angle) * Math.sin(d) * Math.cos(latRad),
        Math.cos(d) - Math.sin(latRad) * Math.sin(pLat)
      );

    points.push([pLat * (180 / Math.PI), pLon * (180 / Math.PI)]);
  }

  points.push([lat, lon]);
  return points;
}

export function CaseMap() {
  const { caseId = '1' } = useParams<{ caseId: string }>();

  // Data State
  const [data, setData] = useState<GeospatialTimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active Layers
  const [layerCDR, setLayerCDR] = useState(true);
  const [layerCCTV, setLayerCCTV] = useState(true);
  const [layerWitness, setLayerWitness] = useState(true);
  const [layerImpossibleTravel, setLayerImpossibleTravel] = useState(true);

  // Replay State
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<1 | 2 | 5 | 10>(1);
  const [currentReplayTime, setCurrentReplayTime] = useState<number>(0);
  const [timeMin, setTimeMin] = useState<number>(0);
  const [timeMax, setTimeMax] = useState<number>(100);

  // Selected Inspector Point / Anomaly
  const [selectedPoint, setSelectedPoint] = useState<SpatioTemporalPoint | null>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<ImpossibleTravelAnomaly | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [liveToast, setLiveToast] = useState<string | null>(null);

  // Map DOM & Leaflet References
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const intervalRef = useRef<any>(null);

  // 1. Fetch Spatio-Temporal Intelligence
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
        setCurrentReplayTime(tEnd); // default to full view
      }
      setError(null);
    } catch (err: any) {
      console.error('Failed to load geospatial timeline:', err);
      setError('Failed to load geospatial data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  // 2. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    // Center on default coordinate (Pune / Western corridor)
    const initialLat = 18.5518;
    const initialLon = 73.9352;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 12,
      zoomControl: false,
    });

    // Dark-themed tactical tiles (CartoDB Dark Matter / Positron)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 3. Replay Timer Loop
  useEffect(() => {
    if (isPlaying) {
      const stepMs = 300; // interval tick
      const timeSpan = timeMax - timeMin || 3600000;
      // Advance by (playbackSpeed * 12 minutes per real second)
      const advancePerTick = (playbackSpeed * 60000 * 2);

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

  // 4. Render Layers and Uncertainty on Map
  useEffect(() => {
    const map = mapInstanceRef.current;
    const lg = layerGroupRef.current;
    if (!map || !lg || !data) return;

    lg.clearLayers();

    const bounds: [number, number][] = [];

    // Filter points by current replay timestamp
    const activePoints = data.points.filter((pt) => {
      const ptTime = new Date(pt.timestamp).getTime();
      return ptTime <= currentReplayTime;
    });

    // A. Render Tower Sectors (Visual Uncertainty: radial cone instead of pin)
    if (layerCDR) {
      const cdrPoints = activePoints.filter((pt) => pt.geo_type === 'tower_sector');
      cdrPoints.forEach((pt) => {
        bounds.push([pt.latitude, pt.longitude]);

        const azimuth = pt.azimuth ?? 90;
        const beam = pt.beam_width ?? 65;
        const radius = pt.radius_meters || 1600;

        // True radial sector polygon
        const sectorCoords = computeSectorPolygon(pt.latitude, pt.longitude, radius, azimuth, beam);
        const sectorPolygon = L.polygon(sectorCoords, {
          color: '#d97706', // amber-600
          weight: 1.5,
          fillColor: '#f59e0b', // amber-500
          fillOpacity: 0.22,
          dashArray: '3, 4',
        });

        sectorPolygon.on('click', () => {
          setSelectedPoint(pt);
          setSelectedAnomaly(null);
        });

        sectorPolygon.bindTooltip(
          `<div class="text-xs font-sans font-bold text-amber-900 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-300">
            📡 Tower Sector: Azimuth ${azimuth}° (±${beam / 2}°) • ${pt.location_name}
          </div>`,
          { sticky: true }
        );
        lg.addLayer(sectorPolygon);

        // Vertex marker representing BTS Mast
        const btsIcon = L.divIcon({
          className: 'custom-bts-marker',
          html: `<div class="w-6 h-6 rounded-full bg-amber-500 border-2 border-white shadow-md flex items-center justify-center text-white text-[10px] font-bold cursor-pointer hover:scale-125 transition-transform">
            📡
          </div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });

        const btsMarker = L.marker([pt.latitude, pt.longitude], { icon: btsIcon });
        btsMarker.on('click', () => {
          setSelectedPoint(pt);
          setSelectedAnomaly(null);
        });
        lg.addLayer(btsMarker);
      });
    }

    // B. Render CCTV Sightings (High spatial certainty pinpoint)
    if (layerCCTV) {
      const cctvPoints = activePoints.filter((pt) => pt.geo_type === 'point');
      cctvPoints.forEach((pt) => {
        bounds.push([pt.latitude, pt.longitude]);

        const cctvIcon = L.divIcon({
          className: 'custom-cctv-marker',
          html: `<div class="relative group cursor-pointer">
            <div class="absolute -inset-1 rounded-full bg-blue-500/30 animate-ping"></div>
            <div class="w-7 h-7 rounded-full bg-blue-600 border-2 border-white shadow-lg flex items-center justify-center text-white text-[11px] font-bold">
              📹
            </div>
          </div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const marker = L.marker([pt.latitude, pt.longitude], { icon: cctvIcon });
        marker.on('click', () => {
          setSelectedPoint(pt);
          setSelectedAnomaly(null);
        });
        marker.bindTooltip(
          `<div class="text-xs font-sans font-bold text-blue-900 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-300">
            📹 CCTV: ${pt.title} (${new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
          </div>`,
          { sticky: true }
        );
        lg.addLayer(marker);
      });
    }

    // C. Render Witness Areas (Spatial Uncertainty Circle: 350-450m radius)
    if (layerWitness) {
      const witnessPoints = activePoints.filter((pt) => pt.geo_type === 'area');
      witnessPoints.forEach((pt) => {
        bounds.push([pt.latitude, pt.longitude]);

        const circle = L.circle([pt.latitude, pt.longitude], {
          radius: pt.radius_meters || 380,
          color: '#9333ea', // purple-600
          weight: 2,
          dashArray: '5, 5',
          fillColor: '#c084fc', // purple-400
          fillOpacity: 0.25,
        });

        circle.on('click', () => {
          setSelectedPoint(pt);
          setSelectedAnomaly(null);
        });
        circle.bindTooltip(
          `<div class="text-xs font-sans font-bold text-purple-900 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-300">
            👁️ Witness Area (${pt.radius_meters || 380}m uncertainty): ${pt.title}
          </div>`,
          { sticky: true }
        );
        lg.addLayer(circle);

        const wIcon = L.divIcon({
          className: 'custom-witness-marker',
          html: `<div class="w-6 h-6 rounded-full bg-purple-600 border-2 border-white shadow-md flex items-center justify-center text-white text-[10px] font-bold cursor-pointer">
            👁️
          </div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const wMarker = L.marker([pt.latitude, pt.longitude], { icon: wIcon });
        wMarker.on('click', () => {
          setSelectedPoint(pt);
          setSelectedAnomaly(null);
        });
        lg.addLayer(wMarker);
      });
    }

    // D. Render Impossible Travel Teleportation Vectors (>140 km/h)
    if (layerImpossibleTravel && data.impossible_travel_anomalies) {
      data.impossible_travel_anomalies.forEach((anom) => {
        const tA = new Date(anom.from_time).getTime();
        const tB = new Date(anom.to_time).getTime();

        // Only show if the second point in anomaly is within replay window
        if (tB <= currentReplayTime) {
          bounds.push(anom.from_coords);
          bounds.push(anom.to_coords);

          // Pulsing red trajectory line
          const polyline = L.polyline([anom.from_coords, anom.to_coords], {
            color: '#dc2626', // red-600
            weight: 4,
            dashArray: '8, 8',
            opacity: 0.9,
          });

          polyline.on('click', () => {
            setSelectedAnomaly(anom);
            setSelectedPoint(null);
          });
          lg.addLayer(polyline);

          // Midpoint Badge
          const midLat = (anom.from_coords[0] + anom.to_coords[0]) / 2;
          const midLon = (anom.from_coords[1] + anom.to_coords[1]) / 2;

          const badgeIcon = L.divIcon({
            className: 'impossible-travel-badge',
            html: `<div class="px-2 py-1 bg-red-600 text-white rounded shadow-lg border border-red-300 flex items-center gap-1.5 whitespace-nowrap cursor-pointer hover:scale-105 transition-transform text-[11px] font-mono font-bold animate-pulse">
              <span>⚠️</span>
              <span>${anom.calculated_speed_kmh} km/h IMPOSSIBLE SPEED</span>
              <span class="text-[9px] opacity-80">(${anom.distance_km}km in ${anom.time_delta_minutes}m)</span>
            </div>`,
            iconSize: [200, 26],
            iconAnchor: [100, 13],
          });

          const badgeMarker = L.marker([midLat, midLon], { icon: badgeIcon });
          badgeMarker.on('click', () => {
            setSelectedAnomaly(anom);
            setSelectedPoint(null);
          });
          lg.addLayer(badgeMarker);
        }
      });
    }

    // Pan map to fit visible points on initial load
    if (bounds.length > 0 && !isPlaying && currentReplayTime === timeMax) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40], maxZoom: 14 });
    }
  }, [data, currentReplayTime, layerCDR, layerCCTV, layerWitness, layerImpossibleTravel]);

  // 5. Simulate Live Event Push
  const handleSimulateLiveEvent = async () => {
    try {
      setSimulating(true);
      const res = await geospatialTimelineService.simulateEvent(caseId);
      setLiveToast(`📡 Live Telemetry Received: ${res.point?.title || 'New ALPR Sighting'}`);

      // Add to local state with live animation
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
      console.error('Failed to simulate live event:', err);
    } finally {
      setSimulating(false);
    }
  };

  // Replay Time Helpers
  const formatTime = (ts: number) => {
    if (!ts) return '—';
    const d = new Date(ts);
    return `${d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
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
    const stepDelta = 15 * 60000; // 15 minutes
    setCurrentReplayTime((prev) => {
      const target = direction === 'forward' ? prev + stepDelta : prev - stepDelta;
      return Math.max(timeMin, Math.min(timeMax, target));
    });
  };

  // Points currently visible at scrubber time
  const visiblePoints = useMemo(() => {
    if (!data) return [];
    return data.points.filter((pt) => new Date(pt.timestamp).getTime() <= currentReplayTime);
  }, [data, currentReplayTime]);

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col space-y-3 relative font-sans">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-border shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-serif font-bold text-[#191410]">
              Real-Time Spatio-Temporal Intelligence Map
            </h1>
            <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-semibold flex items-center gap-1 border border-red-200">
              <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span> LIVE CORRIDOR
            </span>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Unified cellular CDR tower sectors, CCTV camera pinpoints, witness observation areas, and impossible velocity alerts.
          </p>
        </div>

        {/* Action Controls & Layer Toggles */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Layer Visibility Pills */}
          <div className="flex items-center gap-1 bg-[#f8f9fa] p-1 rounded-lg border border-border text-xs">
            <button
              onClick={() => setLayerCDR(!layerCDR)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors font-medium ${
                layerCDR ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'text-text-muted hover:bg-slate-200'
              }`}
              title="Toggle Cellular Tower Azimuth Sectors"
            >
              <Radio className="w-3.5 h-3.5 text-amber-600" /> CDR Sectors
            </button>

            <button
              onClick={() => setLayerCCTV(!layerCCTV)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors font-medium ${
                layerCCTV ? 'bg-blue-100 text-blue-900 border border-blue-300' : 'text-text-muted hover:bg-slate-200'
              }`}
              title="Toggle CCTV Sightings"
            >
              <Video className="w-3.5 h-3.5 text-blue-600" /> CCTV
            </button>

            <button
              onClick={() => setLayerWitness(!layerWitness)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors font-medium ${
                layerWitness ? 'bg-purple-100 text-purple-900 border border-purple-300' : 'text-text-muted hover:bg-slate-200'
              }`}
              title="Toggle Witness Area Radius"
            >
              <UserCheck className="w-3.5 h-3.5 text-purple-600" /> Witness Area
            </button>

            <button
              onClick={() => setLayerImpossibleTravel(!layerImpossibleTravel)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors font-medium ${
                layerImpossibleTravel ? 'bg-red-100 text-red-900 border border-red-300' : 'text-text-muted hover:bg-slate-200'
              }`}
              title="Toggle Impossible Travel Teleportation Vectors"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-red-600" /> Impossible Travel ({data?.impossible_travel_count || 0})
            </button>
          </div>

          {/* Simulate Live Hit Button */}
          <button
            onClick={handleSimulateLiveEvent}
            disabled={simulating}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50"
            title="Simulate incoming real-time telemetry from ALPR camera over SSE"
          >
            <Zap className={`w-3.5 h-3.5 ${simulating ? 'animate-spin' : ''}`} />
            {simulating ? 'Receiving...' : 'Simulate Live Hit'}
          </button>

          {/* Switch to Timeline View */}
          <Link
            to={`/cases/${caseId}/timeline`}
            className="flex items-center gap-1 px-3 py-1.5 bg-surface border border-border hover:bg-surface-hover text-xs font-medium text-text-secondary rounded-lg transition-colors"
          >
            <Clock className="w-3.5 h-3.5 text-primary" /> View Timeline
          </Link>
        </div>
      </div>

      {/* Live Toast Notification */}
      {liveToast && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[1000] bg-emerald-950 text-emerald-100 border border-emerald-500 px-4 py-2 rounded-lg shadow-2xl flex items-center gap-2 text-xs font-medium animate-bounce">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>{liveToast}</span>
          <button onClick={() => setLiveToast(null)} className="ml-2 text-emerald-300 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Map Canvas & Overlay Inspector */}
      <div className="flex-1 relative rounded-xl overflow-hidden border border-[#eae4d9] shadow-xs bg-[#faf7f2]">
        <div ref={mapContainerRef} className="w-full h-full z-0" />

        {/* Tactical Map Watermark & Horizon Info */}
        <div className="absolute top-3 left-3 z-[400] bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg border border-border shadow-md pointer-events-auto max-w-xs">
          <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-1 mb-1.5">
            <span className="text-[11px] font-bold tracking-wider text-slate-700 uppercase flex items-center gap-1">
              <Compass className="w-3 h-3 text-primary" /> Spatio-Temporal Scope
            </span>
            <span className="text-[10px] font-mono font-semibold px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded">
              {visiblePoints.length}/{data?.total_points_count || 0} hits
            </span>
          </div>
          <div className="text-[11px] text-slate-600 space-y-0.5">
            <div><span className="font-semibold text-slate-800">Docket:</span> {data?.case_title || 'Case Investigation'}</div>
            <div><span className="font-semibold text-slate-800">Scrubber:</span> <span className="font-mono text-primary font-bold">{formatTime(currentReplayTime)}</span></div>
          </div>
        </div>

        {/* Uncertainty Legend Overlay */}
        <div className="absolute top-3 right-3 z-[400] bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg border border-border shadow-md pointer-events-auto text-[11px] space-y-1.5">
          <div className="font-bold text-slate-700 uppercase tracking-wider text-[10px] border-b pb-1">
            Uncertainty Visual Legend
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-3 rounded-sm bg-amber-400/40 border border-amber-600"></span>
            <span className="text-slate-700 font-medium">CDR Tower Sector (Cone)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-3 rounded-full bg-purple-400/30 border border-purple-600 border-dashed"></span>
            <span className="text-slate-700 font-medium">Witness Observation Area</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-600 border border-white"></span>
            <span className="text-slate-700 font-medium">CCTV Camera Pinpoint</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-red-600 border border-red-500 border-dashed"></span>
            <span className="text-red-700 font-bold">&gt;140 km/h Impossible Travel</span>
          </div>
        </div>

        {/* Source Exhibit Provenance Inspector Drawer (Slide-over on marker click) */}
        {selectedPoint && (
          <div className="absolute top-0 right-0 bottom-0 w-96 bg-white shadow-2xl border-l border-border z-[500] flex flex-col p-4 animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between border-b pb-3 mb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                <h3 className="font-serif font-bold text-base text-[#191410]">Source Exhibit Inspector</h3>
              </div>
              <button
                onClick={() => setSelectedPoint(null)}
                className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1 text-xs">
              {/* Exhibit Header */}
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
                  Index / Row / Page: <span className="font-semibold text-slate-700">Page {selectedPoint.source_page_or_row}</span>
                </div>
              </div>

              {/* Verified Source Quote */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted block mb-1">
                  Ground-Truth Quote in Exhibit:
                </label>
                <div className="bg-amber-50/80 border-l-4 border-amber-500 p-2.5 rounded-r-lg font-serif italic text-slate-800 text-xs leading-relaxed">
                  "{selectedPoint.source_quote}"
                </div>
              </div>

              {/* Spatial Uncertainty Breakdown */}
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                  Spatial Uncertainty Telemetry
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-text-muted">Geometry:</span>{' '}
                    <span className="font-semibold text-slate-800 capitalize">{selectedPoint.geo_type.replace('_', ' ')}</span>
                  </div>
                  <div>
                    <span className="text-text-muted">Radius:</span>{' '}
                    <span className="font-semibold text-slate-800">{selectedPoint.radius_meters} meters</span>
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
                <div className="text-[10px] text-slate-500 italic pt-1 border-t">
                  {selectedPoint.geo_type === 'tower_sector'
                    ? 'Translucent cone bounds mobile handset presence within BTS radio propagation arc.'
                    : selectedPoint.geo_type === 'area'
                    ? 'Circle reflects subjective witness estimation margin of error.'
                    : 'Pinpoint confirms exact lens coordinates with sub-20m certainty.'}
                </div>
              </div>

              {/* Point Meta */}
              <div className="space-y-1.5 text-[11px]">
                <div><span className="text-text-muted">Location:</span> <span className="font-medium text-slate-800">{selectedPoint.location_name}</span></div>
                <div><span className="text-text-muted">Entity:</span> <span className="font-medium text-slate-800">{selectedPoint.suspect_or_entity}</span></div>
                <div><span className="text-text-muted">Event Time:</span> <span className="font-mono text-slate-800">{formatTime(new Date(selectedPoint.timestamp).getTime())}</span></div>
                {selectedPoint.time_uncertainty_minutes > 0 && (
                  <div className="text-amber-700 bg-amber-50 p-1.5 rounded border border-amber-200">
                    ⚠️ Temporal Uncertainty: ±{selectedPoint.time_uncertainty_minutes} min window
                  </div>
                )}
                <div><span className="text-text-muted">Confidence:</span> <span className="font-semibold text-emerald-700">{selectedPoint.confidence}%</span></div>
              </div>
            </div>

            <div className="pt-3 border-t flex justify-end">
              <Link
                to={`/cases/${caseId}/evidence`}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-hover transition-colors shadow-sm"
              >
                Open Exhibit File <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </div>
        )}

        {/* Impossible Travel Inspector Drawer */}
        {selectedAnomaly && (
          <div className="absolute top-0 right-0 bottom-0 w-96 bg-white shadow-2xl border-l border-red-200 z-[500] flex flex-col p-4 animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between border-b border-red-100 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <h3 className="font-serif font-bold text-base text-red-950">Impossible Velocity Detection</h3>
              </div>
              <button
                onClick={() => setSelectedAnomaly(null)}
                className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 text-xs pr-1">
              <div className="bg-red-50 p-3 rounded-lg border border-red-200 space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-red-700">Calculated Teleportation Velocity</div>
                <div className="text-2xl font-mono font-bold text-red-700">
                  {selectedAnomaly.calculated_speed_kmh} <span className="text-sm">km/h</span>
                </div>
                <div className="text-[11px] text-red-900 font-medium">
                  Statutory Threshold: {selectedAnomaly.threshold_speed_kmh} km/h (Road Transit Physics Ceiling)
                </div>
              </div>

              {/* Route Breakdown */}
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Origin & Destination Hits</div>
                <div className="text-[11px] space-y-1">
                  <div className="flex items-start gap-1.5">
                    <span className="text-red-600 font-bold">A:</span>
                    <div>
                      <div className="font-semibold text-slate-800">{selectedAnomaly.from_location}</div>
                      <div className="font-mono text-[10px] text-text-muted">{formatTime(new Date(selectedAnomaly.from_time).getTime())}</div>
                      <div className="text-[10px] text-slate-500">{selectedAnomaly.source_a}</div>
                    </div>
                  </div>
                  <div className="w-full h-px bg-slate-200 my-1"></div>
                  <div className="flex items-start gap-1.5">
                    <span className="text-red-600 font-bold">B:</span>
                    <div>
                      <div className="font-semibold text-slate-800">{selectedAnomaly.to_location}</div>
                      <div className="font-mono text-[10px] text-text-muted">{formatTime(new Date(selectedAnomaly.to_time).getTime())}</div>
                      <div className="text-[10px] text-slate-500">{selectedAnomaly.source_b}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Physical Parameters */}
              <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span className="text-text-muted">Geodesic Distance:</span>
                  <div className="font-bold text-slate-800">{selectedAnomaly.distance_km} km</div>
                </div>
                <div>
                  <span className="text-text-muted">Elapsed Time:</span>
                  <div className="font-bold text-slate-800">{selectedAnomaly.time_delta_minutes} minutes</div>
                </div>
              </div>

              {/* Forensic Reasoning */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted block mb-1">
                  Forensic & Investigative Assessment:
                </label>
                <div className="bg-amber-50 border-l-4 border-amber-500 p-2.5 rounded-r-lg text-slate-800 leading-relaxed text-[11px]">
                  {selectedAnomaly.reasoning}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Replay Scrubber Controller ("Play the case from 8 PM to 6 AM") */}
      <Card className="p-3 bg-white border border-border shadow-md">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          {/* Play / Step Buttons & Speed Control */}
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
              {formatTime(timeMin)}
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
              {formatTime(timeMax)}
            </span>
          </div>

          {/* Current Scrubber Timestamp Readout */}
          <div className="px-3 py-1 bg-emerald-50 border border-emerald-200 text-emerald-800 font-mono text-xs font-bold rounded-xl shadow-xs whitespace-nowrap flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span>{formatTime(currentReplayTime)}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
