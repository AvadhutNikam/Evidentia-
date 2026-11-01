// src/pages/case/MobileFieldCapture.tsx
import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { 
  Camera, Mic, Video, MapPin, ShieldCheck, ShieldAlert, 
  CheckCircle2, AlertTriangle, RefreshCw, Smartphone, ArrowLeft, 
  Lock, FileText, Check, Copy, UploadCloud, Info, Play, Pause,
  Square, Radio, Wifi, WifiOff, Volume2, Sparkles, X, ChevronRight,
  Bookmark, Award
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { evidenceService, caseService, voiceNoteService } from '../../services';
import { Case, Evidence, VoiceNote, OfflineFieldExhibit } from '../../types';
import { cn } from '../../utils';

const OFFLINE_QUEUE_KEY = 'evidentia_offline_field_exhibits';

export function MobileFieldCapture() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { user, role } = useAuth();

  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  const [loadingCase, setLoadingCase] = useState(true);

  // Top Level Mode: 'media_capture' | 'voice_notes'
  const [activeTab, setActiveTab] = useState<'media_capture' | 'voice_notes'>('media_capture');

  // Network & Offline State
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [offlineQueue, setOfflineQueue] = useState<OfflineFieldExhibit[]>([]);
  const [syncingQueue, setSyncingQueue] = useState(false);
  const [queueDrawerOpen, setQueueDrawerOpen] = useState(false);

  // Media Capture Mode: 'photo' | 'video' | 'audio' | 'file'
  const [captureMode, setCaptureMode] = useState<'photo' | 'video' | 'audio' | 'file'>('photo');
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [clientHash, setClientHash] = useState<string>('');
  const [hashingInProgress, setHashingInProgress] = useState(false);

  // Live in-app recording states
  const [isLiveCameraActive, setIsLiveCameraActive] = useState(false);
  const [isVideoRecording, setIsVideoRecording] = useState(false);
  const [isAudioRecording, setIsAudioRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);

  // GPS & Location State
  const [gpsLocation, setGpsLocation] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude: number | null;
  } | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [fetchingGps, setFetchingGps] = useState(false);
  const [capturedAt, setCapturedAt] = useState<string>('');

  // Form Details
  const [title, setTitle] = useState('');
  const [evidenceType, setEvidenceType] = useState('photograph');
  const [locationName, setLocationName] = useState('');
  const [tamperSealNumber, setTamperSealNumber] = useState('');
  const [custodyNotes, setCustodyNotes] = useState('');
  const [officerConfirmed, setOfficerConfirmed] = useState(false);
  const [officerDeclaration, setOfficerDeclaration] = useState('');

  // Submission State
  const [submitting, setSubmitting] = useState(false);
  const [submittedEvidence, setSubmittedEvidence] = useState<Evidence | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [offlineSavedSuccess, setOfflineSavedSuccess] = useState<boolean>(false);

  // Quick Voice Notes State
  const [voiceNotes, setVoiceNotes] = useState<VoiceNote[]>([]);
  const [loadingVoiceNotes, setLoadingVoiceNotes] = useState(false);
  const [isVoiceNoteRecording, setIsVoiceNoteRecording] = useState(false);
  const [voiceNoteText, setVoiceNoteText] = useState('');
  const [voiceNoteInterim, setVoiceNoteInterim] = useState('');
  const [voiceNoteCategory, setVoiceNoteCategory] = useState('field_observation');
  const [voiceNoteAudioBlob, setVoiceNoteAudioBlob] = useState<Blob | null>(null);
  const [savingVoiceNote, setSavingVoiceNote] = useState(false);
  const [latestSavedNote, setLatestSavedNote] = useState<VoiceNote | null>(null);
  const [copiedCitation, setCopiedCitation] = useState<string | null>(null);

  // Hardware Element Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const liveStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordTimerRef = useRef<any>(null);
  const voiceNoteRecognitionRef = useRef<any>(null);

  // Load case metadata
  useEffect(() => {
    if (!caseId) return;
    caseService.getCaseById(caseId)
      .then(c => {
        if (c) setCurrentCase(c);
      })
      .catch(err => console.error('Failed to load case:', err))
      .finally(() => setLoadingCase(false));
  }, [caseId]);

  // Network status listeners
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      autoSyncOfflineQueue();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    loadOfflineQueue();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Request GPS coordinates on mount
  useEffect(() => {
    fetchCurrentLocation();
  }, []);

  // Update default officer declaration when user is ready
  useEffect(() => {
    if (user?.full_name) {
      setOfficerDeclaration(
        `I, ${user.full_name} (${user.badge_number || user.role}), hereby certify under Section 63/65B of the Indian Evidence Act / Section 61 BSA that this exhibit was captured directly at the crime scene at the recorded date, time, and GPS coordinates without alteration, filtering, or tampering.`
      );
    }
  }, [user]);

  // Load existing voice notes when voice_notes tab is opened
  useEffect(() => {
    if (activeTab === 'voice_notes' && caseId) {
      loadCaseVoiceNotes();
    }
  }, [activeTab, caseId]);

  const loadCaseVoiceNotes = async () => {
    if (!caseId) return;
    try {
      setLoadingVoiceNotes(true);
      const notes = await voiceNoteService.getVoiceNotes(caseId);
      setVoiceNotes(notes);
    } catch (err) {
      console.error('Failed to load voice notes:', err);
    } finally {
      setLoadingVoiceNotes(false);
    }
  };

  const fetchCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by this mobile device/browser.');
      return;
    }
    setFetchingGps(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          altitude: pos.coords.altitude
        });
        setFetchingGps(false);
      },
      (err) => {
        setGpsError(`GPS lookup failed: ${err.message}. Manual location notes will apply.`);
        setFetchingGps(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  };

  // On-Device SHA-256 Hashing using Web Cryptography API
  const computeClientHashFromBlob = async (blob: Blob): Promise<string> => {
    setHashingInProgress(true);
    try {
      const buffer = await blob.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      setClientHash(hashHex);
      return hashHex;
    } catch (e: any) {
      console.error('Failed to compute on-device hash:', e);
      setSubmitError('Failed to calculate on-device SHA-256 hash.');
      return '';
    } finally {
      setHashingInProgress(false);
    }
  };

  // ==============================================================================
  // OFFLINE QUEUE (INDEXEDDB / LOCALSTORAGE)
  // ==============================================================================

  const loadOfflineQueue = () => {
    try {
      const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        setOfflineQueue(parsed);
      }
    } catch (e) {
      console.warn('Failed to load offline queue:', e);
    }
  };

  const saveExhibitToOfflineQueue = async (blob: Blob, itemTitle: string, type: string, hash: string) => {
    const reader = new FileReader();
    reader.readAsDataURL(blob);
    reader.onloadend = () => {
      const base64Data = reader.result as string;
      const queuedItem: OfflineFieldExhibit = {
        id: `offline_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        caseId: caseId || '1',
        title: itemTitle || `Scene Exhibit: ${type.toUpperCase()}`,
        evidenceType: type,
        fileName: `field_${type}_${Date.now()}.${type === 'photograph' ? 'jpg' : type === 'video' ? 'webm' : 'webm'}`,
        blobDataUrl: base64Data,
        fileSize: blob.size,
        clientHash: hash,
        capturedAt: capturedAt || new Date().toISOString(),
        latitude: gpsLocation?.latitude,
        longitude: gpsLocation?.longitude,
        accuracy: gpsLocation?.accuracy,
        locationName,
        tamperSealNumber,
        custodyNotes,
        officerDeclaration,
        syncStatus: 'pending'
      };

      const updated = [queuedItem, ...offlineQueue];
      setOfflineQueue(updated);
      try {
        localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(updated));
      } catch (err) {
        console.warn('LocalStorage quota exceeded for offline queue:', err);
      }
      setOfflineSavedSuccess(true);
    };
  };

  const autoSyncOfflineQueue = async () => {
    if (offlineQueue.length === 0 || syncingQueue) return;
    await syncAllOfflineItems();
  };

  const syncAllOfflineItems = async () => {
    if (!caseId) return;
    setSyncingQueue(true);
    const remaining = [...offlineQueue];

    for (let i = 0; i < remaining.length; i++) {
      const item = remaining[i];
      if (item.syncStatus === 'synced') continue;

      try {
        remaining[i].syncStatus = 'syncing';
        setOfflineQueue([...remaining]);

        // Convert data URL back to Blob
        let fileBlob: Blob;
        if (item.blobDataUrl) {
          const res = await fetch(item.blobDataUrl);
          fileBlob = await res.blob();
        } else {
          continue;
        }

        const formData = new FormData();
        formData.append('file', fileBlob, item.fileName);
        formData.append('client_computed_hash', item.clientHash);
        formData.append('officer_confirmed', 'true');
        formData.append('officer_declaration', item.officerDeclaration);
        formData.append('evidence_type', item.evidenceType);
        formData.append('title', item.title);
        if (item.latitude) formData.append('latitude', String(item.latitude));
        if (item.longitude) formData.append('longitude', String(item.longitude));
        if (item.accuracy) formData.append('accuracy_meters', String(item.accuracy));
        formData.append('captured_at', item.capturedAt);
        formData.append('device_info', 'Offline Field Device Sync');
        if (item.locationName) formData.append('location_name', item.locationName);
        if (item.tamperSealNumber) formData.append('tamper_seal_number', item.tamperSealNumber);
        formData.append('source_agency', 'Scene Mobile Forensics Unit');
        if (item.custodyNotes) formData.append('custody_notes', item.custodyNotes);

        const created = await evidenceService.uploadFieldEvidence(caseId, formData);
        remaining[i].syncStatus = 'synced';
        remaining[i].syncedEvidenceId = created.id;
      } catch (err: any) {
        remaining[i].syncStatus = 'failed';
        remaining[i].syncError = err.message || 'Sync failed';
      }
    }

    // Keep failed or recently synced for confirmation
    const finalQueue = remaining.filter(item => item.syncStatus !== 'synced');
    setOfflineQueue(finalQueue);
    try {
      localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(finalQueue));
    } catch (e) {}
    setSyncingQueue(false);
  };

  // ==============================================================================
  // LIVE CAMERA & VIDEO/AUDIO RECORDER CONTROLS
  // ==============================================================================

  const startLiveCamera = async () => {
    try {
      setIsLiveCameraActive(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false
      });
      liveStreamRef.current = stream;
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream;
      }
    } catch (err: any) {
      console.error('Camera stream error:', err);
      setSubmitError('Unable to access live camera. Please use file upload mode.');
      setIsLiveCameraActive(false);
    }
  };

  const stopLiveCamera = () => {
    if (liveStreamRef.current) {
      liveStreamRef.current.getTracks().forEach(t => t.stop());
      liveStreamRef.current = null;
    }
    setIsLiveCameraActive(false);
  };

  const capturePhotoFrame = async () => {
    if (!cameraVideoRef.current) return;
    const video = cameraVideoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const nowIso = new Date().toISOString();
      setCapturedAt(nowIso);
      setCapturedBlob(blob);
      setEvidenceType('photograph');
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
      if (!title) setTitle(`Scene Photo: Recovery at ${new Date().toLocaleTimeString()}`);
      stopLiveCamera();
      await computeClientHashFromBlob(blob);
      fetchCurrentLocation();
    }, 'image/jpeg', 0.92);
  };

  const startVideoRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: true
      });
      liveStreamRef.current = stream;
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream;
      }
      const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const fullBlob = new Blob(chunks, { type: 'video/webm' });
        setCapturedBlob(fullBlob);
        setEvidenceType('video');
        const url = URL.createObjectURL(fullBlob);
        setPreviewUrl(url);
        if (!title) setTitle(`Scene Video: Field Walkthrough ${new Date().toLocaleTimeString()}`);
        await computeClientHashFromBlob(fullBlob);
        fetchCurrentLocation();
        stopLiveCamera();
      };

      recorder.start();
      setIsVideoRecording(true);
      setRecordingDuration(0);
      recordTimerRef.current = setInterval(() => {
        setRecordingDuration(d => d + 1);
      }, 1000);
    } catch (err: any) {
      setSubmitError('Failed to start video recording: ' + err.message);
    }
  };

  const stopVideoRecording = () => {
    if (mediaRecorderRef.current && isVideoRecording) {
      mediaRecorderRef.current.stop();
      setIsVideoRecording(false);
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    }
  };

  const startAudioRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      liveStreamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const fullBlob = new Blob(chunks, { type: 'audio/webm' });
        setCapturedBlob(fullBlob);
        setEvidenceType('audio');
        const url = URL.createObjectURL(fullBlob);
        setPreviewUrl(url);
        if (!title) setTitle(`Scene Audio: Ambient Statement ${new Date().toLocaleTimeString()}`);
        await computeClientHashFromBlob(fullBlob);
        fetchCurrentLocation();
        stream.getTracks().forEach(t => t.stop());
      };

      recorder.start();
      setIsAudioRecording(true);
      setRecordingDuration(0);
      recordTimerRef.current = setInterval(() => {
        setRecordingDuration(d => d + 1);
      }, 1000);
    } catch (err: any) {
      setSubmitError('Failed to start audio recording: ' + err.message);
    }
  };

  const stopAudioRecording = () => {
    if (mediaRecorderRef.current && isAudioRecording) {
      mediaRecorderRef.current.stop();
      setIsAudioRecording(false);
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    }
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setCapturedFile(file);
    setCapturedBlob(file);
    const nowIso = new Date().toISOString();
    setCapturedAt(nowIso);

    if (file.type.startsWith('image/')) {
      setEvidenceType('photograph');
      setPreviewUrl(URL.createObjectURL(file));
    } else if (file.type.startsWith('video/')) {
      setEvidenceType('video');
      setPreviewUrl(URL.createObjectURL(file));
    } else if (file.type.startsWith('audio/')) {
      setEvidenceType('audio');
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setEvidenceType('document');
      setPreviewUrl(null);
    }

    if (!title) {
      const baseName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      setTitle(`Scene Exhibit: ${baseName}`);
    }

    await computeClientHashFromBlob(file);
    fetchCurrentLocation();
  };

  // Submit Field Media
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !capturedBlob) return;

    if (!officerConfirmed) {
      setSubmitError('You must check the legal certification box before registering field evidence.');
      return;
    }

    if (!clientHash) {
      setSubmitError('On-device SHA-256 hash not computed. Please capture or select media again.');
      return;
    }

    // IF OFFLINE: Save to Offline Queue immediately
    if (!isOnline) {
      await saveExhibitToOfflineQueue(capturedBlob, title, evidenceType, clientHash);
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);

      const ext = evidenceType === 'photograph' ? 'jpg' : evidenceType === 'video' ? 'webm' : 'webm';
      const filename = capturedFile ? capturedFile.name : `field_${evidenceType}_${Date.now()}.${ext}`;

      const formData = new FormData();
      formData.append('file', capturedBlob, filename);
      formData.append('client_computed_hash', clientHash);
      formData.append('officer_confirmed', 'true');
      formData.append('officer_declaration', officerDeclaration);
      formData.append('evidence_type', evidenceType);
      formData.append('title', title || filename);

      if (gpsLocation) {
        formData.append('latitude', String(gpsLocation.latitude));
        formData.append('longitude', String(gpsLocation.longitude));
        formData.append('accuracy_meters', String(gpsLocation.accuracy));
      }
      formData.append('captured_at', capturedAt || new Date().toISOString());
      formData.append('device_info', `${navigator.userAgent} (${navigator.platform || 'Mobile Field Unit'})`);
      if (locationName) formData.append('location_name', locationName);
      if (tamperSealNumber) formData.append('tamper_seal_number', tamperSealNumber);
      formData.append('source_agency', 'Scene Mobile Forensics Unit');
      if (custodyNotes) formData.append('custody_notes', custodyNotes);

      const created = await evidenceService.uploadFieldEvidence(caseId, formData);
      setSubmittedEvidence(created);
    } catch (err: any) {
      console.warn('Network upload error, saving to offline queue:', err);
      // Fallback save to offline queue on network error
      await saveExhibitToOfflineQueue(capturedBlob, title, evidenceType, clientHash);
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setCapturedFile(null);
    setCapturedBlob(null);
    setPreviewUrl(null);
    setClientHash('');
    setTitle('');
    setLocationName('');
    setTamperSealNumber('');
    setCustodyNotes('');
    setOfficerConfirmed(false);
    setSubmittedEvidence(null);
    setOfflineSavedSuccess(false);
    setSubmitError(null);
    stopLiveCamera();
    stopVideoRecording();
    stopAudioRecording();
    fetchCurrentLocation();
  };

  // ==============================================================================
  // QUICK VOICE NOTES BY VOICE (BECOME CITED CASE NOTES)
  // ==============================================================================

  const startVoiceNoteRecording = async () => {
    setSubmitError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      liveStreamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        const fullBlob = new Blob(chunks, { type: 'audio/webm' });
        setVoiceNoteAudioBlob(fullBlob);
        stream.getTracks().forEach(t => t.stop());
      };

      recorder.start();

      // Start SpeechRecognition
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recog = new SpeechRecognition();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = 'en-US';

        recog.onresult = (e: any) => {
          let interim = '';
          for (let i = e.resultIndex; i < e.results.length; ++i) {
            const transcript = e.results[i][0].transcript;
            if (e.results[i].isFinal) {
              setVoiceNoteText(prev => (prev ? `${prev} ${transcript.trim()}` : transcript.trim()));
            } else {
              interim += transcript;
            }
          }
          setVoiceNoteInterim(interim);
        };

        recog.start();
        voiceNoteRecognitionRef.current = recog;
      }

      setIsVoiceNoteRecording(true);
      fetchCurrentLocation();
    } catch (err: any) {
      setSubmitError('Microphone error: ' + err.message);
    }
  };

  const stopVoiceNoteRecording = () => {
    setIsVoiceNoteRecording(false);
    setVoiceNoteInterim('');
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    if (voiceNoteRecognitionRef.current) {
      try {
        voiceNoteRecognitionRef.current.stop();
      } catch (e) {}
    }
  };

  const handleSaveVoiceNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !voiceNoteText.trim()) return;

    try {
      setSavingVoiceNote(true);
      setSubmitError(null);

      const formData = new FormData();
      formData.append('note_text', voiceNoteText.trim());
      formData.append('category', voiceNoteCategory);
      if (gpsLocation) {
        formData.append('latitude', String(gpsLocation.latitude));
        formData.append('longitude', String(gpsLocation.longitude));
        formData.append('accuracy_meters', String(gpsLocation.accuracy));
      }
      formData.append('location_name', locationName || 'Crime Scene Perimeter');
      formData.append('recorded_at', new Date().toISOString());
      formData.append('source_device', 'Investigator Mobile Voice Memo');

      if (voiceNoteAudioBlob) {
        formData.append('audio_file', voiceNoteAudioBlob, `voicenote_${Date.now()}.webm`);
      }

      const createdNote = await voiceNoteService.createVoiceNote(caseId, formData);
      setLatestSavedNote(createdNote);
      setVoiceNoteText('');
      setVoiceNoteAudioBlob(null);
      await loadCaseVoiceNotes();
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to save cited voice note');
    } finally {
      setSavingVoiceNote(false);
    }
  };

  const copyCitation = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCitation(code);
    setTimeout(() => setCopiedCitation(null), 2500);
  };

  return (
    <div className="min-h-screen bg-[#faf7f2] text-[#191410] pb-24 selection:bg-[#d93829] selection:text-white">
      {/* Top Mobile Bar */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-[#eae4d9] px-4 py-3 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-2.5">
          <Link
            to={`/cases/${caseId}/evidence`}
            className="p-1.5 rounded-xl bg-[#faf7f2] hover:bg-[#f0ebe1] border border-[#eae4d9] text-[#6e665d] hover:text-[#191410] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="text-[10px] uppercase font-bold tracking-widest text-[#d93829] font-mono flex items-center gap-1">
              <Smartphone className="w-3 h-3" />
              On-Scene Field & Audio Capture
            </div>
            <h1 className="text-sm font-bold text-[#191410] truncate max-w-[200px] sm:max-w-md">
              {currentCase ? currentCase.title || currentCase.name : `Case #${caseId}`}
            </h1>
          </div>
        </div>

        {/* Live Network & GPS Status Pills */}
        <div className="flex items-center gap-2">
          {/* Online/Offline Status */}
          <div className="flex items-center gap-1.5">
            {isOnline ? (
              <span className="px-2 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-mono flex items-center gap-1">
                <Wifi className="w-3 h-3" />
                <span className="hidden sm:inline">Online</span>
              </span>
            ) : (
              <span className="px-2 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-mono flex items-center gap-1">
                <WifiOff className="w-3 h-3 animate-pulse" />
                <span>Offline Mode</span>
              </span>
            )}

            {/* Offline Queue Badge */}
            {offlineQueue.length > 0 && (
              <button
                onClick={() => setQueueDrawerOpen(true)}
                className="px-2.5 py-1 rounded-full bg-red-50 hover:bg-red-100 border border-red-200 text-[#d93829] text-[10px] font-mono font-bold flex items-center gap-1 transition-all cursor-pointer"
                title="View Offline Queue"
              >
                <UploadCloud className="w-3 h-3" />
                <span>{offlineQueue.length} Queued</span>
              </button>
            )}
          </div>

          {/* GPS Pill */}
          {fetchingGps ? (
            <span className="px-2 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-mono flex items-center gap-1">
              <RefreshCw className="w-3 h-3 animate-spin" />
              GPS...
            </span>
          ) : gpsLocation ? (
            <span className="px-2 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-mono flex items-center gap-1" title={`±${gpsLocation.accuracy.toFixed(1)}m`}>
              <MapPin className="w-3 h-3" />
              <span className="hidden sm:inline">GPS Locked</span>
            </span>
          ) : (
            <button
              onClick={fetchCurrentLocation}
              className="px-2 py-1 rounded-full bg-red-50 border border-red-200 text-[#d93829] text-[10px] font-mono flex items-center gap-1 cursor-pointer"
            >
              <AlertTriangle className="w-3 h-3" />
              No GPS
            </button>
          )}
        </div>
      </header>

      {/* Main Tab Switcher */}
      <div className="max-w-xl mx-auto px-4 pt-4">
        <div className="flex rounded-2xl bg-white p-1 border border-[#eae4d9] shadow-xs">
          <button
            onClick={() => setActiveTab('media_capture')}
            className={cn(
              "flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer",
              activeTab === 'media_capture'
                ? "bg-[#d93829] text-white shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Camera className="w-4 h-4" />
            <span>Scene Media Capture</span>
          </button>
          <button
            onClick={() => setActiveTab('voice_notes')}
            className={cn(
              "flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer",
              activeTab === 'voice_notes'
                ? "bg-[#d93829] text-white shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Mic className="w-4 h-4" />
            <span>Quick Voice Notes</span>
            <span className="text-[10px] bg-white/20 px-1.5 py-0.2 rounded-full font-mono">
              Cited
            </span>
          </button>
        </div>
      </div>

      {/* Offline Mode Alert Banner */}
      {!isOnline && (
        <div className="max-w-xl mx-auto px-4 pt-3">
          <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <WifiOff className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Offline: Exhibits will be saved securely to local queue and synced when connection returns.</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Container */}
      <main className="max-w-xl mx-auto p-4 space-y-5">
        {activeTab === 'media_capture' ? (
          <>
            {/* SUCCESS CONFIRMATION: ONLINE UPLOAD */}
            {submittedEvidence && (
              <div className="p-6 rounded-3xl bg-white border border-emerald-300 shadow-md space-y-4 animate-in zoom-in-95">
                <div className="flex items-center gap-3 text-emerald-700">
                  <div className="w-10 h-10 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-[#191410]">Registered in Forensic Chain of Custody!</h3>
                    <p className="text-xs text-emerald-800">
                      Exhibit #{submittedEvidence.id} verified with on-device SHA-256 integrity.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-[#6e665d]">Filename:</span>
                    <span className="text-[#191410] font-bold truncate max-w-[200px]">{submittedEvidence.fileName || submittedEvidence.file_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6e665d]">On-Device SHA-256:</span>
                    <span className="text-emerald-700 font-bold">{submittedEvidence.file_hash?.substring(0, 16)}...</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6e665d]">Provenance:</span>
                    <span className="text-purple-700 font-bold">On-Scene Mobile Capture</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6e665d]">Custody Logs:</span>
                    <span className="text-amber-800 font-bold">FIELD_CAPTURE & INTAKE Recorded</span>
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    onClick={resetForm}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-white hover:bg-[#faf7f2] border border-[#eae4d9] text-[#191410] text-xs font-bold transition-all text-center cursor-pointer shadow-xs"
                  >
                    Capture Another
                  </button>
                  <Link
                    to={`/cases/${caseId}/evidence`}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-[#d93829] hover:bg-[#b82d20] text-white text-xs font-bold transition-all text-center flex items-center justify-center gap-1.5 shadow-xs"
                  >
                    <span>View Evidence Locker</span>
                  </Link>
                </div>
              </div>
            )}

            {/* SUCCESS CONFIRMATION: SAVED TO OFFLINE QUEUE */}
            {offlineSavedSuccess && !submittedEvidence && (
              <div className="p-6 rounded-3xl bg-white border border-amber-300 shadow-md space-y-4 animate-in zoom-in-95">
                <div className="flex items-center gap-3 text-amber-700">
                  <div className="w-10 h-10 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center">
                    <Bookmark className="w-6 h-6 text-amber-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-[#191410]">Saved to Local Offline Queue!</h3>
                    <p className="text-xs text-amber-800">
                      Tamper-evident SHA-256 and GPS saved locally. Will sync automatically when connection returns.
                    </p>
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    onClick={resetForm}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-white hover:bg-[#faf7f2] border border-[#eae4d9] text-[#191410] text-xs font-bold transition-all text-center cursor-pointer shadow-xs"
                  >
                    Capture Next Exhibit
                  </button>
                  <button
                    onClick={() => setQueueDrawerOpen(true)}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all text-center flex items-center justify-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <span>View Offline Queue ({offlineQueue.length})</span>
                  </button>
                </div>
              </div>
            )}

            {/* FORM: EVIDENCE CAPTURE */}
            {!submittedEvidence && !offlineSavedSuccess && (
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Mode Selector */}
                <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-wider text-[#191410] font-mono flex items-center gap-1.5">
                      <Camera className="w-4 h-4 text-[#d93829]" />
                      1. Scene Capture Mode
                    </label>
                    <div className="flex gap-1 bg-[#faf7f2] border border-[#eae4d9] p-0.5 rounded-lg text-[10px] font-semibold">
                      <button
                        type="button"
                        onClick={() => { setCaptureMode('photo'); stopLiveCamera(); }}
                        className={cn(
                          "px-2.5 py-1 rounded-md transition-all cursor-pointer",
                          captureMode === 'photo' ? "bg-[#d93829] text-white" : "text-[#6e665d] hover:text-[#191410]"
                        )}
                      >
                        Photo
                      </button>
                      <button
                        type="button"
                        onClick={() => { setCaptureMode('video'); stopLiveCamera(); }}
                        className={cn(
                          "px-2.5 py-1 rounded-md transition-all cursor-pointer",
                          captureMode === 'video' ? "bg-[#d93829] text-white" : "text-[#6e665d] hover:text-[#191410]"
                        )}
                      >
                        Video
                      </button>
                      <button
                        type="button"
                        onClick={() => { setCaptureMode('audio'); stopLiveCamera(); }}
                        className={cn(
                          "px-2.5 py-1 rounded-md transition-all cursor-pointer",
                          captureMode === 'audio' ? "bg-[#d93829] text-white" : "text-[#6e665d] hover:text-[#191410]"
                        )}
                      >
                        Audio
                      </button>
                      <button
                        type="button"
                        onClick={() => { setCaptureMode('file'); stopLiveCamera(); }}
                        className={cn(
                          "px-2.5 py-1 rounded-md transition-all cursor-pointer",
                          captureMode === 'file' ? "bg-[#d93829] text-white" : "text-[#6e665d] hover:text-[#191410]"
                        )}
                      >
                        File
                      </button>
                    </div>
                  </div>

                  {/* Viewfinder / Recorder Area */}
                  {captureMode === 'photo' && (
                    <div className="space-y-3">
                      {isLiveCameraActive ? (
                        <div className="relative rounded-2xl overflow-hidden bg-black border border-stone-800 aspect-video flex items-center justify-center">
                          <video
                            ref={cameraVideoRef}
                            autoPlay
                            playsInline
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute bottom-3 inset-x-0 flex items-center justify-center gap-3">
                            <button
                              type="button"
                              onClick={capturePhotoFrame}
                              className="w-14 h-14 rounded-full bg-white hover:bg-stone-200 border-4 border-[#d93829] flex items-center justify-center shadow-lg transition-transform active:scale-90 cursor-pointer"
                              title="Snap & Hash Photo"
                            >
                              <div className="w-10 h-10 rounded-full bg-[#d93829]" />
                            </button>
                            <button
                              type="button"
                              onClick={stopLiveCamera}
                              className="px-3 py-1.5 rounded-full bg-black/60 text-white text-xs border border-white/20 cursor-pointer"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={startLiveCamera}
                            className="p-5 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                          >
                            <Camera className="w-8 h-8 text-[#d93829]" />
                            <span className="text-xs font-bold">Open Camera Shutter</span>
                            <span className="text-[10px] text-[#6e665d]">Live on-scene snap</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="p-5 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                          >
                            <UploadCloud className="w-8 h-8 text-[#6e665d]" />
                            <span className="text-xs font-bold">Device Gallery / File</span>
                            <span className="text-[10px] text-[#6e665d]">Select stored file</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {captureMode === 'video' && (
                    <div className="space-y-3">
                      {isVideoRecording ? (
                        <div className="relative rounded-2xl overflow-hidden bg-black border border-rose-800 aspect-video flex flex-col items-center justify-center p-4">
                          <video
                            ref={cameraVideoRef}
                            autoPlay
                            playsInline
                            muted
                            className="w-full h-full object-cover rounded-xl"
                          />
                          <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-950/80 border border-rose-600 text-rose-300 text-xs font-mono font-bold animate-pulse">
                            <Radio className="w-3.5 h-3.5 text-rose-500 animate-spin" />
                            <span>REC {Math.floor(recordingDuration / 60)}:{(recordingDuration % 60).toString().padStart(2, '0')}</span>
                          </div>
                          <div className="absolute bottom-3 inset-x-0 flex justify-center">
                            <button
                              type="button"
                              onClick={stopVideoRecording}
                              className="px-6 py-2.5 rounded-full bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs flex items-center gap-2 shadow-xl cursor-pointer"
                            >
                              <Square className="w-4 h-4 fill-white" />
                              <span>Stop & Compute Hash</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={startVideoRecording}
                            className="p-5 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                          >
                            <Video className="w-8 h-8 text-[#d93829]" />
                            <span className="text-xs font-bold">Start Live Video</span>
                            <span className="text-[10px] text-[#6e665d]">Record scene walkthrough</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="p-5 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                          >
                            <UploadCloud className="w-8 h-8 text-[#6e665d]" />
                            <span className="text-xs font-bold">Choose Video File</span>
                            <span className="text-[10px] text-[#6e665d]">Select MP4/WebM</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {captureMode === 'audio' && (
                    <div className="space-y-3">
                      {isAudioRecording ? (
                        <div className="p-6 rounded-2xl bg-[#faf7f2] border border-rose-300 flex flex-col items-center justify-center gap-3">
                          <div className="flex items-center gap-2 text-rose-700 font-mono font-bold animate-pulse">
                            <Radio className="w-4 h-4 text-rose-600 animate-spin" />
                            <span>RECORDING AUDIO: {Math.floor(recordingDuration / 60)}:{(recordingDuration % 60).toString().padStart(2, '0')}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                              <div key={i} className="w-1.5 h-6 bg-rose-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.1}s` }} />
                            ))}
                          </div>
                          <button
                            type="button"
                            onClick={stopAudioRecording}
                            className="px-6 py-2 rounded-full bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs flex items-center gap-2 shadow-lg cursor-pointer"
                          >
                            <Square className="w-4 h-4 fill-white" />
                            <span>Stop & Save Audio</span>
                          </button>
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={startAudioRecording}
                            className="p-5 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                          >
                            <Mic className="w-8 h-8 text-[#d93829]" />
                            <span className="text-xs font-bold">Record Scene Audio</span>
                            <span className="text-[10px] text-[#6e665d]">Live microphone memo</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="p-5 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                          >
                            <UploadCloud className="w-8 h-8 text-[#6e665d]" />
                            <span className="text-xs font-bold">Choose Audio File</span>
                            <span className="text-[10px] text-[#6e665d]">Select WAV/MP3/M4A</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {captureMode === 'file' && (
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full p-8 rounded-2xl border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] hover:bg-white flex flex-col items-center justify-center gap-2 text-[#191410] transition-all cursor-pointer shadow-xs"
                    >
                      <UploadCloud className="w-10 h-10 text-[#d93829]" />
                      <span className="text-xs font-bold">Select Scene File / Document</span>
                      <span className="text-[10px] text-[#6e665d]">PDF, images, audio, video</span>
                    </button>
                  )}

                  {/* Hidden File Input */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,video/*,audio/*,.pdf,.txt"
                    onChange={handleFileSelected}
                    className="hidden"
                  />

                  {/* Preview Banner */}
                  {previewUrl && (
                    <div className="p-3 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 truncate">
                        {evidenceType === 'photograph' && (
                          <img src={previewUrl} alt="Preview" className="w-12 h-12 rounded-xl object-cover border border-[#eae4d9]" />
                        )}
                        {evidenceType === 'video' && (
                          <video src={previewUrl} controls className="w-20 h-12 rounded-xl object-cover border border-[#eae4d9]" />
                        )}
                        {evidenceType === 'audio' && (
                          <audio src={previewUrl} controls className="h-8 max-w-[180px]" />
                        )}
                        <div className="truncate">
                          <div className="text-xs font-bold text-[#191410] truncate">{title || 'Captured Exhibit'}</div>
                          <div className="text-[10px] text-[#6e665d] font-mono">
                            {capturedBlob ? `${(capturedBlob.size / 1024).toFixed(1)} KB` : ''} • {evidenceType.toUpperCase()}
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => { setCapturedBlob(null); setPreviewUrl(null); setClientHash(''); }}
                        className="p-1 rounded-lg bg-stone-100 hover:bg-stone-200 text-[#6e665d] hover:text-[#191410] cursor-pointer"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  )}

                  {/* Cryptographic SHA-256 Hash Card */}
                  {hashingInProgress && (
                    <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2 font-mono">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600" />
                      <span>Computing on-device SHA-256 cryptographic hash...</span>
                    </div>
                  )}

                  {clientHash && !hashingInProgress && (
                    <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs space-y-1 font-mono">
                      <div className="flex items-center justify-between">
                        <span className="font-bold flex items-center gap-1 text-[11px] uppercase tracking-wider text-emerald-800">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          On-Device SHA-256 Verified
                        </span>
                        <span className="text-[10px] text-[#6e665d]">WebCrypto API</span>
                      </div>
                      <div className="text-[10px] text-emerald-900 break-all bg-white p-2 rounded-lg border border-emerald-200">
                        {clientHash}
                      </div>
                    </div>
                  )}
                </div>

                {/* Step 2: Geo-Temporal & Custody Metadata */}
                <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#191410] font-mono flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-[#d93829]" />
                    2. Geo-Temporal Forensics
                  </label>

                  <div>
                    <label className="text-[11px] font-bold text-[#6e665d] block mb-1">Exhibit Title</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Broken Balcony Latch / Recovered Mobile SIM"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] focus:outline-hidden focus:border-[#d93829] focus:bg-white"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-bold text-[#6e665d] block mb-1">Location Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Master Bedroom, Flat 402"
                        value={locationName}
                        onChange={(e) => setLocationName(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] focus:outline-hidden focus:border-[#d93829] focus:bg-white"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-bold text-[#6e665d] block mb-1">Tamper Seal Number</label>
                      <input
                        type="text"
                        placeholder="e.g. SEAL-SOCO-2026-881"
                        value={tamperSealNumber}
                        onChange={(e) => setTamperSealNumber(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] focus:outline-hidden focus:border-[#d93829] focus:bg-white"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-[#6e665d] block mb-1">Recovery & Custody Notes</label>
                    <textarea
                      rows={2}
                      placeholder="e.g. Seized from underneath north floorboards during initial search."
                      value={custodyNotes}
                      onChange={(e) => setCustodyNotes(e.target.value)}
                      className="w-full p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] focus:outline-hidden focus:border-[#d93829] focus:bg-white"
                    />
                  </div>
                </div>

                {/* Step 3: Legal Integrity Certification (Sec 63/65B IEA / 61 BSA) */}
                <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-3">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#191410] font-mono flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    3. Legal Certification Declaration
                  </label>

                  <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[11px] font-mono text-[#191410] leading-relaxed">
                    {officerDeclaration}
                  </div>

                  <label className="flex items-start gap-2.5 pt-1 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={officerConfirmed}
                      onChange={(e) => setOfficerConfirmed(e.target.checked)}
                      className="mt-0.5 w-4 h-4 rounded text-[#d93829] focus:ring-0 focus:outline-hidden accent-[#d93829]"
                    />
                    <span className="text-xs text-[#191410] font-medium">
                      I solemnly affirm and verify under official duty that this exhibit was captured directly at the crime scene and has not been altered or tampered with in any manner.
                    </span>
                  </label>
                </div>

                {/* Submit / Save to Offline Queue Button */}
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={submitting || hashingInProgress || !capturedBlob || !officerConfirmed}
                    className={cn(
                      "w-full py-3.5 px-6 rounded-2xl text-xs font-bold text-white shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-98",
                      submitting || hashingInProgress || !capturedBlob || !officerConfirmed
                        ? "bg-stone-300 text-stone-500 cursor-not-allowed"
                        : isOnline
                          ? "bg-[#d93829] hover:bg-[#b82d20]"
                          : "bg-amber-600 hover:bg-amber-700"
                    )}
                  >
                    {submitting ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Verifying & Recording Chain of Custody...</span>
                      </>
                    ) : isOnline ? (
                      <>
                        <ShieldCheck className="w-4 h-4" />
                        <span>Submit to Central Evidence Enclave</span>
                      </>
                    ) : (
                      <>
                        <Bookmark className="w-4 h-4" />
                        <span>Save to Local Offline Queue ({offlineQueue.length} Pending)</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </>
        ) : (
          /* ============================================================================== */
          /* QUICK VOICE NOTES TAB (CITED CASE NOTES)                                       */
          /* ============================================================================== */
          <div className="space-y-5">
            {/* Voice Dictation Card */}
            <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-[#191410] flex items-center gap-2">
                    <Mic className="w-4 h-4 text-[#d93829]" />
                    <span>Quick Voice Note Dictation</span>
                  </h3>
                  <p className="text-[11px] text-[#6e665d] mt-0.5">
                    Speak observations or leads. Audio is transcribed and anchored into cited case notes.
                  </p>
                </div>

                {/* Big Record Button */}
                <button
                  type="button"
                  onClick={isVoiceNoteRecording ? stopVoiceNoteRecording : startVoiceNoteRecording}
                  className={cn(
                    "w-12 h-12 rounded-full flex items-center justify-center shadow-xs transition-transform active:scale-95 cursor-pointer font-bold shrink-0",
                    isVoiceNoteRecording
                      ? "bg-rose-600 hover:bg-rose-700 text-white animate-pulse"
                      : "bg-[#d93829] hover:bg-[#b82d20] text-white"
                  )}
                  title={isVoiceNoteRecording ? "Stop Dictation" : "Start Voice Dictation"}
                >
                  {isVoiceNoteRecording ? <Square className="w-5 h-5 fill-white" /> : <Mic className="w-5 h-5" />}
                </button>
              </div>

              {/* Live Speech Recognition Transcript */}
              {isVoiceNoteRecording && (
                <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-xs space-y-1 animate-pulse">
                  <div className="flex items-center gap-1.5 text-rose-700 font-bold text-[11px] uppercase tracking-wider">
                    <Radio className="w-3.5 h-3.5 text-rose-600 animate-spin" />
                    <span>Transcribing Voice Memo in Real-Time:</span>
                  </div>
                  <p className="text-[#191410] font-medium italic text-sm">
                    {voiceNoteInterim || "Listening... Speak your observations clearly into the microphone."}
                  </p>
                </div>
              )}

              {/* Dictated Note Text Area */}
              <div>
                <label className="text-[11px] font-bold text-[#6e665d] block mb-1">
                  Dictated Note Content (Editable)
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Your spoken observations will appear here automatically, or you can type directly..."
                  value={voiceNoteText}
                  onChange={(e) => setVoiceNoteText(e.target.value)}
                  className="w-full p-3.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] focus:outline-hidden focus:border-[#d93829] focus:bg-white leading-relaxed"
                />
              </div>

              {/* Category Selector */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-[#6e665d]">Category:</span>
                  <select
                    value={voiceNoteCategory}
                    onChange={(e) => setVoiceNoteCategory(e.target.value)}
                    className="px-2.5 py-1.5 text-xs rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410] focus:outline-hidden"
                  >
                    <option value="field_observation">Field Observation</option>
                    <option value="suspect_statement">Suspect Remark / Spontaneous Admission</option>
                    <option value="witness_lead">Witness Lead</option>
                    <option value="forensic_note">Forensic Specimen Note</option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleSaveVoiceNote}
                  disabled={savingVoiceNote || !voiceNoteText.trim()}
                  className={cn(
                    "py-2.5 px-5 rounded-xl text-xs font-bold text-white shadow-xs transition-all flex items-center gap-2 cursor-pointer active:scale-95",
                    savingVoiceNote || !voiceNoteText.trim()
                      ? "bg-stone-300 text-stone-500 cursor-not-allowed"
                      : "bg-emerald-600 hover:bg-emerald-700"
                  )}
                >
                  {savingVoiceNote ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Anchoring Citation...</span>
                    </>
                  ) : (
                    <>
                      <Bookmark className="w-3.5 h-3.5" />
                      <span>Save Cited Case Note</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* LATEST SAVED CITED NOTE CONFIRMATION */}
            {latestSavedNote && (
              <div className="p-5 rounded-3xl bg-white border border-emerald-300 shadow-md space-y-3 animate-in zoom-in-95">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-emerald-700 font-bold text-xs uppercase tracking-wider">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Cited Case Note Created & Anchored!</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLatestSavedNote(null)}
                    className="text-[#6e665d] hover:text-[#191410] cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-3 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-bold text-amber-800">
                      {latestSavedNote.citation_code}
                    </span>
                    <button
                      onClick={() => copyCitation(latestSavedNote.citation_code)}
                      className="px-2 py-0.5 rounded-md bg-white hover:bg-stone-100 border border-[#eae4d9] text-[#191410] text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                    >
                      {copiedCitation === latestSavedNote.citation_code ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedCitation === latestSavedNote.citation_code ? 'Copied' : 'Copy Citation'}</span>
                    </button>
                  </div>
                  <p className="italic text-xs text-[#191410]">
                    "{latestSavedNote.note_text}"
                  </p>
                  <div className="flex flex-wrap items-center gap-3 pt-1 text-[10px] font-mono text-[#6e665d]">
                    <span>Officer: {latestSavedNote.officer_name}</span>
                    {latestSavedNote.latitude && (
                      <span>GPS: ({latestSavedNote.latitude.toFixed(4)}, {latestSavedNote.longitude?.toFixed(4)})</span>
                    )}
                    <span>Anchors: {latestSavedNote.citations.length} chunks</span>
                  </div>
                </div>
              </div>
            )}

            {/* RECENT CASE VOICE NOTES LIST */}
            <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#191410] font-mono flex items-center gap-1.5">
                  <Bookmark className="w-3.5 h-3.5 text-amber-600" />
                  <span>Docket Voice Notes ({voiceNotes.length})</span>
                </h4>
                <button
                  onClick={loadCaseVoiceNotes}
                  className="text-[10px] text-[#6e665d] hover:text-[#191410] flex items-center gap-1 cursor-pointer"
                >
                  <RefreshCw className={cn("w-3 h-3 text-[#d93829]", loadingVoiceNotes && "animate-spin")} />
                  <span>Refresh</span>
                </button>
              </div>

              {loadingVoiceNotes ? (
                <div className="py-6 text-center text-xs text-[#6e665d]">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-[#d93829]" />
                  Loading case voice notes...
                </div>
              ) : voiceNotes.length === 0 ? (
                <div className="py-6 text-center text-xs text-[#6e665d]">
                  No voice notes recorded yet for this case. Dictate observations above to generate cited notes.
                </div>
              ) : (
                <div className="space-y-3">
                  {voiceNotes.map(n => (
                    <div key={n.id} className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono font-bold text-amber-800">
                          {n.citation_code}
                        </span>
                        <button
                          onClick={() => copyCitation(n.citation_code)}
                          className="px-2 py-0.5 rounded-md bg-white hover:bg-stone-100 border border-[#eae4d9] text-[#191410] text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                        >
                          {copiedCitation === n.citation_code ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedCitation === n.citation_code ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>

                      <p className="text-xs text-[#191410] leading-relaxed">
                        {n.note_text}
                      </p>

                      {/* Audio Player if audio was recorded */}
                      {n.audio_path && (
                        <div className="pt-1">
                          <audio src={`/api/files/${n.audio_path.split('/').pop()}`} controls className="h-7 w-full" />
                        </div>
                      )}

                      <div className="flex flex-wrap items-center justify-between text-[10px] font-mono text-[#6e665d] pt-1 border-t border-[#eae4d9]">
                        <span>{n.officer_name} • {new Date(n.recorded_at).toLocaleDateString()}</span>
                        {n.location_name && <span className="truncate max-w-[160px]">{n.location_name}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* OFFLINE QUEUE DRAWER */}
      {queueDrawerOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#eae4d9] rounded-3xl w-full max-w-md p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-[#d93829]" />
                <h3 className="font-serif font-bold text-sm text-[#191410]">Offline Evidence Queue</h3>
                <span className="px-2 py-0.5 rounded-full bg-stone-100 border border-[#eae4d9] text-[10px] font-mono font-bold text-[#191410]">
                  {offlineQueue.length} items
                </span>
              </div>
              <button
                onClick={() => setQueueDrawerOpen(false)}
                className="text-[#6e665d] hover:text-[#191410] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-[#6e665d] leading-relaxed">
              These exhibits were captured while disconnected. On-device SHA-256 hashes and GPS stamps were locked at the time of capture.
            </p>

            {offlineQueue.length === 0 ? (
              <div className="py-8 text-center text-xs text-[#6e665d]">
                Queue is empty. All exhibits synced to central docket.
              </div>
            ) : (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {offlineQueue.map(item => (
                  <div key={item.id} className="p-3 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#191410] truncate max-w-[200px]">{item.title}</span>
                      <span className={cn(
                        "text-[10px] uppercase font-bold px-2 py-0.5 rounded-full",
                        item.syncStatus === 'synced' ? "bg-emerald-50 text-emerald-800 border border-emerald-200" :
                        item.syncStatus === 'syncing' ? "bg-blue-50 text-blue-800 border border-blue-200 animate-pulse" :
                        item.syncStatus === 'failed' ? "bg-red-50 text-red-800 border border-red-200" :
                        "bg-amber-50 text-amber-800 border border-amber-200"
                      )}>
                        {item.syncStatus}
                      </span>
                    </div>
                    <div className="text-[10px] text-[#6e665d] flex justify-between">
                      <span>SHA-256: {item.clientHash.substring(0, 12)}...</span>
                      <span>{(item.fileSize / 1024).toFixed(1)} KB</span>
                    </div>
                    {item.syncError && (
                      <div className="text-[10px] text-red-700">{item.syncError}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2 pt-2 border-t border-[#eae4d9]">
              <button
                onClick={() => setQueueDrawerOpen(false)}
                className="flex-1 py-2.5 px-4 rounded-xl border border-[#eae4d9] hover:bg-[#faf7f2] text-[#191410] text-xs font-bold transition-all cursor-pointer"
              >
                Close
              </button>
              {isOnline && offlineQueue.length > 0 && (
                <button
                  onClick={syncAllOfflineItems}
                  disabled={syncingQueue}
                  className="flex-1 py-2.5 px-4 rounded-xl bg-[#d93829] hover:bg-[#b82d20] text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-xs"
                >
                  {syncingQueue ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
                  <span>Sync Queue Now</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
