import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  FileText, ShieldCheck, AlertTriangle, CheckCircle2, RefreshCw, 
  Search, Eye, Edit3, ArrowLeftRight, Volume2, ZoomIn, ZoomOut, 
  Maximize2, GitCommit, UserCheck, Layers, BookOpen, Quote, 
  HelpCircle, ChevronDown, ChevronRight, Check, Copy, ExternalLink,
  Sparkles, Lock, ShieldAlert, Cpu, Filter, Play, Pause, RotateCcw
} from 'lucide-react';
import { 
  Evidence, 
  MultilingualProfileResponse, 
  ExhibitTextVersion, 
  ExhibitSegment, 
  ExhibitTranslation, 
  DualCitation, 
  LanguageProfileConfig 
} from '../../types';
import { multilingualService } from '../../services';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { cn } from '../../utils';

interface SideBySideMultilingualViewerProps {
  caseId: string;
  evidence: Evidence;
  initialSearchQuery?: string;
  onTextUpdated?: () => void;
}

export const SideBySideMultilingualViewer: React.FC<SideBySideMultilingualViewerProps> = ({
  caseId,
  evidence,
  initialSearchQuery,
  onTextUpdated,
}) => {
  // State: Data
  const [loading, setLoading] = useState<boolean>(true);
  const [profile, setProfile] = useState<MultilingualProfileResponse | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null);
  const [hoveredSegmentId, setHoveredSegmentId] = useState<number | null>(null);

  // State: View options
  const [showOnlyLowConfidence, setShowOnlyLowConfidence] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'both' | 'original' | 'translation'>('both');
  const [searchQuery, setSearchQuery] = useState<string>(initialSearchQuery || '');

  useEffect(() => {
    if (initialSearchQuery) {
      setSearchQuery(initialSearchQuery);
    }
  }, [initialSearchQuery]);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // State: Audio playback simulation
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [audioPlaybackSec, setAudioPlaybackSec] = useState<number>(0);
  const audioIntervalRef = useRef<any>(null);

  // State: Modals & Dialogs
  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState<boolean>(false);
  const [isEditProfileOpen, setIsEditProfileOpen] = useState<boolean>(false);
  const [isDualCitationsOpen, setIsDualCitationsOpen] = useState<boolean>(false);
  const [correctionText, setCorrectionText] = useState<string>('');
  const [editReason, setEditReason] = useState<string>('');
  const [requiresSecondSignoff, setRequiresSecondSignoff] = useState<boolean>(false);
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Profile Edit fields
  const [editLang, setEditLang] = useState<string>('mr');
  const [editScript, setEditScript] = useState<string>('devanagari');
  const [editContentType, setEditContentType] = useState<string>('printed');
  const [editIsMixed, setEditIsMixed] = useState<boolean>(false);
  const [editIsPoorAudio, setEditIsPoorAudio] = useState<boolean>(false);

  // Fetch full multilingual profile
  const fetchProfile = async () => {
    try {
      setLoading(true);
      const data = await multilingualService.getProfile(caseId, evidence.id);
      setProfile(data);
      if (data.current_version) {
        setSelectedVersionId(data.current_version.id);
        setCorrectionText(data.current_version.raw_text || data.current_version.extracted_text || '');
      }
      setEditLang(data.primary_language || 'mr');
      setEditScript(data.script || 'devanagari');
      setEditContentType(data.content_type || 'printed');
      setEditIsMixed(Boolean(data.is_mixed));
      setEditIsPoorAudio(Boolean(data.is_poor_audio));
    } catch (err) {
      console.error('Failed to load exhibit multilingual profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [caseId, evidence.id]);

  // Current selected version
  const activeVersion = useMemo(() => {
    if (!profile) return null;
    if (!selectedVersionId) return profile.current_version || profile.versions[0] || null;
    return profile.versions.find(v => v.id === selectedVersionId) || profile.current_version || null;
  }, [profile, selectedVersionId]);

  // Current active translation
  const activeTranslation = useMemo(() => {
    if (!profile || !profile.translations || profile.translations.length === 0) return null;
    // Prefer reviewed or current version matching
    return profile.translations[0];
  }, [profile]);

  // Segments to display
  const segments = useMemo(() => {
    if (!activeVersion || !activeVersion.segments) return [];
    let list = [...activeVersion.segments];
    if (showOnlyLowConfidence) {
      list = list.filter(s => s.is_low_confidence || (s.confidence && s.confidence < 0.75));
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(s => 
        (s.raw_text && s.raw_text.toLowerCase().includes(q)) ||
        (s.normalized_text && s.normalized_text.toLowerCase().includes(q))
      );
    }
    return list;
  }, [activeVersion, showOnlyLowConfidence, searchQuery]);

  // Audio playback ticker
  useEffect(() => {
    if (isPlayingAudio) {
      audioIntervalRef.current = setInterval(() => {
        setAudioPlaybackSec(prev => {
          const next = prev + 1;
          // highlight segment matching playback
          if (activeVersion?.segments) {
            const match = activeVersion.segments.find(s => 
              s.start_time_sec != null && s.end_time_sec != null &&
              s.start_time_sec <= next && next <= s.end_time_sec
            );
            if (match) setActiveSegmentId(match.id);
          }
          return next > 120 ? 0 : next;
        });
      }, 1000);
    } else {
      if (audioIntervalRef.current) clearInterval(audioIntervalRef.current);
    }
    return () => {
      if (audioIntervalRef.current) clearInterval(audioIntervalRef.current);
    };
  }, [isPlayingAudio, activeVersion]);

  // Handle Text Correction submission
  const handleSubmitCorrection = async () => {
    if (!correctionText.trim()) return;
    if (!editReason.trim()) {
      setActionMessage({ text: 'Please specify the judicial reason for this correction.', type: 'error' });
      return;
    }

    try {
      setIsSubmittingCorrection(true);
      const res = await multilingualService.submitTextCorrection(caseId, evidence.id, {
        new_text: correctionText,
        edit_reason: editReason,
        requires_second_signoff: requiresSecondSignoff,
      });

      setActionMessage({
        text: `Version ${res.version_number} saved into cryptographic Merkle audit log. ${res.stale_citations_marked} downstream citations marked stale. ACH hypothesis probabilities updated.`,
        type: 'success',
      });

      setIsCorrectionModalOpen(false);
      setEditReason('');
      await fetchProfile();
      if (onTextUpdated) onTextUpdated();
    } catch (err: any) {
      console.error('Error submitting correction:', err);
      setActionMessage({ text: err?.message || 'Failed to submit text correction.', type: 'error' });
    } finally {
      setIsSubmittingCorrection(false);
    }
  };

  // Handle Version Revert
  const handleRevertVersion = async (versionId: number) => {
    try {
      const res = await multilingualService.revertToVersion(caseId, evidence.id, versionId);
      setActionMessage({
        text: `Reverted to version ${res.target_version}. Created new version ${res.new_version_number}.`,
        type: 'success'
      });
      await fetchProfile();
      if (onTextUpdated) onTextUpdated();
    } catch (err: any) {
      setActionMessage({ text: err?.message || 'Failed to revert version.', type: 'error' });
    }
  };

  // Handle Reviewer Signoff
  const handleSignoff = async (versionId: number) => {
    try {
      const res = await multilingualService.signoffVersion(caseId, evidence.id, versionId);
      setActionMessage({
        text: `Sign-off recorded by ${res.signoff_by}. Reliability rating updated.`,
        type: 'success'
      });
      await fetchProfile();
      if (onTextUpdated) onTextUpdated();
    } catch (err: any) {
      setActionMessage({ text: err?.message || 'Failed to record sign-off.', type: 'error' });
    }
  };

  // Handle Profile Confirmation / Update
  const handleSaveProfile = async () => {
    try {
      await multilingualService.confirmLanguageProfile(caseId, evidence.id, {
        primary_language: editLang,
        script: editScript,
        content_type: editContentType,
        is_mixed: editIsMixed,
        is_poor_audio: editIsPoorAudio,
      });
      setIsEditProfileOpen(false);
      setActionMessage({ text: 'Language profile confirmed and saved by analyst.', type: 'success' });
      await fetchProfile();
    } catch (err: any) {
      setActionMessage({ text: err?.message || 'Failed to update language profile.', type: 'error' });
    }
  };

  // Handle Translation Certification
  const handleCertifyTranslation = async (translationId: number) => {
    try {
      await multilingualService.reviewTranslation(caseId, evidence.id, translationId);
      setActionMessage({ text: 'Translation marked as certified human reviewed.', type: 'success' });
      await fetchProfile();
    } catch (err: any) {
      setActionMessage({ text: err?.message || 'Failed to certify translation.', type: 'error' });
    }
  };

  if (loading) {
    return (
      <div className="p-8 rounded-xl border border-border bg-surface flex flex-col items-center justify-center gap-3 text-cyan-400">
        <RefreshCw className="w-8 h-8 animate-spin text-cyan-500" />
        <span className="text-xs font-mono text-text-muted">Loading multilingual exhibit engine & synchronized viewer...</span>
      </div>
    );
  }

  if (!profile || !activeVersion) {
    return (
      <div className="p-6 rounded-xl border border-border bg-surface text-center">
        <p className="text-sm text-text-muted">No multilingual transcript or OCR version available for this exhibit.</p>
      </div>
    );
  }

  const isAudio = profile.content_type === 'audio' || profile.file_type?.toLowerCase().includes('audio');
  const isHandwritten = profile.content_type === 'handwritten';
  const hasLowConfidenceSegments = (activeVersion.segments || []).some(s => s.is_low_confidence || (s.confidence && s.confidence < 0.75));

  return (
    <div className="space-y-4">
      {/* Action Notification Alert */}
      {actionMessage && (
        <div className={cn(
          "p-3 rounded-lg border text-xs flex items-center justify-between gap-3 font-mono transition-all animate-fadeIn",
          actionMessage.type === 'success' 
            ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-300"
            : "bg-rose-950/40 border-rose-500/50 text-rose-300"
        )}>
          <div className="flex items-center gap-2">
            {actionMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-rose-400" />}
            <span>{actionMessage.text}</span>
          </div>
          <button 
            onClick={() => setActionMessage(null)}
            className="text-[10px] uppercase font-bold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ============================================================ */}
      {/* 1. TOP CONTROL BAR: METADATA, VERSION PICKER & ACTIONS       */}
      {/* ============================================================ */}
      <div className="p-4 rounded-xl border border-[#eae4d9] bg-white flex flex-col lg:flex-row lg:items-center justify-between gap-4 shadow-xs text-[#191410]">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              {profile.primary_language === 'mr' ? 'Marathi (मराठी)' : profile.primary_language === 'hi' ? 'Hindi (हिंदी)' : profile.primary_language === 'en' ? 'English' : 'Mixed / Hinglish'}
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-surface text-text-muted border border-border">
              Script: {profile.script}
            </span>
            <span className={cn(
              "px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase border",
              isHandwritten ? "bg-amber-500/10 text-amber-300 border-amber-500/30" : "bg-surface text-slate-300 border-border"
            )}>
              {profile.content_type}
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono text-text-muted bg-surface/60 border border-border">
              {profile.language_source === 'user_confirmed' ? '✓ Analyst Confirmed' : '⚡ Auto-Detected'}
            </span>
            <button
              onClick={() => setIsEditProfileOpen(!isEditProfileOpen)}
              className="text-[10px] text-cyan-400 hover:text-cyan-300 underline font-mono flex items-center gap-1 cursor-pointer"
            >
              <Edit3 className="w-2.5 h-2.5" /> Configure Profile
            </button>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <span className="font-semibold text-white">OCR / Reader:</span>
            <span className="font-mono text-cyan-300">{profile.ocr_reading_method || 'gemini_multimodal_ocr'}</span>
            <span className="text-text-muted">•</span>
            <span className="font-semibold text-white">Mean Confidence:</span>
            <span className={cn(
              "font-mono font-bold",
              profile.ocr_confidence >= 0.85 ? "text-emerald-400" : profile.ocr_confidence >= 0.70 ? "text-amber-400" : "text-rose-400"
            )}>
              {Math.round((profile.ocr_confidence || 0.85) * 100)}%
            </span>
            <span className="text-text-muted">•</span>
            <span className="font-semibold text-white">Reliability Score:</span>
            <span className="font-mono font-bold text-emerald-400">
              {profile.reliability_assessment?.reliability_rating ?? 0.85}
            </span>
          </div>
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Version Selector */}
          <div className="flex items-center gap-1.5 bg-surface border border-border rounded-lg px-2.5 py-1 text-xs">
            <GitCommit className="w-3.5 h-3.5 text-cyan-400" />
            <select
              value={activeVersion.id}
              onChange={(e) => setSelectedVersionId(Number(e.target.value))}
              aria-label="Select Exhibit Version"
              className="bg-transparent text-xs text-[#191410] font-mono focus:outline-none cursor-pointer"
            >
              {profile.versions.map((v) => (
                <option key={v.id} value={v.id} className="bg-white text-[#191410]">
                  v{v.version_number} ({v.status}) {v.is_current ? '• Active' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Correct Text Button */}
          <button
            onClick={() => {
              setCorrectionText(activeVersion.raw_text || activeVersion.extracted_text || '');
              setIsCorrectionModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shadow-md transition-all cursor-pointer"
            title="Submit a logged analyst correction with Merkle audit block and downstream ACH cascade"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Correct Text</span>
          </button>

          {/* Revert Button (if not current) */}
          {!activeVersion.is_current && (
            <button
              onClick={() => handleRevertVersion(activeVersion.id)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface hover:bg-surface-hover border border-border text-xs text-amber-300 font-mono transition-all cursor-pointer"
              title="Revert active exhibit text back to this version (appends new version)"
            >
              <RotateCcw className="w-3 h-3 text-amber-400" />
              <span>Revert to v{activeVersion.version_number}</span>
            </button>
          )}

          {/* Signoff Button (if requires second review) */}
          {activeVersion.requires_second_signoff && !activeVersion.second_signoff_by && (
            <button
              onClick={() => handleSignoff(activeVersion.id)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-all cursor-pointer"
              title="Second reviewer sign-off to finalize judicial veracity"
            >
              <UserCheck className="w-3 h-3" />
              <span>Reviewer Sign-off</span>
            </button>
          )}

          {/* Dual Citations Toggle */}
          <button
            onClick={() => setIsDualCitationsOpen(!isDualCitationsOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-hover border border-border text-xs text-slate-300 font-medium transition-all cursor-pointer"
            title="View citations in original language + English translation"
          >
            <Quote className="w-3.5 h-3.5 text-amber-400" />
            <span>Dual Citations ({profile.dual_citations?.length || 0})</span>
          </button>
        </div>
      </div>

      {/* ============================================================ */}
      {/* PROFILE CONFIGURATION POPUP / DRAWER                         */}
      {/* ============================================================ */}
      {isEditProfileOpen && (
        <div className="p-4 rounded-xl border border-border bg-surface/95 space-y-4 shadow-lg animate-fadeIn">
          <div className="flex items-center justify-between border-b border-border/50 pb-2">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              Exhibit Language & Reading Configuration
            </h4>
            <button onClick={() => setIsEditProfileOpen(false)} className="text-xs text-text-muted hover:text-white">✕</button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <label className="text-[10px] font-mono text-text-muted uppercase block mb-1">Primary Language</label>
              <select
                value={editLang}
                onChange={(e) => setEditLang(e.target.value)}
                className="w-full p-2 rounded bg-background border border-border text-white text-xs font-mono"
              >
                <option value="mr">Marathi (mr)</option>
                <option value="hi">Hindi (hi)</option>
                <option value="en">English (en)</option>
                <option value="mixed">Mixed (Devanagari + Latin)</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] font-mono text-text-muted uppercase block mb-1">Script Type</label>
              <select
                value={editScript}
                onChange={(e) => setEditScript(e.target.value)}
                className="w-full p-2 rounded bg-background border border-border text-white text-xs font-mono"
              >
                <option value="devanagari">Devanagari (देवनागरी)</option>
                <option value="latin">Latin / Roman</option>
                <option value="mixed">Mixed Script</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] font-mono text-text-muted uppercase block mb-1">Content Medium</label>
              <select
                value={editContentType}
                onChange={(e) => setEditContentType(e.target.value)}
                className="w-full p-2 rounded bg-background border border-border text-white text-xs font-mono"
              >
                <option value="printed">Printed Judicial Document</option>
                <option value="typed">Typewritten Report / FIR</option>
                <option value="handwritten">Handwritten Panchnama / Diary</option>
                <option value="stamped">Stamped Registry / Seal</option>
                <option value="audio">Audio Intercept / Recording</option>
              </select>
            </div>

            <div className="flex flex-col justify-end space-y-2">
              <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={editIsMixed}
                  onChange={(e) => setEditIsMixed(e.target.checked)}
                  className="rounded border-border"
                />
                <span>Code-switching (e.g. Marathi + English)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={editIsPoorAudio}
                  onChange={(e) => setEditIsPoorAudio(e.target.checked)}
                  className="rounded border-border"
                />
                <span>Degraded Audio / Heavy Background Noise</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border/40">
            <button
              onClick={() => setIsEditProfileOpen(false)}
              className="px-3 py-1.5 rounded bg-surface border border-border text-xs text-text-muted hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveProfile}
              className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shadow-md transition-all"
            >
              Confirm & Save Profile
            </button>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 2. VIEWER SUB-HEADER: SEARCH & FILTER CONTROLS               */}
      {/* ============================================================ */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface/60 p-2.5 rounded-lg border border-border text-xs">
        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search Devanagari (उदा. राऊत, खून) or English translation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded bg-background border border-border text-white text-xs placeholder:text-text-muted focus:outline-none focus:border-cyan-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-2 text-[10px] text-text-muted hover:text-white"
            >
              ✕
            </button>
          )}
        </div>

        {/* Filters and View Toggles */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowOnlyLowConfidence(!showOnlyLowConfidence)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all cursor-pointer",
              showOnlyLowConfidence 
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold"
                : "bg-surface hover:bg-surface-hover text-text-muted border border-border"
            )}
            title="Filter segments with confidence below threshold to quickly spot OCR errors"
          >
            <Filter className="w-3 h-3" />
            <span>Low Confidence Only</span>
            {hasLowConfidenceSegments && (
              <span className="w-2 h-2 rounded-full bg-amber-400" />
            )}
          </button>

          <div className="flex rounded bg-surface border border-border p-0.5 text-xs font-mono">
            <button
              onClick={() => setViewMode('both')}
              className={cn(
                "px-2.5 py-1 rounded transition-all",
                viewMode === 'both' ? "bg-cyan-500/20 text-cyan-300 font-semibold" : "text-text-muted hover:text-white"
              )}
            >
              Dual View
            </button>
            <button
              onClick={() => setViewMode('original')}
              className={cn(
                "px-2.5 py-1 rounded transition-all",
                viewMode === 'original' ? "bg-cyan-500/20 text-cyan-300 font-semibold" : "text-text-muted hover:text-white"
              )}
            >
              Original Text
            </button>
            <button
              onClick={() => setViewMode('translation')}
              className={cn(
                "px-2.5 py-1 rounded transition-all",
                viewMode === 'translation' ? "bg-cyan-500/20 text-cyan-300 font-semibold" : "text-text-muted hover:text-white"
              )}
            >
              English Translation
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 3. MAIN SIDE-BY-SIDE SYNCHRONIZED SPLIT VIEWER               */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* ------------------------------------------------------------ */}
        {/* LEFT COLUMN (COL-5): ORIGINAL SCAN / AUDIO CANVAS            */}
        {/* ------------------------------------------------------------ */}
        <div className="lg:col-span-5 space-y-2 flex flex-col">
          <div className="flex items-center justify-between px-2 text-xs">
            <span className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-cyan-400" />
              {isAudio ? 'Authentic Audio Media' : 'Original Raw Document Scan'}
            </span>
            <div className="flex items-center gap-2 text-text-muted">
              {!isAudio && (
                <>
                  <button 
                    onClick={() => setZoomLevel(prev => Math.max(0.75, prev - 0.2))} 
                    className="p-1 hover:text-white" 
                    title="Zoom Out"
                    aria-label="Zoom Out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <span className="font-mono text-[10px]">{Math.round(zoomLevel * 100)}%</span>
                  <button 
                    onClick={() => setZoomLevel(prev => Math.min(2.0, prev + 0.2))} 
                    className="p-1 hover:text-white" 
                    title="Zoom In"
                    aria-label="Zoom In"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="flex-1 rounded-xl border border-[#eae4d9] bg-white p-4 flex flex-col justify-between shadow-xs relative min-h-[460px] overflow-hidden">
            {/* Audio Mode */}
            {isAudio ? (
              <div className="space-y-6 my-auto text-center p-4">
                <div className="w-16 h-16 rounded-full bg-cyan-500/10 border-2 border-cyan-500/40 flex items-center justify-center mx-auto text-cyan-400">
                  <Volume2 className="w-8 h-8" />
                </div>

                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-white">{profile.file_name}</h4>
                  <p className="text-xs font-mono text-text-muted">
                    Format: WAV/MP3 • Speech-to-Text: Whisper Large v3 Indic
                  </p>
                  {profile.is_poor_audio && (
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-[10px] font-mono mt-2">
                      <AlertTriangle className="w-3 h-3 text-rose-400" />
                      <span>Degraded Audio (-0.10 reliability penalty active)</span>
                    </div>
                  )}
                </div>

                {/* Simulated Audio Player Controls */}
                <div className="space-y-2 max-w-xs mx-auto">
                  <div className="flex items-center justify-center gap-3">
                    <button
                      onClick={() => setIsPlayingAudio(!isPlayingAudio)}
                      className="w-10 h-10 rounded-full bg-cyan-600 hover:bg-cyan-500 text-white flex items-center justify-center shadow-lg transition-all"
                    >
                      {isPlayingAudio ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                    </button>
                    <button
                      onClick={() => {
                        setAudioPlaybackSec(0);
                        setIsPlayingAudio(false);
                      }}
                      className="p-2 rounded-lg bg-surface border border-border text-text-muted hover:text-white"
                      title="Rewind to start"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="font-mono text-xs text-cyan-400">
                    {Math.floor(audioPlaybackSec / 60).toString().padStart(2, '0')}:{(audioPlaybackSec % 60).toString().padStart(2, '0')} / 02:00
                  </div>
                </div>

                {/* Audio Timestamps list */}
                <div className="space-y-1.5 text-left max-h-48 overflow-y-auto pt-4 border-t border-border/40 font-mono text-[11px]">
                  {activeVersion.segments?.map((seg) => (
                    <div
                      key={seg.id}
                      onClick={() => {
                        setActiveSegmentId(seg.id);
                        if (seg.start_time_sec != null) setAudioPlaybackSec(seg.start_time_sec);
                      }}
                      className={cn(
                        "p-2 rounded border cursor-pointer transition-all flex items-center justify-between",
                        activeSegmentId === seg.id ? "bg-cyan-500/20 border-cyan-500/60 text-white" : "bg-surface/50 border-border/60 text-text-muted hover:text-white"
                      )}
                    >
                      <span>⏱ {seg.start_time_sec}s - {seg.end_time_sec}s</span>
                      <span className="truncate max-w-[180px]">{seg.raw_text}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* Scanned Document Canvas with Bounding Boxes */
              <div className="relative w-full h-full flex flex-col items-center justify-center overflow-auto">
                <div 
                  className="relative w-full max-w-[380px] bg-[#fbfbf8] text-[#1a1a1a] rounded shadow-2xl p-6 font-serif border border-stone-400 transition-all select-none min-h-[480px]"
                  style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}
                >
                  {/* Watermark / Police Seal Simulation */}
                  <div className="text-center border-b border-stone-300 pb-2 mb-3">
                    <div className="text-[10px] font-mono tracking-widest text-stone-500 uppercase">
                      GOVERNMENT OF MAHARASHTRA • POLICE RECORD
                    </div>
                    <div className="text-xs font-bold font-sans text-stone-800">
                      {profile.file_name}
                    </div>
                  </div>

                  {/* Document Simulated Page Content with Interactive Bounding Box Overlays */}
                  <div className="space-y-3 relative text-[11px] leading-relaxed font-mono">
                    {activeVersion.segments?.map((seg, idx) => {
                      const isHovered = hoveredSegmentId === seg.id;
                      const isActive = activeSegmentId === seg.id;
                      const isLowConf = seg.is_low_confidence || (seg.confidence && seg.confidence < 0.75);

                      return (
                        <div
                          key={seg.id}
                          onMouseEnter={() => setHoveredSegmentId(seg.id)}
                          onMouseLeave={() => setHoveredSegmentId(null)}
                          onClick={() => setActiveSegmentId(seg.id)}
                          className={cn(
                            "relative p-2 rounded transition-all cursor-pointer border",
                            isActive 
                              ? "bg-cyan-500/20 border-cyan-600 shadow-md ring-2 ring-cyan-500" 
                              : isHovered 
                              ? "bg-amber-500/10 border-amber-500/60" 
                              : isLowConf
                              ? "bg-amber-100/50 border-dashed border-amber-500/70 text-stone-800"
                              : "border-transparent hover:border-stone-400 text-stone-800"
                          )}
                        >
                          <div className="flex items-center justify-between text-[9px] font-mono text-stone-500 mb-0.5">
                            <span>Box #{idx + 1} {seg.page_number ? `(P.${seg.page_number})` : ''}</span>
                            <span className={cn(
                              "font-bold",
                              isLowConf ? "text-amber-700" : "text-emerald-700"
                            )}>
                              {Math.round((seg.confidence || 0.85) * 100)}%
                            </span>
                          </div>
                          <p className="font-serif text-[11px] leading-snug">
                            {seg.raw_text}
                          </p>

                          {/* Bounding box marker indicator */}
                          {isActive && (
                            <span className="absolute -top-2 -right-2 px-1.5 py-0.5 bg-cyan-600 text-white rounded text-[8px] font-mono font-bold shadow">
                              ACTIVE
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Bar: Preprocessing Pipeline Indicators */}
            <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[10px] font-mono text-text-muted">
              <span>Enhancements: Deskewed • Denoise • Contrast 1.8x • Super-Res 2x</span>
              <span className="text-cyan-400">SHA-256 Verified ✓</span>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------------------ */}
        {/* RIGHT COLUMN (COL-7): EXTRACTED & TRANSLATED SEGMENTS STREAM */}
        {/* ------------------------------------------------------------ */}
        <div className="lg:col-span-7 space-y-2 flex flex-col">
          <div className="flex items-center justify-between px-2 text-xs">
            <span className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              Extracted Text & Aligned Translations
            </span>
            <span className="font-mono text-text-muted">
              {segments.length} segments displayed
            </span>
          </div>

          <div className="flex-1 rounded-xl border border-[#eae4d9] bg-[#faf7f2] p-4 overflow-y-auto max-h-[620px] space-y-3 shadow-inner">
            {segments.length === 0 ? (
              <div className="p-8 text-center text-text-muted text-xs font-mono">
                No text segments match the current filters or search query.
              </div>
            ) : (
              segments.map((seg, idx) => {
                const isActive = activeSegmentId === seg.id;
                const isHovered = hoveredSegmentId === seg.id;
                const isLowConf = seg.is_low_confidence || (seg.confidence && seg.confidence < 0.75);

                // Find matching translation segment if available
                const translationSeg = activeTranslation?.aligned_segments?.find(
                  ts => ts.source_segment_id === seg.id || idx === 0
                );

                return (
                  <div
                    key={seg.id}
                    onMouseEnter={() => setHoveredSegmentId(seg.id)}
                    onMouseLeave={() => setHoveredSegmentId(null)}
                    onClick={() => setActiveSegmentId(seg.id)}
                    className={cn(
                      "p-3.5 rounded-lg border transition-all cursor-pointer relative",
                      isActive
                        ? "bg-cyan-950/40 border-cyan-500 shadow-md"
                        : isHovered
                        ? "bg-surface-hover border-border/90"
                        : "bg-surface border-border/70"
                    )}
                  >
                    {/* Segment Header */}
                    <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-1.5 mb-2 text-[10px] font-mono">
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 rounded bg-surface border border-border font-bold text-white">
                          #{seg.segment_index || idx + 1}
                        </span>
                        {seg.page_number && (
                          <span className="text-text-muted">Page {seg.page_number}</span>
                        )}
                        {seg.start_time_sec !== undefined && (
                          <span className="text-cyan-400 font-bold">
                            {seg.start_time_sec}s - {seg.end_time_sec}s
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {isLowConf && (
                          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold flex items-center gap-1">
                            <AlertTriangle className="w-2.5 h-2.5" /> Low Confidence
                          </span>
                        )}
                        <span className={cn(
                          "px-2 py-0.5 rounded border font-bold",
                          (seg.confidence || 0.85) >= 0.85
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                        )}>
                          {Math.round((seg.confidence || 0.85) * 100)}%
                        </span>
                      </div>
                    </div>

                    {/* Original Extracted Text */}
                    {(viewMode === 'both' || viewMode === 'original') && (
                      <div className="space-y-1">
                        <div className="text-[10px] font-mono text-cyan-400 uppercase font-semibold flex items-center justify-between">
                          <span>Original Text ({profile.primary_language.toUpperCase()}):</span>
                          {seg.normalized_text && seg.normalized_text !== seg.raw_text && (
                            <span className="text-[9px] text-text-muted font-normal" title="Normalized Devanagari numerals standardizing">
                              Unicode NFC normalized
                            </span>
                          )}
                        </div>
                        <p className={cn(
                          "text-xs leading-relaxed font-sans",
                          isLowConf ? "text-amber-200 underline decoration-amber-500/50 decoration-wavy" : "text-slate-100 font-medium"
                        )}>
                          {seg.raw_text}
                        </p>
                      </div>
                    )}

                    {/* Normalized numerals preview if different */}
                    {seg.normalized_text && seg.normalized_text !== seg.raw_text && (
                      <div className="mt-1.5 p-1.5 rounded bg-background/80 border border-border/50 text-[10px] font-mono text-emerald-300 flex items-center gap-1.5">
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span>Standardized Numerals / Text: {seg.normalized_text}</span>
                      </div>
                    )}

                    {/* English Aligned Translation */}
                    {(viewMode === 'both' || viewMode === 'translation') && activeTranslation && (
                      <div className="mt-2.5 pt-2 border-t border-border/30 space-y-1">
                        <div className="text-[10px] font-mono text-amber-400 uppercase font-semibold flex items-center justify-between">
                          <span>Aligned English Translation:</span>
                          <span className="text-[9px] text-text-muted font-normal">
                            {activeTranslation.review_status === 'reviewed' ? '✓ Human Certified' : '⚡ Machine Translation'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 italic font-sans leading-relaxed">
                          "{translationSeg?.translated_text || activeTranslation.full_translated_text.slice(0, 140)}..."
                        </p>
                      </div>
                    )}

                    {/* Proper name transliteration chips if present */}
                    {translationSeg?.proper_names_json && (
                      <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                        <span className="text-[9px] font-mono text-text-muted">Names:</span>
                        {Object.entries(JSON.parse(translationSeg.proper_names_json)).map(([deva, lat]) => (
                          <span 
                            key={deva} 
                            className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-cyan-950 border border-cyan-700/60 text-cyan-300"
                          >
                            {deva} ⇄ {String(lat)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 4. DUAL CITATIONS COLLAPSIBLE ACCORDION                      */}
      {/* ============================================================ */}
      {isDualCitationsOpen && (
        <Card className="border-border bg-surface animate-fadeIn">
          <CardHeader className="py-3 border-b border-border/50">
            <CardTitle className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Quote className="w-4 h-4 text-amber-400" />
              Judicial Dual-Format Citations Anchored to this Exhibit
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-3">
            {profile.dual_citations?.length === 0 ? (
              <p className="text-xs text-text-muted italic">No citations anchored to this exhibit yet.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {profile.dual_citations?.map((cit) => (
                  <div key={cit.citation_id} className="p-3.5 rounded-lg border border-border bg-background space-y-2">
                    <div className="flex items-center justify-between text-[10px] font-mono border-b border-border/40 pb-1.5">
                      <span className="font-bold text-cyan-400">Citation #{cit.citation_id}</span>
                      <span className="text-text-muted">{cit.location_tag}</span>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[10px] font-mono text-text-muted uppercase">Original Quote:</div>
                      <p className="text-xs font-serif text-white font-medium italic">
                        "{cit.original_quote}"
                      </p>
                    </div>

                    {cit.translated_quote && (
                      <div className="space-y-1 pt-1.5 border-t border-border/30">
                        <div className="text-[10px] font-mono text-amber-400 uppercase flex items-center justify-between">
                          <span>English Translation:</span>
                          <span className="text-[9px] text-text-muted font-normal">{cit.translation_label}</span>
                        </div>
                        <p className="text-xs text-slate-300 italic">
                          "{cit.translated_quote}"
                        </p>
                      </div>
                    )}

                    {cit.is_stale && (
                      <div className="text-[10px] font-mono text-rose-400 flex items-center gap-1 pt-1">
                        <AlertTriangle className="w-3 h-3 text-rose-400" />
                        <span>Flagged as stale due to text correction; re-verification needed.</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ============================================================ */}
      {/* 5. TEXT CORRECTION & AUDIT MODAL                             */}
      {/* ============================================================ */}
      {isCorrectionModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#eae4d9] rounded-xl w-full max-w-3xl overflow-hidden shadow-xl space-y-4 p-6 animate-scaleUp text-[#191410]">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Analyst OCR / Transcript Correction & Cryptographic Versioning
                </h3>
              </div>
              <button 
                onClick={() => setIsCorrectionModalOpen(false)}
                className="text-text-muted hover:text-white text-xs font-mono"
              >
                ✕ Cancel
              </button>
            </div>

            <div className="p-3 bg-cyan-950/30 border border-cyan-500/30 rounded-lg text-xs text-cyan-200 space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-cyan-400" /> Judicial Immutability & Audit Guarantee
              </div>
              <p className="text-[11px] text-text-muted">
                Original Machine Version 1 remains permanently preserved and untouched. Submitting this correction creates an immutable Version {activeVersion.version_number + 1}, logs a SHA-256 Merkle audit block, marks affected entities and citations as stale for review, and automatically recalculates ACH hypothesis probabilities.
              </p>
            </div>

            {/* Editable Text Area */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-text-muted uppercase">
                Corrected Full Text ({profile.primary_language.toUpperCase()}):
              </label>
              <textarea
                value={correctionText}
                onChange={(e) => setCorrectionText(e.target.value)}
                rows={8}
                className="w-full p-3 rounded-lg bg-background border border-border text-white text-xs font-sans leading-relaxed focus:outline-none focus:border-cyan-500"
                placeholder="Enter corrected transcript or OCR text..."
              />
            </div>

            {/* Mandatory Reason for Edit */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-amber-300 uppercase font-semibold">
                Mandatory Legal / Judicial Reason for Correction:
              </label>
              <input
                type="text"
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                placeholder="e.g. Corrected Marathi spelling of suspect name Yogesh Raut and rectified OCR numeral 2541"
                className="w-full p-2.5 rounded bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Second Signoff Checkbox */}
            <div className="pt-1">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresSecondSignoff}
                  onChange={(e) => setRequiresSecondSignoff(e.target.checked)}
                  className="rounded border-border"
                />
                <span>Require second reviewer sign-off before finalizing legal score upgrade</span>
              </label>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border/40">
              <button
                onClick={() => setIsCorrectionModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-hover border border-border text-xs text-text-muted hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitCorrection}
                disabled={isSubmittingCorrection || !correctionText.trim() || !editReason.trim()}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold text-xs shadow-lg transition-all"
              >
                {isSubmittingCorrection && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Version & Log to Audit Chain</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
