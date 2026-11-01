import { useParams } from 'react-router-dom';
import { useState, useEffect, useMemo, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Mic, PlayCircle, PauseCircle, FileText, Clock, Search, 
  Upload, Tag, AlertTriangle, CheckCircle2, User, Volume2, 
  Share2, Download, Plus, Filter, ShieldCheck, HelpCircle,
  Sparkles, ArrowRight, Link as LinkIcon, RefreshCw, X, AlertCircle, ChevronDown, ChevronUp,
  Radio, MicOff, Activity, ShieldAlert, Check
} from 'lucide-react';
import { cn } from '../../utils';
import { interviewService, jobService } from '../../services';
import { 
  InterviewSession, 
  InterviewStatement, 
  InterviewContradiction, 
  SuggestedQuestion 
} from '../../types';

export function Interviews() {
  const { caseId } = useParams<{ caseId: string }>();
  
  // State
  const [interviews, setInterviews] = useState<InterviewSession[]>([]);
  const [selectedInterviewId, setSelectedInterviewId] = useState<number | null>(null);
  const [activeInterview, setActiveInterview] = useState<InterviewSession | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<SuggestedQuestion[]>([]);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [questionsLoading, setQuestionsLoading] = useState<boolean>(false);
  const [analyzingStatement, setAnalyzingStatement] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Audio simulation
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentSeconds, setCurrentSeconds] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Suggested questions filter
  const [questionCategoryFilter, setQuestionCategoryFilter] = useState<'all' | 'contradiction' | 'gap' | 'alibi'>('all');
  const [isQuestionsPanelOpen, setIsQuestionsPanelOpen] = useState<boolean>(true);

  // New statement recording form
  const [activeQuestion, setActiveQuestion] = useState<string>('');
  const [questionSourceType, setQuestionSourceType] = useState<string>('manual');
  const [questionSourceId, setQuestionSourceId] = useState<string>('');
  const [answerText, setAnswerText] = useState<string>('');
  const [speakerRole, setSpeakerRole] = useState<'interviewee' | 'investigator' | 'counsel'>('interviewee');

  // Immediate contradiction highlight banner
  const [latestFlaggedContradiction, setLatestFlaggedContradiction] = useState<InterviewContradiction | null>(null);

  // Inspection modal for contradiction details
  const [inspectingContradiction, setInspectingContradiction] = useState<InterviewContradiction | null>(null);

  // Live Audio Streaming & Rolling Transcription Studio State
  const [studioTab, setStudioTab] = useState<'stream' | 'manual'>('stream');
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(false);
  const [liveStreamSeconds, setLiveStreamSeconds] = useState<number>(0);
  const [liveSpeaker, setLiveSpeaker] = useState<'interviewee' | 'investigator'>('interviewee');
  const [liveInterimText, setLiveInterimText] = useState<string>('');
  const [liveStatusText, setLiveStatusText] = useState<string>('Ready to stream live audio');
  const [micAudioLevel, setMicAudioLevel] = useState<number>(0);

  const recognitionRef = useRef<any>(null);
  const streamTimerRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<any>(null);

  // New Interview Modal
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [newInterviewee, setNewInterviewee] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('suspect');
  const [newInterviewer, setNewInterviewer] = useState<string>('Lead Investigating Officer');

  // Clean-up streaming on unmount
  useEffect(() => {
    return () => {
      stopLiveStreaming();
    };
  }, []);

  // Subscribe to live SSE interview events for rolling synchronization
  useEffect(() => {
    if (!caseId || !activeInterview) return;
    const unsub = jobService.subscribeCaseEvents(caseId, (event: any) => {
      if (
        event?.event_type === 'interview.live_statement' ||
        event?.event_type === 'interview.statement_contradiction'
      ) {
        const payload = event?.payload;
        if (payload && payload.interview_id === activeInterview.id && payload.statement) {
          setActiveInterview(prev => {
            if (!prev) return prev;
            if (prev.statements?.some(s => s.id === payload.statement.id)) {
              return prev;
            }
            const updatedStmts = [...(prev.statements || []), payload.statement];
            const updatedContras = payload.new_contradictions?.length
              ? [...(prev.contradictions || []), ...payload.new_contradictions]
              : (prev.contradictions || []);
            return {
              ...prev,
              statement_count: updatedStmts.length,
              contradiction_count: updatedContras.length,
              statements: updatedStmts,
              contradictions: updatedContras
            };
          });

          if (payload.has_contradiction && payload.new_contradictions?.length > 0) {
            setLatestFlaggedContradiction(payload.new_contradictions[0]);
          }
        }
      }
    });
    return () => {
      if (unsub) unsub();
    };
  }, [caseId, activeInterview?.id]);

  // Load interviews list on mount or caseId change
  useEffect(() => {
    if (!caseId) return;
    loadInterviews();
  }, [caseId]);

  const loadInterviews = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await interviewService.getCaseInterviews(caseId);
      setInterviews(data);
      if (data.length > 0) {
        const targetId = selectedInterviewId || data[0].id;
        setSelectedInterviewId(targetId);
        await loadInterviewDetail(targetId);
      }
    } catch (err: any) {
      console.error('Failed to load case interviews:', err);
      setError(err?.message || 'Failed to load case interview records');
    } finally {
      setLoading(false);
    }
  };

  const loadInterviewDetail = async (id: number) => {
    if (!caseId) return;
    try {
      const detail = await interviewService.getInterviewDetail(caseId, id);
      setActiveInterview(detail);
      loadQuestions(detail.interviewee_name, id);
    } catch (err) {
      console.error('Failed to fetch interview detail:', err);
    }
  };

  const loadQuestions = async (subjectName?: string, intId?: number) => {
    if (!caseId) return;
    setQuestionsLoading(true);
    try {
      const questions = await interviewService.getSuggestedQuestions(caseId, subjectName, intId);
      setSuggestedQuestions(questions);
    } catch (err) {
      console.error('Failed to load suggested questions:', err);
    } finally {
      setQuestionsLoading(false);
    }
  };

  // Audio scrubber interval
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentSeconds(prev => (prev >= 600 ? 0 : prev + 1));
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleSelectInterview = (intSession: InterviewSession) => {
    setSelectedInterviewId(intSession.id);
    setCurrentSeconds(0);
    setIsPlaying(false);
    setLatestFlaggedContradiction(null);
    loadInterviewDetail(intSession.id);
  };

  const handleApplyQuestion = (q: SuggestedQuestion) => {
    setActiveQuestion(q.question);
    setQuestionSourceType(q.category);
    setQuestionSourceId(q.source_id || q.id);
    // Smooth scroll down to response studio
    const studio = document.getElementById('response-recording-studio');
    if (studio) {
      studio.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleRecordStatement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !activeInterview || !answerText.trim()) return;

    setAnalyzingStatement(true);
    setError(null);
    try {
      const timestampMarker = formatSeconds(currentSeconds);
      const res = await interviewService.addStatementAndAnalyze(caseId, activeInterview.id, {
        speaker: activeInterview.interviewee_name,
        role: speakerRole,
        timestamp_marker: timestampMarker,
        seconds: currentSeconds,
        question: activeQuestion.trim() || undefined,
        question_source_type: questionSourceType,
        question_source_id: questionSourceId,
        text: answerText.trim(),
        tag: questionSourceType !== 'manual' ? `${questionSourceType.toUpperCase()} INQUIRY` : undefined
      });

      // Update statement list in active interview
      setActiveInterview(prev => {
        if (!prev) return prev;
        const updatedStatements = [...(prev.statements || []), res.statement];
        const updatedContradictions = res.new_contradictions.length > 0 
          ? [...(prev.contradictions || []), ...res.new_contradictions]
          : (prev.contradictions || []);
        return {
          ...prev,
          statement_count: updatedStatements.length,
          contradiction_count: updatedContradictions.length,
          statements: updatedStatements,
          contradictions: updatedContradictions
        };
      });

      // If a contradiction was flagged, set the alert banner
      if (res.has_contradiction && res.new_contradictions.length > 0) {
        setLatestFlaggedContradiction(res.new_contradictions[0]);
      } else {
        setLatestFlaggedContradiction(null);
      }

      // Reset form fields
      setAnswerText('');
      setActiveQuestion('');
      setQuestionSourceType('manual');
      setQuestionSourceId('');

      // Refresh list to update count badges
      const updatedList = await interviewService.getCaseInterviews(caseId);
      setInterviews(updatedList);
    } catch (err: any) {
      console.error('Error analyzing statement:', err);
      setError(err?.message || 'Failed to record statement');
    } finally {
      setAnalyzingStatement(false);
    }
  };

  const startLiveStreaming = async () => {
    if (!caseId || !activeInterview) return;
    setError(null);
    setLiveStatusText('Requesting microphone access...');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        const ctx = new AudioCtx();
        audioContextRef.current = ctx;
        const src = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 64;
        src.connect(analyser);
        analyserRef.current = analyser;

        const pData = new Uint8Array(analyser.frequencyBinCount);
        const checkLevel = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getByteFrequencyData(pData);
          let sum = 0;
          for (let i = 0; i < pData.length; i++) sum += pData[i];
          const avg = sum / pData.length;
          setMicAudioLevel(Math.min(100, Math.round(avg * 1.5)));
          animFrameRef.current = requestAnimationFrame(checkLevel);
        };
        checkLevel();
      } catch (e) {
        console.warn('Audio analyser unavailable:', e);
      }

      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setLiveStatusText('Live Web Speech API not supported in this browser. Please use Google Chrome or Edge.');
      } else {
        const recog = new SpeechRecognition();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = 'en-US';

        recog.onresult = async (event: any) => {
          let interim = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              setLiveInterimText('');
              await handleSendRollingStatement(transcript.trim());
            } else {
              interim += transcript;
            }
          }
          if (interim) {
            setLiveInterimText(interim);
          }
        };

        recog.onerror = (e: any) => {
          console.warn('SpeechRecognition error:', e.error);
          if (e.error === 'not-allowed') {
            setError('Microphone access was denied. Please allow microphone permissions.');
            stopLiveStreaming();
          }
        };

        recog.onend = () => {
          if (recognitionRef.current && isLiveStreaming) {
            try {
              recog.start();
            } catch (err) {}
          }
        };

        recog.start();
        recognitionRef.current = recog;
      }

      setIsLiveStreaming(true);
      setLiveStreamSeconds(0);
      setLiveStatusText('Streaming live interview audio. Detecting contradictions in real time...');

      streamTimerRef.current = setInterval(() => {
        setLiveStreamSeconds(prev => prev + 1);
      }, 1000);

    } catch (err: any) {
      console.error('Failed to start live stream:', err);
      setError(err?.message || 'Failed to access microphone for live interview streaming');
      stopLiveStreaming();
    }
  };

  const stopLiveStreaming = () => {
    setIsLiveStreaming(false);
    setLiveStatusText('Stream stopped');
    setMicAudioLevel(0);
    setLiveInterimText('');

    if (streamTimerRef.current) {
      clearInterval(streamTimerRef.current);
      streamTimerRef.current = null;
    }

    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    }

    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch (e) {}
      audioContextRef.current = null;
    }
  };

  const handleSendRollingStatement = async (text: string) => {
    if (!caseId || !activeInterview || !text.trim()) return;

    try {
      const timestampMarker = formatSeconds(liveStreamSeconds || currentSeconds);
      const speakerName = liveSpeaker === 'interviewee' 
        ? activeInterview.interviewee_name 
        : (activeInterview.interviewer_name || 'Investigating Officer');

      const formData = new FormData();
      formData.append('transcript_text', text);
      formData.append('speaker', speakerName);
      formData.append('role', liveSpeaker);
      formData.append('timestamp_marker', timestampMarker);
      formData.append('seconds', String(liveStreamSeconds || currentSeconds));
      if (activeQuestion) {
        formData.append('question', activeQuestion);
        formData.append('question_source_type', questionSourceType);
        if (questionSourceId) formData.append('question_source_id', questionSourceId);
      }

      const res = await interviewService.streamLiveChunk(caseId, activeInterview.id, formData);

      setActiveInterview(prev => {
        if (!prev) return prev;
        const exists = prev.statements?.some(s => s.id === res.statement.id);
        const updatedStatements = exists ? prev.statements! : [...(prev.statements || []), res.statement];
        const updatedContras = res.new_contradictions.length > 0 
          ? [...(prev.contradictions || []), ...res.new_contradictions]
          : (prev.contradictions || []);
        return {
          ...prev,
          statement_count: updatedStatements.length,
          contradiction_count: updatedContras.length,
          statements: updatedStatements,
          contradictions: updatedContras
        };
      });

      if (res.has_contradiction && res.new_contradictions.length > 0) {
        setLatestFlaggedContradiction(res.new_contradictions[0]);
      }
    } catch (err: any) {
      console.error('Failed to post rolling statement:', err);
    }
  };

  const handleCreateInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !newInterviewee.trim()) return;

    try {
      const created = await interviewService.createInterview(caseId, {
        interviewee_name: newInterviewee.trim(),
        interviewee_role: newRole,
        interviewer_name: newInterviewer.trim() || 'Investigating Officer',
        interview_date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        duration: '00:00 mins',
        status: 'Active'
      });

      setShowUploadModal(false);
      setNewInterviewee('');
      await loadInterviews();
      setSelectedInterviewId(created.id);
      await loadInterviewDetail(created.id);
    } catch (err: any) {
      console.error('Failed to create interview:', err);
      setError(err?.message || 'Failed to create new interview session');
    }
  };

  // Filter suggested questions
  const filteredQuestions = useMemo(() => {
    if (questionCategoryFilter === 'all') return suggestedQuestions;
    return suggestedQuestions.filter(q => q.category === questionCategoryFilter);
  }, [suggestedQuestions, questionCategoryFilter]);

  // Filter statements by search query
  const filteredStatements = useMemo(() => {
    if (!activeInterview?.statements) return [];
    if (!searchQuery.trim()) return activeInterview.statements;
    const q = searchQuery.toLowerCase();
    return activeInterview.statements.filter(s => 
      s.text.toLowerCase().includes(q) ||
      s.speaker.toLowerCase().includes(q) ||
      (s.question && s.question.toLowerCase().includes(q))
    );
  }, [activeInterview, searchQuery]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 text-[#191410]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[#eae4d9] pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#d93829] animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#d93829]">
              Forensic Interrogation & Deposition Analysis
            </span>
          </div>
          <h1 className="text-2xl font-serif font-bold text-[#191410]">Interviews & Judicial Statements</h1>
          <p className="text-xs text-[#6e665d] mt-1">
            Interrogation studio with AI question synthesis from case contradictions, investigative gaps, and unverified alibis with real-time claim cross-comparison.
          </p>
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-[#d93829] text-white rounded-full hover:bg-[#bf2b1d] transition-all font-semibold text-xs shadow-sm flex items-center gap-2 cursor-pointer active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>New Deposition Session</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-red-700">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Grid: Catalog + Interactive Studio */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Recording Catalog */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between mb-2 px-1">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#6e665d]">
              Case Sessions ({interviews.length})
            </h2>
            <span className="text-[10px] text-[#6e665d] bg-white px-2 py-0.5 rounded-md border border-[#eae4d9]">
              Sec 63 BSA / 65B Certified
            </span>
          </div>
          
          <div className="space-y-2.5">
            {loading ? (
              <div className="p-8 text-center text-xs text-[#6e665d] bg-white rounded-2xl border border-[#eae4d9]">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#d93829]" />
                Loading case recordings...
              </div>
            ) : interviews.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#6e665d] bg-white rounded-2xl border border-[#eae4d9]">
                No recorded interviews found for this case. Click + New Deposition Session above.
              </div>
            ) : (
              interviews.map((rec) => {
                const isSelected = activeInterview?.id === rec.id;
                const hasContradictions = (rec.contradiction_count || 0) > 0;
                return (
                  <div
                    key={rec.id}
                    onClick={() => handleSelectInterview(rec)}
                    className={cn(
                      "p-4 rounded-2xl border transition-all cursor-pointer text-left",
                      isSelected 
                        ? "bg-white border-[#d93829] shadow-md ring-1 ring-[#d93829]/20" 
                        : "bg-white/80 border-[#eae4d9] hover:bg-white hover:border-[#6e665d]/40"
                    )}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2.5">
                        <div className={cn(
                          "w-9 h-9 rounded-full flex items-center justify-center shrink-0",
                          isSelected ? "bg-[#d93829]/10 text-[#d93829]" : "bg-[#f5f0e6] text-[#6e665d]"
                        )}>
                          <Mic className="w-4 h-4" />
                        </div>
                        <div>
                          <h3 className="text-xs font-serif font-bold text-[#191410] leading-snug">
                            {rec.interviewee_name}
                          </h3>
                          <span className={cn(
                            "text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded",
                            rec.interviewee_role === 'suspect' ? "bg-red-50 text-red-700 border border-red-200" :
                            rec.interviewee_role === 'approver' ? "bg-purple-50 text-purple-700 border border-purple-200" :
                            "bg-amber-50 text-amber-700 border border-amber-200"
                          )}>
                            {rec.interviewee_role}
                          </span>
                        </div>
                      </div>
                      
                      {hasContradictions && (
                        <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full bg-red-100 text-red-800 border border-red-300 flex items-center gap-1 animate-pulse">
                          <AlertTriangle className="w-2.5 h-2.5" />
                          {rec.contradiction_count} Conflicts
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-2.5 border-t border-[#f0ebe1] text-[10px] text-[#6e665d]">
                      <span className="font-mono">{rec.session_code} • {rec.interview_date || 'N/A'}</span>
                      <span className="font-semibold text-[#191410] bg-[#faf7f2] px-2 py-0.5 rounded border border-[#eae4d9]">
                        {rec.statement_count || 0} statements
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Audio Scrubber, Suggested Questions, Response Studio, & Transcript */}
        <div className="lg:col-span-8 space-y-5">
          {activeInterview && (
            <>
              {/* Header & Functional Audio Player */}
              <Card className="border border-[#eae4d9] shadow-sm bg-white overflow-hidden">
                <div className="px-6 py-4 bg-[#faf7f2]/60 border-b border-[#eae4d9] flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] font-mono text-[#6e665d] uppercase tracking-wider">
                      {activeInterview.session_code} • Recorded by {activeInterview.interviewer_name}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <h2 className="text-base font-serif font-bold text-[#191410]">
                        {activeInterview.interviewee_name}
                      </h2>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-[#eae4d9]/50 text-[#6e665d]">
                        {activeInterview.interviewee_role}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => window.print()}
                      className="px-3 py-1.5 rounded-lg border border-[#eae4d9] bg-white text-xs font-semibold text-[#191410] hover:bg-[#f5f0e6] transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
                    >
                      <FileText className="w-3.5 h-3.5 text-[#6e665d]" />
                      <span>Print Docket</span>
                    </button>
                  </div>
                </div>

                {/* Audio Scrubber Bar */}
                <div className="p-4 bg-white flex flex-col gap-2">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="w-10 h-10 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white flex items-center justify-center shadow-sm transition-transform active:scale-95 cursor-pointer shrink-0"
                      title={isPlaying ? "Pause" : "Play"}
                    >
                      {isPlaying ? <PauseCircle className="w-6 h-6" /> : <PlayCircle className="w-6 h-6" />}
                    </button>

                    <div className="flex-1 space-y-1">
                      <div className="flex justify-between text-[11px] font-mono text-[#6e665d]">
                        <span className="font-bold text-[#d93829]">{formatSeconds(currentSeconds)}</span>
                        <span>{activeInterview.duration || '42:15 mins'}</span>
                      </div>

                      <input 
                        type="range"
                        min="0"
                        max="600"
                        value={currentSeconds}
                        onChange={(e) => setCurrentSeconds(Number(e.target.value))}
                        className="w-full h-2 bg-[#eae4d9] rounded-lg appearance-none cursor-pointer accent-[#d93829]"
                      />
                    </div>

                    <div className="hidden sm:flex items-center gap-1 text-[11px] text-[#6e665d] px-2 py-1 rounded bg-[#faf7f2] border border-[#eae4d9]">
                      <Volume2 className="w-3.5 h-3.5 text-[#d93829]" />
                      <span className="font-mono">1.0x</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* SECTION: SUGGESTED INTERROGATION QUESTIONS */}
              <Card className="border border-amber-200/80 shadow-sm bg-linear-to-b from-amber-50/40 to-white overflow-hidden">
                <div className="px-5 py-3 border-b border-amber-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-600" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#191410]">
                      Suggested Questions (Derived from Analysis)
                    </h3>
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                      {suggestedQuestions.length}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsQuestionsPanelOpen(!isQuestionsPanelOpen)}
                      className="text-xs text-[#6e665d] hover:text-[#191410] flex items-center gap-1 cursor-pointer font-medium"
                    >
                      <span>{isQuestionsPanelOpen ? 'Collapse' : 'Expand'}</span>
                      {isQuestionsPanelOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {isQuestionsPanelOpen && (
                  <div className="p-4 space-y-3">
                    {/* Filter pills */}
                    <div className="flex flex-wrap items-center gap-1.5 pb-2 border-b border-[#eae4d9]">
                      <button
                        onClick={() => setQuestionCategoryFilter('all')}
                        className={cn(
                          "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-pointer",
                          questionCategoryFilter === 'all' 
                            ? "bg-[#191410] text-white" 
                            : "bg-white border border-[#eae4d9] text-[#6e665d] hover:bg-[#faf7f2]"
                        )}
                      >
                        All ({suggestedQuestions.length})
                      </button>
                      <button
                        onClick={() => setQuestionCategoryFilter('contradiction')}
                        className={cn(
                          "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-pointer flex items-center gap-1",
                          questionCategoryFilter === 'contradiction' 
                            ? "bg-[#d93829] text-white" 
                            : "bg-white border border-[#eae4d9] text-[#6e665d] hover:bg-red-50 hover:text-red-700"
                        )}
                      >
                        <span>⚡ Contradictions</span>
                      </button>
                      <button
                        onClick={() => setQuestionCategoryFilter('gap')}
                        className={cn(
                          "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-pointer flex items-center gap-1",
                          questionCategoryFilter === 'gap' 
                            ? "bg-amber-600 text-white" 
                            : "bg-white border border-[#eae4d9] text-[#6e665d] hover:bg-amber-50 hover:text-amber-700"
                        )}
                      >
                        <span>🔍 Case Gaps</span>
                      </button>
                      <button
                        onClick={() => setQuestionCategoryFilter('alibi')}
                        className={cn(
                          "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-pointer flex items-center gap-1",
                          questionCategoryFilter === 'alibi' 
                            ? "bg-purple-700 text-white" 
                            : "bg-white border border-[#eae4d9] text-[#6e665d] hover:bg-purple-50 hover:text-purple-700"
                        )}
                      >
                        <span>📍 Unverified Alibis</span>
                      </button>
                    </div>

                    {/* Question List */}
                    {questionsLoading ? (
                      <div className="py-6 text-center text-xs text-[#6e665d]">
                        <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-amber-600" />
                        Synthesizing questions from contradictions, gaps & alibis...
                      </div>
                    ) : filteredQuestions.length === 0 ? (
                      <div className="py-4 text-center text-xs text-[#6e665d]">
                        No suggested questions in this category.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-1">
                        {filteredQuestions.map((q) => (
                          <div 
                            key={q.id}
                            className={cn(
                              "p-3 rounded-xl border bg-white text-xs flex flex-col justify-between transition-all hover:shadow-xs",
                              q.severity === 'critical' ? "border-red-200" :
                              q.severity === 'major' ? "border-amber-200" : "border-[#eae4d9]"
                            )}
                          >
                            <div className="space-y-1.5">
                              <div className="flex items-center justify-between gap-1">
                                <span className={cn(
                                  "text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded",
                                  q.category === 'contradiction' ? "bg-red-50 text-red-700 border border-red-200" :
                                  q.category === 'alibi' ? "bg-purple-50 text-purple-700 border border-purple-200" :
                                  "bg-amber-50 text-amber-800 border border-amber-200"
                                )}>
                                  {q.category_label}
                                </span>
                                {q.is_subject_specific && (
                                  <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                    Direct Subject
                                  </span>
                                )}
                              </div>

                              <p className="font-serif font-medium text-[#191410] leading-snug">
                                "{q.question}"
                              </p>

                              <p className="text-[10px] text-[#6e665d] line-clamp-2">
                                <span className="font-semibold">Rationale:</span> {q.rationale}
                              </p>
                            </div>

                            <div className="mt-3 pt-2 border-t border-[#f0ebe1] flex items-center justify-between">
                              <span className="text-[9px] text-[#6e665d] truncate max-w-[150px]">
                                {q.title}
                              </span>
                              <button
                                onClick={() => handleApplyQuestion(q)}
                                className="px-2.5 py-1 bg-[#d93829]/10 hover:bg-[#d93829] text-[#d93829] hover:text-white rounded-lg text-[10px] font-bold transition-all flex items-center gap-1 cursor-pointer active:scale-95"
                              >
                                <span>Ask Question</span>
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>

              {/* REAL-TIME CONTRADICTION BANNER (WHEN FLAGGED) */}
              {latestFlaggedContradiction && (
                <div className="p-4 bg-red-50 border-2 border-red-400 rounded-2xl shadow-md text-xs text-[#191410] space-y-3 animate-in fade-in-50 slide-in-from-top-4">
                  <div className="flex items-center justify-between border-b border-red-200 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-red-600 animate-ping" />
                      <span className="font-serif font-bold text-red-900 text-sm">
                        🚨 New Contradiction Flagged Immediately ({latestFlaggedContradiction.conflict_type})
                      </span>
                    </div>
                    <button 
                      onClick={() => setLatestFlaggedContradiction(null)}
                      className="text-red-700 hover:text-red-900 cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <p className="text-red-950 text-xs leading-relaxed">
                    <span className="font-bold">Forensic Rationale:</span> {latestFlaggedContradiction.reasoning}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <div className="p-3 bg-white rounded-xl border border-red-200">
                      <span className="text-[10px] font-mono uppercase font-bold text-red-700 block mb-1">
                        Current Statement ({latestFlaggedContradiction.source_new})
                      </span>
                      <p className="italic text-[#191410] leading-relaxed">
                        "{latestFlaggedContradiction.quote_new}"
                      </p>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-red-200">
                      <span className="text-[10px] font-mono uppercase font-bold text-[#6e665d] block mb-1">
                        Conflicting Record ({latestFlaggedContradiction.source_prior})
                      </span>
                      <p className="italic text-[#191410] leading-relaxed">
                        "{latestFlaggedContradiction.quote_prior}"
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* LIVE RESPONSE RECORDING STUDIO */}
              <Card id="response-recording-studio" className="border border-[#eae4d9] shadow-sm bg-white overflow-hidden">
                <CardHeader className="py-3 px-5 bg-[#faf7f2]/50 border-b border-[#eae4d9]">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#191410]">
                        Interview Capture Studio
                      </span>
                      {isLiveStreaming && (
                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-300 text-[10px] font-bold uppercase animate-pulse">
                          <Radio className="w-3 h-3 text-rose-600 animate-spin" />
                          Live Stream Active
                        </span>
                      )}
                    </div>

                    {/* Mode Toggle */}
                    <div className="flex rounded-lg border border-[#eae4d9] bg-[#faf7f2] p-0.5 text-xs">
                      <button
                        type="button"
                        onClick={() => setStudioTab('stream')}
                        className={cn(
                          "px-3 py-1 rounded-md font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                          studioTab === 'stream' 
                            ? "bg-[#d93829] text-white shadow-xs" 
                            : "text-[#6e665d] hover:text-[#191410]"
                        )}
                      >
                        <Mic className="w-3.5 h-3.5" />
                        <span>Live Audio Stream</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setStudioTab('manual')}
                        className={cn(
                          "px-3 py-1 rounded-md font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                          studioTab === 'manual' 
                            ? "bg-[#d93829] text-white shadow-xs" 
                            : "text-[#6e665d] hover:text-[#191410]"
                        )}
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Manual Entry</span>
                      </button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-5">
                  {studioTab === 'stream' ? (
                    /* LIVE AUDIO STREAMING PANEL */
                    <div className="space-y-4">
                      {/* Control Strip */}
                      <div className="p-4 rounded-2xl bg-[#faf7f2] text-[#191410] border border-[#eae4d9] flex flex-wrap items-center justify-between gap-4 shadow-xs">
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={isLiveStreaming ? stopLiveStreaming : startLiveStreaming}
                            className={cn(
                              "w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-transform active:scale-95 cursor-pointer font-bold shrink-0",
                              isLiveStreaming 
                                ? "bg-rose-600 hover:bg-rose-700 text-white animate-pulse" 
                                : "bg-emerald-600 hover:bg-emerald-700 text-white"
                            )}
                            title={isLiveStreaming ? "Stop Live Stream" : "Start Live Audio Streaming"}
                          >
                            {isLiveStreaming ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
                          </button>

                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-[#191410]">
                                {isLiveStreaming ? "Live Audio Streaming Active" : "Start Live Audio Stream"}
                              </span>
                              <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#191410] text-amber-300 font-bold border border-[#191410]">
                                {formatSeconds(liveStreamSeconds)}
                              </span>
                            </div>
                            <p className="text-[11px] text-[#6e665d] mt-0.5">
                              {liveStatusText}
                            </p>
                          </div>
                        </div>

                        {/* Speaker Toggle & Audio Waveform Meter */}
                        <div className="flex items-center gap-3">
                          {isLiveStreaming && (
                            <div className="flex items-center gap-1 bg-[#faf7f2] px-2.5 py-1.5 rounded-xl border border-[#eae4d9]">
                              <span className="text-[10px] text-[#6e665d] font-mono">Mic:</span>
                              <div className="w-16 h-2 bg-[#eae4d9] rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-emerald-600 transition-all duration-75"
                                  style={{ width: `${micAudioLevel}%` }}
                                />
                              </div>
                            </div>
                          )}

                          <div className="flex rounded-xl bg-[#faf7f2] p-1 border border-[#eae4d9] text-xs">
                            <button
                              type="button"
                              onClick={() => setLiveSpeaker('interviewee')}
                              className={cn(
                                "px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer",
                                liveSpeaker === 'interviewee' 
                                  ? "bg-[#d93829] text-white shadow-xs" 
                                  : "text-[#6e665d] hover:text-[#191410]"
                              )}
                            >
                              Subject ({activeInterview.interviewee_name.split(' ')[0]})
                            </button>
                            <button
                              type="button"
                              onClick={() => setLiveSpeaker('investigator')}
                              className={cn(
                                "px-2.5 py-1 rounded-lg text-xs font-bold transition-all",
                                liveSpeaker === 'investigator' 
                                  ? "bg-blue-700 text-white shadow-xs" 
                                  : "text-stone-400 hover:text-white"
                              )}
                            >
                              Investigator
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Active Interrogation Question Context if selected */}
                      {activeQuestion && (
                        <div className="p-3 bg-amber-50/90 border border-amber-200 rounded-xl text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">
                              Active Context Question ({questionSourceType})
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                setActiveQuestion('');
                                setQuestionSourceType('manual');
                              }}
                              className="text-amber-700 hover:text-amber-900 cursor-pointer"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          <p className="font-serif italic text-[#191410]">
                            "{activeQuestion}"
                          </p>
                        </div>
                      )}

                      {/* Live Interim Speech Preview Bubble */}
                      {isLiveStreaming && (
                        <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 text-xs space-y-1 animate-pulse">
                          <div className="flex items-center gap-1.5 text-blue-800 font-bold text-[11px] uppercase tracking-wider">
                            <Activity className="w-3.5 h-3.5" />
                            <span>Live Transcription Rolling:</span>
                          </div>
                          <p className="text-blue-950 font-medium italic text-sm">
                            {liveInterimText || "Listening for speech... Spoken statements will appear and be checked instantly for contradictions."}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* MANUAL TEXT ENTRY FORM */
                    <form onSubmit={handleRecordStatement} className="space-y-4">
                      {/* Prompt question preview if set */}
                      {activeQuestion && (
                        <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-xl text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">
                              Active Interrogation Prompt ({questionSourceType})
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                setActiveQuestion('');
                                setQuestionSourceType('manual');
                              }}
                              className="text-amber-700 hover:text-amber-900 cursor-pointer"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          <p className="font-serif italic text-[#191410]">
                            "{activeQuestion}"
                          </p>
                        </div>
                      )}

                      {!activeQuestion && (
                        <div>
                          <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1">
                            Investigator Question (Optional or pick from above)
                          </label>
                          <input
                            type="text"
                            placeholder="Type investigator question or select a suggested question above..."
                            value={activeQuestion}
                            onChange={(e) => setActiveQuestion(e.target.value)}
                            className="w-full px-3 py-2 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                          />
                        </div>
                      )}

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d]">
                            {activeInterview.interviewee_name}'s Response / Deposition Statement
                          </label>
                          <span className="text-[10px] font-mono text-[#6e665d]">
                            Audio marker: {formatSeconds(currentSeconds)}
                          </span>
                        </div>
                        
                        <textarea
                          rows={3}
                          required
                          placeholder="Type or dictate the interviewee's spoken statement for instant claim verification..."
                          value={answerText}
                          onChange={(e) => setAnswerText(e.target.value)}
                          className="w-full p-3 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829] leading-relaxed"
                        />
                      </div>

                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-[#6e665d]">Speaker Role:</span>
                          <select
                            value={speakerRole}
                            onChange={(e: any) => setSpeakerRole(e.target.value)}
                            className="px-2.5 py-1 text-xs border border-[#eae4d9] rounded-lg bg-white text-[#191410]"
                          >
                            <option value="interviewee">Interviewee ({activeInterview.interviewee_role})</option>
                            <option value="investigator">Investigator</option>
                            <option value="counsel">Legal Counsel</option>
                          </select>
                        </div>

                        <button
                          type="submit"
                          disabled={analyzingStatement || !answerText.trim()}
                          className={cn(
                            "px-5 py-2 rounded-full text-xs font-semibold text-white shadow-sm transition-all flex items-center gap-2 cursor-pointer active:scale-95",
                            analyzingStatement || !answerText.trim()
                              ? "bg-stone-400 cursor-not-allowed"
                              : "bg-[#d93829] hover:bg-[#bf2b1d]"
                          )}
                        >
                          {analyzingStatement ? (
                            <>
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              <span>Running NLI Claim Comparison...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>Record & Analyze Statement</span>
                            </>
                          )}
                        </button>
                      </div>
                    </form>
                  )}
                </CardContent>
              </Card>

              {/* SYNCHRONIZED TRANSCRIPT */}
              <Card className="border border-[#eae4d9] shadow-sm bg-white overflow-hidden">
                <div className="px-5 py-3 bg-[#faf7f2]/50 border-b border-[#eae4d9] flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#6e665d]" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#191410]">
                      Judicial Transcript ({filteredStatements.length} statements)
                    </h3>
                  </div>

                  <div className="relative w-48 sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#6e665d]" />
                    <input 
                      type="text" 
                      placeholder="Search testimony..." 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-1 bg-white border border-[#eae4d9] rounded-lg text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                    />
                  </div>
                </div>

                <div className="p-6 space-y-4 max-h-[460px] overflow-y-auto bg-white">
                  {filteredStatements.length === 0 ? (
                    <div className="py-8 text-center text-xs text-[#6e665d]">
                      No statements match your search criteria.
                    </div>
                  ) : (
                    filteredStatements.map((stmt) => {
                      const isCurrent = currentSeconds >= stmt.seconds && 
                        (stmt.sequence_order === activeInterview.statements?.length || currentSeconds < (activeInterview.statements?.[stmt.sequence_order]?.seconds || 9999));
                      const isFlagged = stmt.is_contradiction_flag;
                      const linkedContra = activeInterview.contradictions?.find(c => c.statement_id === stmt.id);

                      return (
                        <div 
                          key={stmt.id}
                          className={cn(
                            "p-4 rounded-xl border transition-all text-xs space-y-2",
                            isCurrent 
                              ? "bg-[#d93829]/5 border-[#d93829]/30 shadow-xs" 
                              : "bg-[#faf7f2]/30 border-[#eae4d9] hover:bg-[#faf7f2]/70",
                            isFlagged && "border-l-4 border-l-[#d93829] bg-red-50/20"
                          )}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-[10px] bg-white px-2 py-0.5 rounded border border-[#eae4d9] text-[#6e665d]">
                                {stmt.timestamp_marker}
                              </span>
                              <span className={cn(
                                "font-bold uppercase tracking-wider text-[11px]",
                                stmt.role === 'investigator' ? "text-[#191410]" : "text-[#d93829]"
                              )}>
                                {stmt.speaker}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5">
                              {stmt.tag && (
                                <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                                  {stmt.tag}
                                </span>
                              )}

                              {isFlagged && (
                                <button
                                  onClick={() => linkedContra && setInspectingContradiction(linkedContra)}
                                  className="text-[9px] font-bold uppercase px-2 py-0.5 rounded bg-red-600 text-white hover:bg-red-700 transition-colors cursor-pointer flex items-center gap-1"
                                >
                                  <AlertTriangle className="w-2.5 h-2.5" />
                                  <span>Contradiction Flagged</span>
                                </button>
                              )}
                            </div>
                          </div>

                          {stmt.question && (
                            <div className="pl-2 border-l-2 border-[#eae4d9] text-[11px] text-[#6e665d] italic">
                              <span className="font-semibold text-[#191410]">Q:</span> {stmt.question}
                            </div>
                          )}

                          <p className="text-xs text-[#191410] leading-relaxed pl-1 font-sans">
                            {stmt.text}
                          </p>

                          {/* Inline preview of linked contradiction if flagged */}
                          {isFlagged && linkedContra && (
                            <div className="mt-2 p-2.5 bg-red-50 border border-red-200 rounded-lg text-[11px] text-red-950 space-y-1">
                              <div className="flex items-center justify-between font-bold text-[10px] text-red-800">
                                <span>CONFLICT: {linkedContra.conflict_type}</span>
                                <span className="font-mono">{Math.round(linkedContra.confidence)}% confidence</span>
                              </div>
                              <p className="text-[10px] text-[#6e665d] line-clamp-2">
                                <span className="font-semibold text-red-900">Conflicts with:</span> "{linkedContra.quote_prior}" ({linkedContra.source_prior})
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* CONTRADICTION INSPECTION MODAL (DUAL QUOTE LINK) */}
      {inspectingContradiction && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in-50">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 border border-[#eae4d9] shadow-2xl text-[#191410] space-y-4">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-600" />
                <h3 className="text-base font-serif font-bold text-red-900">
                  Contradiction Dual-Quote Inspection
                </h3>
              </div>
              <button 
                onClick={() => setInspectingContradiction(null)}
                className="text-[#6e665d] hover:text-[#191410] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block mb-0.5">
                  Conflict Classification
                </span>
                <span className="text-sm font-bold text-[#191410]">
                  {inspectingContradiction.conflict_type}
                </span>
                <p className="text-[11px] text-[#6e665d] mt-1">
                  {inspectingContradiction.reasoning}
                </p>
              </div>

              {/* Side-by-side or stacked quotes */}
              <div className="space-y-3">
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold uppercase text-red-800">
                      New Statement Quote
                    </span>
                    <span className="text-[10px] text-red-700 font-mono">
                      {inspectingContradiction.source_new}
                    </span>
                  </div>
                  <p className="italic font-serif text-sm text-[#191410] leading-relaxed">
                    "{inspectingContradiction.quote_new}"
                  </p>
                </div>

                <div className="p-3 bg-[#faf7f2] border border-[#eae4d9] rounded-xl space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold uppercase text-[#6e665d]">
                      Conflicting Prior Quote
                    </span>
                    <span className="text-[10px] text-[#6e665d] font-mono">
                      {inspectingContradiction.source_prior}
                    </span>
                  </div>
                  <p className="italic font-serif text-sm text-[#191410] leading-relaxed">
                    "{inspectingContradiction.quote_prior}"
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-[#eae4d9]">
              <button
                onClick={() => setInspectingContradiction(null)}
                className="px-4 py-2 bg-[#191410] text-white rounded-full text-xs font-semibold hover:bg-stone-800 transition-colors cursor-pointer"
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ADD NEW INTERVIEW RECORD */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 border border-[#eae4d9] shadow-xl text-[#191410] animate-in fade-in-50 zoom-in-95">
            <h3 className="text-base font-serif font-bold text-[#191410] mb-1">
              New Judicial Deposition Session
            </h3>
            <p className="text-xs text-[#6e665d] mb-4">
              Create an interrogation or witness deposition session under BNSS 2023 with automated cross-statement contradiction detection.
            </p>
            
            <form onSubmit={handleCreateInterview} className="space-y-3.5">
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1">
                  Subject Name
                </label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={newInterviewee}
                  onChange={(e) => setNewInterviewee(e.target.value)}
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1">
                  Subject Role / Designation
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829] bg-white"
                >
                  <option value="suspect">Suspect / Prime Accused</option>
                  <option value="witness">Eyewitness / Witness</option>
                  <option value="approver">Approver (Sec 164 CrPC / 183 BNSS)</option>
                  <option value="victim">Victim / Complainant</option>
                  <option value="expert">Forensic Expert / Panch Witness</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1">
                  Interviewer / Officer Name
                </label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. PI Kishor Mhaswade"
                  value={newInterviewer}
                  onChange={(e) => setNewInterviewer(e.target.value)}
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-[#eae4d9]">
                <button 
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="px-4 py-2 bg-[#d93829] text-white rounded-full text-xs font-semibold hover:bg-[#bf2b1d] transition-colors cursor-pointer active:scale-95"
                >
                  Initialize Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
