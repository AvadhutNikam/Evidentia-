import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import {
  ZoomIn, ZoomOut, Maximize2, X, Eye, EyeOff,
  User, Building2, MapPin, Car, Zap, FileText, Clock, Lightbulb,
  Video, Mic, Image as ImageIcon,
  Download, RotateCcw, Maximize, Minimize,
  Play, Pause, SkipForward, SkipBack, Plus, Columns, LayoutGrid, StickyNote, Calendar, Info
} from 'lucide-react';
import { 
  computeStructuredWhiteboardLayout, 
  getInvestigationStages, 
  ColumnHeader, 
  InvestigationStage 
} from './whiteboardUtils';
import html2canvas from 'html2canvas-pro';
import type { InvestigationNode, InvestigationEdge, Entity, Evidence, TimelineEvent, Hypothesis } from '../../types';
import { computeForceLayout } from '../../hooks/useForceLayout';
import { cn } from '../../utils';

// ============================================================
// Constants
// ============================================================

const BOARD_W = 5000;
const BOARD_H = 3500;
const CARD_W = 260;

const CARD_HEIGHTS: Record<string, number> = {
  Person: 190,
  Organization: 155,
  Location: 160,
  Vehicle: 130,
  Event: 130,
  Other: 130,
  Evidence: 215,
  TimelineEvent: 240,
  Hypothesis: 220,
};

const TYPE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  Person:         { bg: 'rgba(96,165,250,0.12)',  text: '#60a5fa', label: 'PERSON' },
  Organization:   { bg: 'rgba(192,132,252,0.12)', text: '#c084fc', label: 'ORGANIZATION' },
  Location:       { bg: 'rgba(74,222,128,0.12)',  text: '#4ade80', label: 'LOCATION' },
  Vehicle:        { bg: 'rgba(250,204,21,0.12)',  text: '#facc15', label: 'VEHICLE' },
  Event:          { bg: 'rgba(248,113,113,0.12)', text: '#f87171', label: 'EVENT' },
  Other:          { bg: 'rgba(148,163,184,0.12)', text: '#94a3b8', label: 'OTHER' },
  Evidence:       { bg: 'rgba(148,163,184,0.10)', text: '#94a3b8', label: 'EVIDENCE' },
  TimelineEvent:  { bg: 'rgba(234,179,8,0.14)',   text: '#a16207', label: 'TIMELINE' },
  Hypothesis:     { bg: 'rgba(251,146,60,0.14)',  text: '#fb923c', label: 'HYPOTHESIS' },
};

const CARD_BG: Record<string, string> = {
  Person: '#faf8f0',
  Organization: '#f5f7fa',
  Location: '#f0f5f0',
  Vehicle: '#faf5e8',
  Event: '#faf0f0',
  Other: '#fefce8',
  Evidence: '#ffffff',
  TimelineEvent: '#fef9c3',
  Hypothesis: '#faf0e5',
};

const ACCENT: Record<string, string> = {
  Person: '#3b82f6', Organization: '#a855f7', Location: '#22c55e',
  Vehicle: '#eab308', Event: '#ef4444', Other: '#94a3b8',
  Evidence: '#64748b', TimelineEvent: '#ca8a04', Hypothesis: '#f97316',
};

const STRING_COLOR = '#8b1a1a';
const STRING_HIGHLIGHT = '#cc2222';

const ALL_NODE_TYPES: string[] = [
  'Person', 'Organization', 'Location', 'Vehicle',
  'Event', 'Other', 'Evidence', 'TimelineEvent', 'Hypothesis',
];

// ============================================================
// Helpers
// ============================================================

function stableRotation(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0;
  }
  return ((hash % 300) / 100) - 1.5;
}

function pinPoint(nodeType: string, center: { x: number; y: number }) {
  const hh = (CARD_HEIGHTS[nodeType] ?? 150) / 2;
  return { x: center.x, y: center.y - hh + 10 };
}

function stringPath(
  p1: { x: number; y: number },
  p2: { x: number; y: number },
): string {
  const dx = Math.abs(p2.x - p1.x);
  const dy = Math.abs(p2.y - p1.y);
  const dist = Math.sqrt(dx * dx + dy * dy);
  const sag = Math.min(dist * 0.1, 50) + 12;
  const cx = (p1.x + p2.x) / 2;
  const cy = Math.max(p1.y, p2.y) + sag;
  return `M ${p1.x} ${p1.y} Q ${cx} ${cy} ${p2.x} ${p2.y}`;
}

function fileTypeIcon(type: string) {
  switch (type) {
    case 'Video': return <Video className="w-3.5 h-3.5" />;
    case 'Audio': return <Mic className="w-3.5 h-3.5" />;
    case 'Image': return <ImageIcon className="w-3.5 h-3.5" />;
    default: return <FileText className="w-3.5 h-3.5" />;
  }
}

function typeIcon(nodeType: string) {
  switch (nodeType) {
    case 'Person': return <User className="w-3.5 h-3.5" />;
    case 'Organization': return <Building2 className="w-3.5 h-3.5" />;
    case 'Location': return <MapPin className="w-3.5 h-3.5" />;
    case 'Vehicle': return <Car className="w-3.5 h-3.5" />;
    case 'Event': return <Zap className="w-3.5 h-3.5" />;
    case 'Evidence': return <FileText className="w-3.5 h-3.5" />;
    case 'TimelineEvent': return <Clock className="w-3.5 h-3.5" />;
    case 'Hypothesis': return <Lightbulb className="w-3.5 h-3.5" />;
    default: return <FileText className="w-3.5 h-3.5" />;
  }
}

// ============================================================
// Types
// ============================================================

interface Transform {
  x: number;
  y: number;
  scale: number;
}

interface BoardPersistedState {
  positions: Record<string, { x: number; y: number }>;
  zOrder: Record<string, number>;
  viewport: Transform;
  visibleTypes: string[];
  showConnections: boolean;
}

interface InvestigationBoardProps {
  nodes: InvestigationNode[];
  edges: InvestigationEdge[];
  entities?: Entity[];
  evidenceItems?: Evidence[];
  timelineEvents?: TimelineEvent[];
  hypotheses?: Hypothesis[];
  caseId?: string;
  caseName?: string;
}

// ============================================================
// Main Component
// ============================================================

export function InvestigationBoard({
  nodes: allNodes,
  edges: allEdges,
  entities = [],
  evidenceItems = [],
  timelineEvents = [],
  hypotheses = [],
  caseId = '',
  caseName = '',
}: InvestigationBoardProps) {
  // ---- Refs ----
  const containerRef = useRef<HTMLDivElement>(null);
  const fullscreenRef = useRef<HTMLDivElement>(null);
  const transformRef = useRef<Transform>({ x: 0, y: 0, scale: 1 });
  const positionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const nodesRef = useRef(allNodes);
  const nextZRef = useRef(100);
  const wheelSaveTimerRef = useRef(0);

  // ---- State ----
  const [size, setSize] = useState({ width: 900, height: 600 });
  const [transform, setTransform] = useState<Transform>({ x: 0, y: 0, scale: 1 });
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(new Set(ALL_NODE_TYPES));
  const [showConnections, setShowConnections] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(new Map());
  const [zOrder, setZOrder] = useState<Map<string, number>>(new Map());
  const [isExporting, setIsExporting] = useState(false);

  // ---- Whiteboard Layout & Investigation Stages ----
  const [layoutMode, setLayoutMode] = useState<'structured' | 'freeform'>('structured');
  const [columnHeaders, setColumnHeaders] = useState<ColumnHeader[]>([]);
  const [customNodes, setCustomNodes] = useState<InvestigationNode[]>([]);
  const [customEdges, setCustomEdges] = useState<InvestigationEdge[]>([]);
  const [customNotesData, setCustomNotesData] = useState<Map<string, { title: string; content: string; color: string }>>(new Map());

  // Merge default + custom notes
  const combinedAllNodes = useMemo(() => [...allNodes, ...customNodes], [allNodes, customNodes]);
  const combinedAllEdges = useMemo(() => [...allEdges, ...customEdges], [allEdges, customEdges]);

  // Investigation progression stages (time-to-time)
  const stages = useMemo(() => getInvestigationStages(caseId, combinedAllNodes), [caseId, combinedAllNodes]);
  const [activeStageId, setActiveStageId] = useState(0); // 0 = Full Case Solved
  const [isPlaying, setIsPlaying] = useState(false);

  // Modal for Adding Notes / Leads
  const [showAddNoteModal, setShowAddNoteModal] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNoteColor, setNewNoteColor] = useState('#fef9c3'); // yellow sticky
  const [newNoteConnectTo, setNewNoteConnectTo] = useState('');

  // Auto-play timer for investigation progression
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setActiveStageId(prev => {
        if (prev >= stages.length - 1) {
          setIsPlaying(false);
          return 0; // return to full
        }
        return prev + 1;
      });
    }, 2800);
    return () => clearInterval(timer);
  }, [isPlaying, stages.length]);

  const currentStage = stages.find(s => s.id === activeStageId) || stages[0];
  const stageNodeIds = useMemo(() => new Set(currentStage.nodeIds), [currentStage]);

  // Keep refs in sync
  useEffect(() => { transformRef.current = transform; }, [transform]);
  useEffect(() => { positionsRef.current = positions; }, [positions]);
  useEffect(() => { nodesRef.current = allNodes; }, [allNodes]);

  // ---- localStorage helpers ----
  const storageKey = `evidentia_whiteboard_v2_${caseId}`;

  const loadState = useCallback((): BoardPersistedState | null => {
    if (!caseId) return null;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return null;
      return JSON.parse(raw) as BoardPersistedState;
    } catch {
      return null;
    }
  }, [caseId, storageKey]);

  const saveState = useCallback((partial: Partial<BoardPersistedState>) => {
    if (!caseId) return;
    try {
      const raw = localStorage.getItem(storageKey);
      const existing = raw ? (JSON.parse(raw) as BoardPersistedState) : {} as BoardPersistedState;
      const merged = { ...existing, ...partial };
      localStorage.setItem(storageKey, JSON.stringify(merged));
    } catch { /* localStorage full or unavailable */ }
  }, [caseId, storageKey]);

  // ---- Resize observer (on fullscreen wrapper) ----
  useEffect(() => {
    const el = fullscreenRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setSize({ width: Math.floor(width), height: Math.floor(height) });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ---- Filter nodes & edges (supports progressive timeline stages) ----
  const { nodes, edges } = useMemo(() => {
    let stageFiltered = combinedAllNodes;
    if (activeStageId > 0) {
      stageFiltered = combinedAllNodes.filter(n => stageNodeIds.has(n.id));
    }
    const filteredNodes = stageFiltered.filter(n => visibleTypes.has(n.type));
    const nodeSet = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = combinedAllEdges.filter(e => nodeSet.has(e.source) && nodeSet.has(e.target));
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [combinedAllNodes, combinedAllEdges, visibleTypes, activeStageId, stageNodeIds]);

  // ---- Initial layout: only compute once per data load, never override manual positions ----
  useEffect(() => {
    if (allNodes.length === 0) {
      setPositions(new Map());
      return;
    }

    // Try to restore from localStorage (case-specific)
    const saved = loadState();
    if (saved?.positions) {
      const savedMap = new Map(Object.entries(saved.positions));
      const allPresent = allNodes.every(n => savedMap.has(n.id));
      if (allPresent) {
        setPositions(savedMap);
        if (saved.viewport) setTransform(saved.viewport);
        if (saved.zOrder) {
          const zMap = new Map(Object.entries(saved.zOrder).map(([k, v]) => [k, Number(v)]));
          setZOrder(zMap);
          let maxZ = 100;
          zMap.forEach(v => { if (v > maxZ) maxZ = v; });
          nextZRef.current = maxZ + 1;
        }
        if (saved.visibleTypes) setVisibleTypes(new Set(saved.visibleTypes));
        if (saved.showConnections !== undefined) setShowConnections(saved.showConnections);
        return; // Positions restored — do NOT recompute layout
      }
    }

    // Initial layout: Use Structured Crime Whiteboard columns
    const { positions: structuredPos, columnHeaders: headers } = computeStructuredWhiteboardLayout(
      combinedAllNodes,
      timelineEvents,
      entities,
      evidenceItems,
      hypotheses
    );
    setPositions(structuredPos);
    setColumnHeaders(headers);
    const computed = structuredPos;

    // Auto-fit to show all cards
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [id, p] of computed) {
      const nt = allNodes.find(n => n.id === id)?.type ?? 'Other';
      const hw = CARD_W / 2 + 30;
      const hh = (CARD_HEIGHTS[nt] ?? 150) / 2 + 40;
      if (p.x - hw < minX) minX = p.x - hw;
      if (p.y - hh < minY) minY = p.y - hh;
      if (p.x + hw > maxX) maxX = p.x + hw;
      if (p.y + hh > maxY) maxY = p.y + hh;
    }
    if (!isFinite(minX)) return;

    const pad = 60;
    const gw = maxX - minX + pad * 2;
    const gh = maxY - minY + pad * 2;
    const sx = size.width / gw;
    const sy = size.height / gh;
    const s = Math.min(sx, sy, 1.2);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const initialTransform = { x: size.width / 2 - cx * s, y: size.height / 2 - cy * s, scale: s };
    setTransform(initialTransform);

    // Save initial layout as persisted state
    const posObj: Record<string, { x: number; y: number }> = {};
    computed.forEach((p, id) => { posObj[id] = p; });
    saveState({
      positions: posObj,
      viewport: initialTransform,
      visibleTypes: [...ALL_NODE_TYPES],
      showConnections: true,
      zOrder: {},
    });
  // Only re-run when the underlying data changes (new case loaded)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allNodes, allEdges]);

  // ---- Helpers ----
  const screenToBoard = useCallback((screenX: number, screenY: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    const t = transformRef.current;
    return {
      x: (screenX - rect.left - t.x) / t.scale,
      y: (screenY - rect.top - t.y) / t.scale,
    };
  }, []);

  const fitToView = useCallback(() => {
    const pos = positionsRef.current;
    if (pos.size === 0) return;
    const currentNodes = nodesRef.current;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [id, p] of pos) {
      const nt = currentNodes.find(n => n.id === id)?.type ?? 'Other';
      const hw = CARD_W / 2 + 30;
      const hh = (CARD_HEIGHTS[nt] ?? 150) / 2 + 40;
      if (p.x - hw < minX) minX = p.x - hw;
      if (p.y - hh < minY) minY = p.y - hh;
      if (p.x + hw > maxX) maxX = p.x + hw;
      if (p.y + hh > maxY) maxY = p.y + hh;
    }
    if (!isFinite(minX)) return;
    const pad = 60;
    const gw = maxX - minX + pad * 2;
    const gh = maxY - minY + pad * 2;
    const sx = size.width / gw;
    const sy = size.height / gh;
    const s = Math.min(sx, sy, 1.2);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const newTransform = { x: size.width / 2 - cx * s, y: size.height / 2 - cy * s, scale: s };
    setTransform(newTransform);
    saveState({ viewport: newTransform });
  }, [size, saveState]);

  // ---- Non-passive wheel handler ----
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const t = transformRef.current;
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
      const newScale = Math.max(0.15, Math.min(4, t.scale * zoomFactor));
      const ratio = newScale / t.scale;
      const newTransform: Transform = {
        x: mouseX - (mouseX - t.x) * ratio,
        y: mouseY - (mouseY - t.y) * ratio,
        scale: newScale,
      };
      setTransform(newTransform);
      // Debounced viewport save
      clearTimeout(wheelSaveTimerRef.current);
      wheelSaveTimerRef.current = window.setTimeout(() => {
        saveState({ viewport: newTransform });
      }, 500);
    };
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [saveState]);

  // ---- Panning ----
  const handleMouseDownBackground = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setSelectedNode(null);
    const startX = e.clientX - transformRef.current.x;
    const startY = e.clientY - transformRef.current.y;
    let currentT: Transform = { ...transformRef.current };

    const handleMove = (ev: MouseEvent) => {
      currentT = { ...currentT, x: ev.clientX - startX, y: ev.clientY - startY };
      setTransform(currentT);
    };
    const handleUp = () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
      saveState({ viewport: currentT });
    };
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
  }, [saveState]);

  // ---- Card dragging ----
  const handleCardMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    if (e.button !== 0) return;
    setSelectedNode(nodeId);
    setIsDragging(true);

    // Bring to front
    nextZRef.current += 1;
    const newZ = nextZRef.current;
    setZOrder(prev => new Map(prev).set(nodeId, newZ));

    const handleMove = (ev: MouseEvent) => {
      const gp = screenToBoard(ev.clientX, ev.clientY);
      setPositions(prev => new Map(prev).set(nodeId, gp));
    };
    const handleUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
      // Persist final positions + z-order + viewport on drag end
      const posObj: Record<string, { x: number; y: number }> = {};
      positionsRef.current.forEach((p, id) => { posObj[id] = p; });
      saveState({
        positions: posObj,
        viewport: transformRef.current,
      });
      // Persist z-order
      setZOrder(currentZ => {
        const zObj: Record<string, number> = {};
        currentZ.forEach((v, k) => { zObj[k] = v; });
        zObj[nodeId] = newZ;
        try {
          const raw = localStorage.getItem(storageKey);
          const existing = raw ? (JSON.parse(raw) as BoardPersistedState) : {} as BoardPersistedState;
          localStorage.setItem(storageKey, JSON.stringify({ ...existing, zOrder: zObj }));
        } catch { /* ignore */ }
        return currentZ; // no re-render needed
      });
    };
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
  }, [screenToBoard, saveState, storageKey]);

  // ---- Fullscreen ----
  useEffect(() => {
    const handleFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handleFsChange);
    return () => document.removeEventListener('fullscreenchange', handleFsChange);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const el = fullscreenRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      el.requestFullscreen().catch(() => { /* might be blocked by browser */ });
    }
  }, []);

  // ---- Export as PNG ----
  const exportBoard = useCallback(async () => {
    const frame = containerRef.current;
    if (!frame) return;
    const surface = frame.querySelector('.board-surface') as HTMLElement;
    if (!surface) return;

    setIsExporting(true);

    // Save current visual state
    const savedSurfaceTransform = surface.style.transform;
    const savedFrameStyle = {
      overflow: frame.style.overflow,
      width: frame.style.width,
      height: frame.style.height,
 };

    try {
      // Compute bounds of all cards
      const pos = positionsRef.current;
      const currentNodes = nodesRef.current;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      pos.forEach((p, id) => {
        const node = currentNodes.find(n => n.id === id);
        const hh = node ? (CARD_HEIGHTS[node.type] ?? 150) / 2 : 75;
        const hw = CARD_W / 2;
        if (p.x - hw < minX) minX = p.x - hw;
        if (p.y - hh - 12 < minY) minY = p.y - hh - 12;
        if (p.x + hw > maxX) maxX = p.x + hw;
        if (p.y + hh > maxY) maxY = p.y + hh;
      });
      if (!isFinite(minX)) return;

      const pad = 80;
      const contentW = maxX - minX + pad * 2;
      const contentH = maxY - minY + pad * 2;
      const framePad = 22;

      // Set up for full capture
      surface.style.transform = `translate(${-minX + pad + 10}px, ${-minY + pad + 10}px) scale(1)`;
      frame.style.overflow = 'visible';
      frame.style.width = (contentW + framePad) + 'px';
      frame.style.height = (contentH + framePad) + 'px';

      // Wait for DOM update
      await new Promise(r => setTimeout(r, 100));

      // Capture
      const canvas = await html2canvas(frame, {
        backgroundColor: '#3d2b1f',
        scale: 2,
        logging: false,
        useCORS: true,
      });

      // Download with sanitized filename
      const link = document.createElement('a');
      const safeName = (caseName || 'Unknown').replace(/[^a-zA-Z0-9_-]/g, '_');
      link.download = `Evidentia_Case_${safeName}_Investigation_Board.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } finally {
      // Restore visual state
      surface.style.transform = savedSurfaceTransform;
      frame.style.overflow = savedFrameStyle.overflow;
      frame.style.width = savedFrameStyle.width;
      frame.style.height = savedFrameStyle.height;
      setIsExporting(false);
    }
  }, [caseName]);

  // ---- Reset Layout (defaults to clean non-overlapping whiteboard columns) ----
  const resetLayout = useCallback(() => {
    // Clear saved state
    if (caseId) {
      try { localStorage.removeItem(storageKey); } catch { /* ignore */ }
    }

    if (combinedAllNodes.length === 0) return;

    let computed: Map<string, { x: number; y: number }>;
    if (layoutMode === 'structured') {
      const res = computeStructuredWhiteboardLayout(
        combinedAllNodes,
        timelineEvents,
        entities,
        evidenceItems,
        hypotheses
      );
      computed = res.positions;
      setColumnHeaders(res.columnHeaders);
    } else {
      computed = computeForceLayout(combinedAllNodes, combinedAllEdges, BOARD_W, BOARD_H);
      setColumnHeaders([]);
    }

    setPositions(computed);
    setZOrder(new Map());
    nextZRef.current = 100;

    // Auto-fit to view with comfortable margins
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [id, p] of computed) {
      const nt = combinedAllNodes.find(n => n.id === id)?.type ?? 'Other';
      const hw = CARD_W / 2 + 30;
      const hh = (CARD_HEIGHTS[nt] ?? 150) / 2 + 40;
      if (p.x - hw < minX) minX = p.x - hw;
      if (p.y - hh < minY) minY = p.y - hh;
      if (p.x + hw > maxX) maxX = p.x + hw;
      if (p.y + hh > maxY) maxY = p.y + hh;
    }
    if (!isFinite(minX)) return;
    const pad = 80;
    const gw = maxX - minX + pad * 2;
    const gh = maxY - minY + pad * 2;
    const s = Math.min(size.width / gw, size.height / gh, 0.95);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const newTransform = { x: size.width / 2 - cx * s, y: size.height / 2 - cy * s, scale: s };
    setTransform(newTransform);

    // Save as new initial state
    const posObj: Record<string, { x: number; y: number }> = {};
    computed.forEach((p, id) => { posObj[id] = p; });
    saveState({
      positions: posObj,
      viewport: newTransform,
      visibleTypes: [...ALL_NODE_TYPES],
      showConnections: true,
      zOrder: {},
    });
  }, [combinedAllNodes, combinedAllEdges, timelineEvents, entities, evidenceItems, hypotheses, layoutMode, caseId, storageKey, size, saveState]);

  // ---- Connected node/edge sets ----
  const { connectedNodes, connectedEdges } = useMemo(() => {
    if (!selectedNode) return { connectedNodes: new Set<string>(), connectedEdges: new Set<string>() };
    const cn = new Set<string>([selectedNode]);
    const ce = new Set<string>();
    for (const edge of edges) {
      if (edge.source === selectedNode || edge.target === selectedNode) {
        cn.add(edge.source);
        cn.add(edge.target);
        ce.add(edge.id);
      }
    }
    return { connectedNodes: cn, connectedEdges: ce };
  }, [selectedNode, edges]);

  // ---- Detail panel data ----
  const detailNode = useMemo(() => {
    if (!selectedNode) return null;
    return allNodes.find(n => n.id === selectedNode) ?? null;
  }, [selectedNode, allNodes]);

  const detailEntity = detailNode ? entities.find(e => e.id === detailNode.id) : null;
  const detailEvidence = detailNode ? evidenceItems.find(e => e.id === detailNode.id) : null;
  const detailTimeline = detailNode ? timelineEvents.find(e => e.id === detailNode.id) : null;
  const detailHypothesis = detailNode ? hypotheses.find(h => h.id === detailNode.id) : null;

  const neighborNodes = useMemo(() => {
    if (!selectedNode) return [];
    return allNodes.filter(n => connectedNodes.has(n.id) && n.id !== selectedNode);
  }, [selectedNode, allNodes, connectedNodes]);

  // ---- Toggle type filter ----
  const toggleType = useCallback((type: string) => {
    setVisibleTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      saveState({ visibleTypes: [...next] });
      return next;
    });
  }, [saveState]);

  const toggleConnections = useCallback(() => {
    setShowConnections(prev => {
      const next = !prev;
      saveState({ showConnections: next });
      return next;
    });
  }, [saveState]);

  // ---- Precompute lookups for card content ----
  const entityMap = useMemo(() => {
    const m = new Map<string, Entity>();
    for (const e of entities) m.set(e.id, e);
    return m;
  }, [entities]);

  const evidenceMap = useMemo(() => {
    const m = new Map<string, Evidence>();
    for (const e of evidenceItems) m.set(e.id, e);
    return m;
  }, [evidenceItems]);

  const timelineMap = useMemo(() => {
    const m = new Map<string, TimelineEvent>();
    for (const t of timelineEvents) m.set(t.id, t);
    return m;
  }, [timelineEvents]);

  const hypothesisMap = useMemo(() => {
    const m = new Map<string, Hypothesis>();
    for (const h of hypotheses) m.set(h.id, h);
    return m;
  }, [hypotheses]);

  // ---- Compute string SVG paths ----
  const stringPaths = useMemo(() => {
    if (!showConnections) return [];
    return edges.map(edge => {
      const p1 = positions.get(edge.source);
      const p2 = positions.get(edge.target);
      if (!p1 || !p2) return null;
      const srcType = nodes.find(n => n.id === edge.source)?.type ?? 'Other';
      const tgtType = nodes.find(n => n.id === edge.target)?.type ?? 'Other';
      const pp1 = pinPoint(srcType, p1);
      const pp2 = pinPoint(tgtType, p2);
      return {
        edge,
        path: stringPath(pp1, pp2),
        mid: { x: (pp1.x + pp2.x) / 2, y: (pp1.y + pp2.y) / 2 + 6 },
      };
    }).filter(Boolean) as { edge: InvestigationEdge; path: string; mid: { x: number; y: number } }[];
  }, [edges, positions, nodes, showConnections]);

  // ============================================================
  // Render
  // ============================================================

  const zoomPercent = Math.round(transform.scale * 100);

  return (
    <div ref={fullscreenRef} className="h-full flex flex-col gap-3 board-fullscreen-wrapper">
      {/* ---- Investigation Progression & Time-to-Time Evolution Controller ---- */}
      <div className="flex flex-col gap-2 p-3 bg-surface rounded-xl border border-border shadow-xs">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-text font-mono flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-primary" /> Case Progression:
            </span>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition-colors shadow-xs cursor-pointer"
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {isPlaying ? 'Pause' : 'Play Timeline'}
            </button>
            <button
              onClick={() => { setActiveStageId(p => Math.max(0, p - 1)); setIsPlaying(false); }}
              disabled={activeStageId <= 0}
              className="p-1.5 rounded-md hover:bg-surface-hover border border-border text-text disabled:opacity-40 cursor-pointer"
              title="Previous Stage"
            >
              <SkipBack className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => { setActiveStageId(p => Math.min(stages.length - 1, p + 1)); setIsPlaying(false); }}
              disabled={activeStageId >= stages.length - 1}
              className="p-1.5 rounded-md hover:bg-surface-hover border border-border text-text disabled:opacity-40 cursor-pointer"
              title="Next Stage"
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Stage selector buttons */}
          <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 max-w-full">
            {stages.map(stg => (
              <button
                key={stg.id}
                onClick={() => { setActiveStageId(stg.id); setIsPlaying(false); }}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-medium shrink-0 transition-all border cursor-pointer",
                  activeStageId === stg.id 
                    ? "bg-primary text-white border-primary shadow-xs font-bold" 
                    : "bg-surface-hover/60 hover:bg-surface-hover text-text-muted border-border"
                )}
              >
                {stg.label} <span className="opacity-75 text-[10px]">({stg.dateStr})</span>
              </button>
            ))}
          </div>

          {/* Whiteboard layout switcher and Add Clue button */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const next = layoutMode === 'structured' ? 'freeform' : 'structured';
                setLayoutMode(next);
                if (next === 'structured') {
                  resetLayout();
                } else {
                  const f = computeForceLayout(combinedAllNodes, combinedAllEdges, BOARD_W, BOARD_H);
                  setPositions(f);
                  setColumnHeaders([]);
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-text text-xs font-semibold transition-colors cursor-pointer"
            >
              {layoutMode === 'structured' ? <Columns className="w-3.5 h-3.5 text-primary" /> : <LayoutGrid className="w-3.5 h-3.5 text-secondary" />}
              {layoutMode === 'structured' ? 'Whiteboard Columns' : 'Freeform Canvas'}
            </button>

            <button
              onClick={() => setShowAddNoteModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-border hover:bg-surface-hover text-text text-xs font-semibold transition-colors shadow-xs cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-primary" />
              Pin Clue / Note
            </button>
          </div>
        </div>

        {/* Active Stage Briefing Banner */}
        <div className="px-3.5 py-2 bg-surface-hover/70 rounded-lg border border-border/80 flex items-center justify-between text-xs gap-3">
          <div className="flex items-center gap-2 overflow-hidden">
            <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-primary/10 text-primary border border-primary/20 shrink-0">
              {currentStage.dateStr}
            </span>
            <span className="font-bold text-text shrink-0">{currentStage.title}:</span>
            <span className="text-text-muted truncate">{currentStage.description}</span>
          </div>
          <span className="text-text-muted text-[11px] shrink-0 font-mono">
            Showing {nodes.length} cards / {edges.length} red strings
          </span>
        </div>
      </div>

      {/* ---- Toolbar ---- */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1.5 flex-wrap">
          {ALL_NODE_TYPES.map(type => {
            const active = visibleTypes.has(type);
            const count = allNodes.filter(n => n.type === type).length;
            if (count === 0) return null;
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all',
                  active
                    ? 'border-border bg-surface text-text'
                    : 'border-transparent bg-surface-hover/30 text-text-muted opacity-50',
                )}
              >
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ background: ACCENT[type], opacity: active ? 1 : 0.3 }}
                />
                <span className="text-[#191410] font-semibold">{type}</span>
                <span className="text-text-muted font-mono">({count})</span>
              </button>
            );
          })}
          <div className="w-px h-5 bg-border mx-1" />
          <button
            onClick={toggleConnections}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all',
              showConnections ? 'border-border bg-surface text-text' : 'border-transparent bg-surface-hover/30 text-text-muted opacity-50',
            )}
            title={showConnections ? 'Hide connections' : 'Show connections'}
          >
            {showConnections ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            Strings
          </button>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[11px] text-text-muted mr-1">
            {nodes.length} items / {edges.length} links
          </span>

          {/* Zoom out */}
          <button
            onClick={() => setTransform(p => ({ ...p, scale: Math.max(p.scale * 0.8, 0.15) }))}
            className="p-1.5 hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors"
            title="Zoom out"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>

          {/* Zoom percentage */}
          <span className="text-[11px] text-text-muted w-10 text-center font-mono select-none">
            {zoomPercent}%
          </span>

          {/* Zoom in */}
          <button
            onClick={() => setTransform(p => ({ ...p, scale: Math.min(p.scale * 1.25, 4) }))}
            className="p-1.5 hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors"
            title="Zoom in"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>

          <div className="w-px h-4 bg-border mx-0.5" />

          {/* Fit to view */}
          <button
            onClick={fitToView}
            className="p-1.5 hover:bg-surface-hover rounded text-primary transition-colors"
            title="Fit to view"
            aria-label="Fit to view"
          >
            <Maximize2 className="w-4 h-4" />
          </button>

          {/* Reset layout */}
          <button
            onClick={resetLayout}
            className="p-1.5 hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors"
            title="Reset layout"
            aria-label="Reset layout"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <div className="w-px h-4 bg-border mx-0.5" />

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="p-1.5 hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
          </button>

          {/* Download / Export */}
          <button
            onClick={exportBoard}
            disabled={isExporting}
            className={cn(
              'p-1.5 rounded transition-colors',
              isExporting
                ? 'text-text-muted opacity-50 cursor-wait'
                : 'hover:bg-surface-hover text-text-muted hover:text-white',
            )}
            title="Download board as PNG"
            aria-label="Download board as PNG"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ---- Board + Detail Panel ---- */}
      <div className="flex-1 flex gap-3 min-h-0">
        {/* Board Container (wooden frame) */}
        <div
          ref={containerRef}
          className="flex-1 relative board-frame overflow-hidden rounded-xl"
          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
          onMouseDown={handleMouseDownBackground}
        >
          {nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <p className="text-sm text-text-muted">Select node types above to display the investigation board.</p>
            </div>
          ) : (
            <div
              className="board-surface"
              style={{
                transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
                transformOrigin: '0 0',
                width: BOARD_W,
                height: BOARD_H,
              }}
            >
              {/* Column Headers for Structured Whiteboard Layout */}
              {layoutMode === 'structured' && columnHeaders.map((col, idx) => (
                <div
                  key={idx}
                  style={{
                    position: 'absolute',
                    left: col.x - CARD_W / 2,
                    top: col.y - 65,
                    width: CARD_W,
                    zIndex: 2,
                  }}
                  className="flex flex-col items-center justify-center py-2 px-3 rounded-lg border border-dashed border-[#ded7cb] bg-[#fdfbf7]/95 shadow-xs pointer-events-none"
                >
                  <div className="text-[12px] font-bold uppercase tracking-wider font-mono flex items-center gap-1.5" style={{ color: col.color }}>
                    <span>{col.title}</span>
                  </div>
                  <div className="text-[10px] text-text-muted mt-0.5 text-center">{col.subtitle}</div>
                </div>
              ))}

              {/* SVG layer for investigation strings (behind cards) */}
              <svg
                className="absolute inset-0 pointer-events-none"
                style={{ width: BOARD_W, height: BOARD_H, zIndex: 1 }}
              >
                {stringPaths.map(({ edge, path, mid }) => {
                  const isHighlighted = !selectedNode || connectedEdges.has(edge.id);
                  const isHovered = hoveredEdge === edge.id;
                  return (
                    <g key={edge.id}>
                      <path
                        d={path}
                        stroke="transparent"
                        strokeWidth={14}
                        fill="none"
                        style={{ cursor: 'pointer', pointerEvents: 'stroke' }}
                        onMouseEnter={() => setHoveredEdge(edge.id)}
                        onMouseLeave={() => setHoveredEdge(null)}
                      />
                      <path
                        d={path}
                        stroke={isHovered ? STRING_HIGHLIGHT : STRING_COLOR}
                        strokeWidth={isHovered ? 2 : 1.4}
                        strokeOpacity={isHighlighted ? (isHovered ? 0.85 : 0.5) : 0.06}
                        fill="none"
                        strokeLinecap="round"
                        pointerEvents="none"
                      />
                      {isHovered && (
                        <text
                          x={mid.x}
                          y={mid.y}
                          textAnchor="middle"
                          fill="#fff"
                          style={{ fontSize: 9, fontFamily: 'var(--font-sans)', pointerEvents: 'none', opacity: 0.85 }}
                        >
                          {edge.label}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>

              {/* Cards layer (above strings) */}
              <div style={{ position: 'relative', zIndex: 2 }}>
                {nodes.map(node => {
                  const pos = positions.get(node.id);
                  if (!pos) return null;
                  const isSelected = selectedNode === node.id;
                  const isConnected = !selectedNode || connectedNodes.has(node.id);
                  const isHovered = hoveredNode === node.id;
                  const rotation = stableRotation(node.id);
                  const cardH = CARD_HEIGHTS[node.type] ?? 150;
                  const accent = ACCENT[node.type] ?? '#94a3b8';
                  const bg = CARD_BG[node.type] ?? '#f5f5f5';
                  const badge = TYPE_BADGE[node.type] ?? TYPE_BADGE.Other;
                  const cardZ = zOrder.get(node.id) ?? 10;

                  return (
                    <div
                      key={node.id}
                      className={cn('board-card', isDragging && isSelected && 'board-card-dragging')}
                      style={{
                        position: 'absolute',
                        left: pos.x - CARD_W / 2,
                        top: pos.y - cardH / 2,
                        width: CARD_W,
                        transform: `rotate(${rotation}deg)`,
                        zIndex: cardZ,
                        opacity: isConnected ? 1 : 0.12,
                        transition: isDragging ? 'none' : 'opacity 0.25s',
                      }}
                      onMouseDown={(e) => handleCardMouseDown(e, node.id)}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                    >
                      {/* Red push pin (above card body) */}
                      <div className="board-pin" />

                      {/* Card body */}
                      <div
                        className={cn(
                          'board-card-inner',
                          isSelected && 'board-card-selected',
                          isHovered && !isSelected && 'board-card-hover',
                          node.type === 'TimelineEvent' && 'board-card-timeline',
                        )}
                        style={{ background: bg }}
                      >
                        {/* Accent top bar */}
                        <div className="board-card-accent" style={{ background: accent }} />

                        {/* Tape strip for timeline cards */}
                        {node.type === 'TimelineEvent' && <div className="board-tape" />}

                        {/* Card header */}
                        <div className="px-3.5 pt-2.5 pb-1 flex items-center gap-1.5">
                          <span
                            className="flex items-center justify-center w-5 h-5 rounded-sm shrink-0"
                            style={{ background: badge.bg, color: badge.text }}
                          >
                            {node.type === 'Evidence'
                              ? fileTypeIcon(evidenceMap.get(node.id)?.fileType ?? 'Document')
                              : typeIcon(node.type)}
                          </span>
                          <span
                            className="text-[9px] font-bold uppercase tracking-wider"
                            style={{ color: badge.text }}
                          >
                            {badge.label}
                          </span>
                        </div>

                        {/* Card content — type-specific */}
                        <div className="px-3.5 pb-3.5">
                          {/* ---- Person ---- */}
                          {node.type === 'Person' && (() => {
                            const ent = entityMap.get(node.id);
                            return (
                              <>
                                <div className="text-[14px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-1.5">{node.id}</div>
                                {ent && (
                                  <>
                                    {ent.aliases.length > 0 && (
                                      <div className="text-[10px] text-gray-500 mb-1.5">
                                        aka {ent.aliases.join(', ')}
                                      </div>
                                    )}
                                    <div className="flex items-center gap-1.5 mt-1">
                                      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                        <div
                                          className="h-full rounded-full"
                                          style={{ width: `${ent.confidence}%`, background: accent }}
                                        />
                                      </div>
                                      <span className="text-[9px] font-semibold text-gray-500">
                                        {ent.confidence}%
                                      </span>
                                    </div>
                                  </>
                                )}
                              </>
                            );
                          })()}

                          {/* ---- Organization ---- */}
                          {node.type === 'Organization' && (() => {
                            const ent = entityMap.get(node.id);
                            return (
                              <>
                                <div className="text-[14px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-1.5">{node.id}</div>
                                {ent && ent.aliases.length > 0 && (
                                  <div className="text-[10px] text-gray-500">
                                    aka {ent.aliases.join(', ')}
                                  </div>
                                )}
                              </>
                            );
                          })()}

                          {/* ---- Location ---- */}
                          {node.type === 'Location' && (() => {
                            const ent = entityMap.get(node.id);
                            return (
                              <>
                                <div className="text-[14px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-1.5">{node.id}</div>
                                {ent && ent.aliases.length > 0 && (
                                  <div className="text-[10px] text-gray-500">
                                    aka {ent.aliases.join(', ')}
                                  </div>
                                )}
                              </>
                            );
                          })()}

                          {/* ---- Vehicle ---- */}
                          {node.type === 'Vehicle' && (
                            <>
                              <div className="text-[14px] font-bold text-gray-800 leading-tight mb-0.5">
                                {node.label}
                              </div>
                              <div className="text-[9px] text-gray-400 font-mono">{node.id}</div>
                            </>
                          )}

                          {/* ---- Event ---- */}
                          {node.type === 'Event' && (
                            <>
                              <div className="text-[14px] font-bold text-gray-800 leading-tight mb-0.5">
                                {node.label}
                              </div>
                              <div className="text-[9px] text-gray-400 font-mono">{node.id}</div>
                            </>
                          )}

                          {/* ---- Other / Sticky Note ---- */}
                          {node.type === 'Other' && (() => {
                            const memo = customNotesData.get(node.id);
                            return (
                              <>
                                <div className="text-[14px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-1">{node.id}</div>
                                {memo ? (
                                  <p className="text-xs text-gray-700 leading-relaxed font-sans mt-1 p-2 rounded bg-amber-50/60 border border-amber-200/50">
                                    {memo.content}
                                  </p>
                                ) : (
                                  <div className="text-[10px] text-gray-500 italic mt-1">Investigative Lead / Field Note</div>
                                )}
                              </>
                            );
                          })()}

                          {/* ---- Evidence ---- */}
                          {node.type === 'Evidence' && (() => {
                            const ev = evidenceMap.get(node.id);
                            return (
                              <>
                                <div className="text-[13px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-2">{node.id}</div>
                                {ev && (
                                  <>
                                    <div className="flex items-center gap-1.5 mb-1.5">
                                      <span
                                        className="text-[9px] font-semibold px-1.5 py-0.5 rounded-sm"
                                        style={{ background: badge.bg, color: badge.text }}
                                      >
                                        {ev.fileType}
                                      </span>
                                      <span className="text-[9px] text-gray-500">
                                        {ev.processingStatus}
                                      </span>
                                    </div>
                                    <div className="text-[10px] text-gray-500 mb-0.5">
                                      {ev.source}
                                    </div>
                                    <div className="text-[9px] text-gray-400 mb-1.5">
                                      {ev.uploadDate ? new Date(ev.uploadDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : ''}
                                    </div>
                                    <div className="flex flex-wrap gap-1">
                                      {ev.tags.slice(0, 3).map(t => (
                                        <span
                                          key={t}
                                          className="text-[9px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded-sm"
                                        >
                                          {t}
                                        </span>
                                      ))}
                                      {ev.tags.length > 3 && (
                                        <span className="text-[9px] text-gray-400">
                                          +{ev.tags.length - 3}
                                        </span>
                                      )}
                                    </div>
                                  </>
                                )}
                              </>
                            );
                          })()}

                          {/* ---- TimelineEvent ---- */}
                          {node.type === 'TimelineEvent' && (() => {
                            const te = timelineMap.get(node.id);
                            return (
                              <>
                                <div className="text-[13px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-1.5">{node.id}</div>
                                {te && (
                                  <>
                                    <div className="text-[10px] text-gray-500 mb-0.5">
                                      {new Date(te.timestamp).toLocaleString('en-US', {
                                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                                      })}
                                    </div>
                                    <div className="text-[10px] text-gray-500 mb-1">
                                      {te.location}
                                    </div>
                                    <div className="text-[10px] text-gray-600 leading-snug line-clamp-2 mb-1.5">
                                      {te.description}
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                        <div
                                          className="h-full rounded-full"
                                          style={{ width: `${te.confidence}%`, background: accent }}
                                        />
                                      </div>
                                      <span className="text-[9px] font-semibold text-gray-500">
                                        {te.confidence}%
                                      </span>
                                    </div>
                                  </>
                                )}
                              </>
                            );
                          })()}

                          {/* ---- Hypothesis ---- */}
                          {node.type === 'Hypothesis' && (() => {
                            const h = hypothesisMap.get(node.id);
                            return (
                              <>
                                <div className="text-[13px] font-bold text-gray-800 leading-tight mb-0.5">
                                  {node.label}
                                </div>
                                <div className="text-[9px] text-gray-400 font-mono mb-1.5">{node.id}</div>
                                {h && (
                                  <>
                                    <span
                                      className="text-[9px] font-semibold px-1.5 py-0.5 rounded-sm"
                                      style={{
                                        background: h.status === 'Active' ? 'rgba(34,197,94,0.12)' : h.status === 'Discarded' ? 'rgba(239,68,68,0.12)' : 'rgba(59,130,246,0.12)',
                                        color: h.status === 'Active' ? '#16a34a' : h.status === 'Discarded' ? '#dc2626' : '#2563eb',
                                      }}
                                    >
                                      {h.status}
                                    </span>
                                    <div className="text-[10px] text-gray-500 leading-snug mt-1.5 mb-1.5 line-clamp-2">
                                      {h.description}
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                        <div
                                          className="h-full rounded-full"
                                          style={{ width: `${h.confidence}%`, background: accent }}
                                        />
                                      </div>
                                      <span className="text-[9px] font-semibold text-gray-500">{h.confidence}%</span>
                                    </div>
                                  </>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ---- Detail Panel ---- */}
        {selectedNode && detailNode && (
          <div className="w-72 shrink-0 glass-panel rounded-xl border border-border/50 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between bg-surface/50">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-3 h-3 rounded-sm shrink-0"
                  style={{ background: ACCENT[detailNode.type] }}
                />
                <span className="text-xs font-bold uppercase tracking-wider text-text-muted truncate">
                  {detailNode.type}
                </span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <h3 className="text-sm font-bold text-white leading-snug">{detailNode.label}</h3>

              {/* Entity-specific details */}
              {detailEntity && (
                <>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Confidence</div>
                    <div className="text-sm font-semibold text-white">{detailEntity.confidence}%</div>
                  </div>
                  {detailEntity.aliases.length > 0 && (
                    <div>
                      <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Aliases</div>
                      <div className="flex flex-wrap gap-1">
                        {detailEntity.aliases.map(a => (
                          <span key={a} className="px-2 py-0.5 bg-surface-hover rounded text-[10px] text-text border border-border">{a}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Source Evidence</div>
                    <div className="space-y-1">
                      {detailEntity.sourceEvidenceIds.map(eid => {
                        const ev = evidenceItems.find(e => e.id === eid);
                        return (
                          <div key={eid} className="text-xs text-text-muted font-mono truncate">
                            {ev ? ev.fileName : eid}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}

              {/* Evidence-specific details */}
              {detailEvidence && (
                <>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Type</div>
                    <div className="text-sm text-white">{detailEvidence.fileType}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Status</div>
                    <div className="text-sm text-white">{detailEvidence.processingStatus}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Source</div>
                    <div className="text-sm text-white">{detailEvidence.source}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Uploaded</div>
                    <div className="text-sm text-white">{detailEvidence.uploadDate ? new Date(detailEvidence.uploadDate).toLocaleString() : 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Tags</div>
                    <div className="flex flex-wrap gap-1">
                      {detailEvidence.tags.map(t => (
                        <span key={t} className="px-2 py-0.5 bg-surface-hover rounded text-[10px] text-text border border-border">{t}</span>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Timeline-specific details */}
              {detailTimeline && (
                <>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Timestamp</div>
                    <div className="text-sm text-white">{new Date(detailTimeline.timestamp).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Location</div>
                    <div className="text-sm text-white">{detailTimeline.location}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Confidence</div>
                    <div className="text-sm text-white">{detailTimeline.confidence}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-2">Description</div>
                    <p className="text-xs text-text-muted leading-relaxed">{detailTimeline.description}</p>
                  </div>
                </>
              )}

              {/* Hypothesis-specific details */}
              {detailHypothesis && (
                <>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Status</div>
                    <div className="text-sm text-white">{detailHypothesis.status}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-1">Confidence</div>
                    <div className="text-sm font-bold text-white">{detailHypothesis.confidence}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted uppercase font-bold mb-2">Description</div>
                    <p className="text-xs text-text-muted leading-relaxed">{detailHypothesis.description}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-green-500/10 rounded-lg p-2 text-center">
                      <div className="text-lg font-bold text-green-400">{detailHypothesis.supportingEvidenceIds.length}</div>
                      <div className="text-[9px] text-text-muted uppercase font-bold">Supporting</div>
                    </div>
                    <div className="bg-red-500/10 rounded-lg p-2 text-center">
                      <div className="text-lg font-bold text-red-400">{detailHypothesis.contradictingEvidenceIds.length}</div>
                      <div className="text-[9px] text-text-muted uppercase font-bold">Contradicting</div>
                    </div>
                  </div>
                </>
              )}

              {/* Connected nodes */}
              {neighborNodes.length > 0 && (
                <div>
                  <div className="text-[10px] text-text-muted uppercase font-bold mb-2">Connected To ({neighborNodes.length})</div>
                  <div className="space-y-1">
                    {neighborNodes.slice(0, 12).map(n => (
                      <button
                        key={n.id}
                        onClick={() => setSelectedNode(n.id)}
                        className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-hover transition-colors text-left"
                      >
                        <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: ACCENT[n.type] }} />
                        <span className="text-xs text-text truncate">{n.label}</span>
                      </button>
                    ))}
                    {neighborNodes.length > 12 && (
                      <div className="text-[10px] text-text-muted">+{neighborNodes.length - 12} more</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ---- Add Clue / Note Modal ---- */}
      {showAddNoteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-surface border border-border rounded-xl shadow-2xl max-w-md w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-bold text-lg text-text flex items-center gap-2">
                <StickyNote className="w-5 h-5 text-primary" />
                Pin Clue / Memo to Whiteboard
              </h3>
              <button 
                onClick={() => setShowAddNoteModal(false)}
                className="p-1 hover:bg-surface-hover rounded text-text-muted cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                  Clue / Note Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Talegaon Toll Naka Surveillance Check"
                  value={newNoteTitle}
                  onChange={e => setNewNoteTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg text-text focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                  Investigator Observation / Lead
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Dispatched sub-inspector team to retrieve Talegaon toll camera timestamps for Qualis cab pass time at 22:45."
                  value={newNoteContent}
                  onChange={e => setNewNoteContent(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg text-text focus:outline-none focus:border-primary resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                    Sticky Note Color
                  </label>
                  <div className="flex items-center gap-2 mt-1">
                    {[
                      { bg: '#fef9c3', label: 'Yellow' },
                      { bg: '#fed7aa', label: 'Peach' },
                      { bg: '#fecdd3', label: 'Rose' },
                      { bg: '#bae6fd', label: 'Sky' },
                    ].map(c => (
                      <button
                        key={c.bg}
                        type="button"
                        onClick={() => setNewNoteColor(c.bg)}
                        style={{ background: c.bg }}
                        className={cn(
                          "w-6 h-6 rounded-full border-2 transition-all cursor-pointer",
                          newNoteColor === c.bg ? "border-primary scale-110 shadow-xs" : "border-transparent"
                        )}
                        title={c.label}
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                    Connect With Yarn To
                  </label>
                  <select
                    value={newNoteConnectTo}
                    onChange={e => setNewNoteConnectTo(e.target.value)}
                    className="w-full px-2 py-1.5 text-xs bg-background border border-border rounded-lg text-text"
                  >
                    <option value="">None (Independent Lead)</option>
                    {allNodes.map(n => (
                      <option key={n.id} value={n.id}>
                        {n.label} ({n.type})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-border">
              <button
                type="button"
                onClick={() => setShowAddNoteModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg hover:bg-surface-hover text-text-muted cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  if (!newNoteTitle.trim()) return;
                  const newId = 'NOTE-' + Date.now().toString().slice(-4);
                  const newNoteNode: InvestigationNode = {
                    id: newId,
                    label: newNoteTitle.trim(),
                    type: 'Other',
                  };
                  setCustomNodes(prev => [...prev, newNoteNode]);
                  
                  if (newNoteConnectTo) {
                    const newEdge: InvestigationEdge = {
                      id: 'e-custom-' + Date.now().toString().slice(-4),
                      source: newId,
                      target: newNoteConnectTo,
                      label: 'investigative lead',
                      type: 'references',
                    };
                    setCustomEdges(prev => [...prev, newEdge]);
                  }

                  // Position note near the right column
                  setPositions(prev => {
                    const next = new Map(prev);
                    next.set(newId, { x: 2360, y: 220 + customNodes.length * 180 });
                    return next;
                  });

                  setCustomNotesData(prev => {
                    const next = new Map(prev);
                    next.set(newId, {
                      title: newNoteTitle.trim(),
                      content: newNoteContent.trim(),
                      color: newNoteColor,
                    });
                    return next;
                  });

                  setNewNoteTitle('');
                  setNewNoteContent('');
                  setShowAddNoteModal(false);
                }}
                disabled={!newNoteTitle.trim()}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
              >
                Pin to Whiteboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}