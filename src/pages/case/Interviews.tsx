import { useParams } from 'react-router-dom';
import { useState, useEffect, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Mic, PlayCircle, PauseCircle, FileText, Clock, Search, 
  Upload, Tag, AlertTriangle, CheckCircle2, User, Volume2, 
  Share2, Download, Plus, Filter, ShieldCheck
} from 'lucide-react';
import { cn } from '../../utils';
import { matchesCase } from '../../engine/CaseStateEngine';

interface InterviewRecord {
  id: string;
  interviewee: string;
  role: string;
  interviewer: string;
  date: string;
  duration: string;
  status: 'Transcribed' | 'Analyzing' | 'Pending';
  audioProgressPercent: number;
  transcript: Array<{
    timestamp: string;
    seconds: number;
    speaker: string;
    role: 'investigator' | 'interviewee' | 'counsel';
    text: string;
    isContradictionFlag?: boolean;
    tag?: string;
  }>;
}

const CASE_INTERVIEWS_MAP: Record<string, InterviewRecord[]> = {
  // Case 1: Nayana Pujari
  '1': [
    {
      id: 'REC-2009-001',
      interviewee: 'Yogesh Raut',
      role: 'Prime Accused / Driver',
      interviewer: 'PI Kishor Mhaswade',
      date: 'Oct 17, 2009',
      duration: '42:15 mins',
      status: 'Transcribed',
      audioProgressPercent: 35,
      transcript: [
        {
          timestamp: '00:05',
          seconds: 5,
          speaker: 'PI Kishor Mhaswade',
          role: 'investigator',
          text: 'State your full name and confirm your role with the white Toyota Qualis cab on the night of October 7th, 2009.'
        },
        {
          timestamp: '00:22',
          seconds: 22,
          speaker: 'Yogesh Raut',
          role: 'interviewee',
          text: 'My name is Yogesh Ashok Raut. I was driving the Qualis cab MH-12-AQ-4411 on company pickup duty near Kharadi bypass that evening.'
        },
        {
          timestamp: '01:15',
          seconds: 75,
          speaker: 'PI Kishor Mhaswade',
          role: 'investigator',
          text: 'CCTV timestamps from Yerwada SBI ATM show a withdrawal at 21:42 using victim Nayana Pujari\'s card. Who was holding the card?'
        },
        {
          timestamp: '01:40',
          seconds: 100,
          speaker: 'Yogesh Raut',
          role: 'interviewee',
          text: 'Rajesh Chaudhari and I walked up to the counter. The PIN number was obtained inside the vehicle before we reached Yerwada.',
          isContradictionFlag: true,
          tag: 'Key Admission'
        },
        {
          timestamp: '02:30',
          seconds: 150,
          speaker: 'PI Kishor Mhaswade',
          role: 'investigator',
          text: 'Where was the victim transported following the cash withdrawal?'
        },
        {
          timestamp: '02:55',
          seconds: 175,
          speaker: 'Yogesh Raut',
          role: 'interviewee',
          text: 'We took the Nashik highway towards Rajgurunagar and Zarewadi forest area. The vehicle did not stop at toll gates.'
        }
      ]
    },
    {
      id: 'REC-2009-002',
      interviewee: 'Rajesh Chaudhari',
      role: 'Approver (Sec 164 CrPC)',
      interviewer: 'Judicial Magistrate First Class',
      date: 'Nov 02, 2009',
      duration: '38:40 mins',
      status: 'Transcribed',
      audioProgressPercent: 60,
      transcript: [
        {
          timestamp: '00:10',
          seconds: 10,
          speaker: 'Magistrate Court',
          role: 'investigator',
          text: 'Are you giving this confession voluntarily without any threat or promise of pardon from the police?'
        },
        {
          timestamp: '00:30',
          seconds: 30,
          speaker: 'Rajesh Chaudhari',
          role: 'interviewee',
          text: 'Yes, Sir. I want to place the complete truth on judicial record. I was in the front passenger seat when Yogesh stopped for the passenger at Kharadi.'
        },
        {
          timestamp: '01:20',
          seconds: 80,
          speaker: 'Rajesh Chaudhari',
          role: 'interviewee',
          text: 'Vishwas Kadam and Mahesh Thakur were in the rear rows. The vehicle was diverted towards Hadapsar and Yerwada before heading to Khed.',
          isContradictionFlag: true,
          tag: 'Corroborates Route Log'
        }
      ]
    },
    {
      id: 'REC-2009-003',
      interviewee: 'Vishwas Kadam',
      role: 'Accused Accomplice',
      interviewer: 'SIT Inspector',
      date: 'Oct 20, 2009',
      duration: '26:10 mins',
      status: 'Transcribed',
      audioProgressPercent: 10,
      transcript: [
        {
          timestamp: '00:15',
          seconds: 15,
          speaker: 'SIT Officer',
          role: 'investigator',
          text: 'When did you board the vehicle MH-12-AQ-4411 on the date of occurrence?'
        },
        {
          timestamp: '00:40',
          seconds: 40,
          speaker: 'Vishwas Kadam',
          role: 'interviewee',
          text: 'I boarded at Magarpatta junction around 7:45 PM. Yogesh said we would do private drop trips after official shift.'
        }
      ]
    }
  ],

  // Case 2: Pune Cyber Heist
  '2': [
    {
      id: 'REC-2024-001',
      interviewee: 'Devendra Joshi',
      role: 'Lead Systems Administrator',
      interviewer: 'PI Vikram Salunkhe (Cyber Cell)',
      date: 'Feb 15, 2024',
      duration: '34:20 mins',
      status: 'Transcribed',
      audioProgressPercent: 45,
      transcript: [
        {
          timestamp: '00:12',
          seconds: 12,
          speaker: 'PI Vikram Salunkhe',
          role: 'investigator',
          text: 'When did you first notice anomalous traffic spikes across the database cluster?'
        },
        {
          timestamp: '00:35',
          seconds: 35,
          speaker: 'Devendra Joshi',
          role: 'interviewee',
          text: 'At 02:40 AM on February 14th. The SIEM dashboard triggered multiple critical alerts showing 42GB outbound SSH pipe to Frankfurt exit node 185.220.101.5.'
        },
        {
          timestamp: '01:10',
          seconds: 70,
          speaker: 'PI Vikram Salunkhe',
          role: 'investigator',
          text: 'Were administrator credentials used to bypass MFA authentication?'
        },
        {
          timestamp: '01:30',
          seconds: 90,
          speaker: 'Devendra Joshi',
          role: 'interviewee',
          text: 'Yes, a service account belonging to an offsite contractor was reactivated without ticket approval. The password hash was dumped directly from memory.',
          isContradictionFlag: true,
          tag: 'Credential Exploit'
        }
      ]
    }
  ],

  // Case 3: Indiranagar Homicide
  '3': [
    {
      id: 'REC-2023-001',
      interviewee: 'M. Venkatesh',
      role: 'Security Gate Guard',
      interviewer: 'Insp. B. Manjunath',
      date: 'Nov 16, 2023',
      duration: '22:15 mins',
      status: 'Transcribed',
      audioProgressPercent: 20,
      transcript: [
        {
          timestamp: '00:10',
          seconds: 10,
          speaker: 'Insp. B. Manjunath',
          role: 'investigator',
          text: 'Describe the vehicle that exited through the rear 100ft road gate at 02:47 AM.'
        },
        {
          timestamp: '00:30',
          seconds: 30,
          speaker: 'M. Venkatesh',
          role: 'interviewee',
          text: 'It was a silver Hyundai sedan. The driver flashed high beams and did not stop at the barrier. The front number plate was masked with mud.'
        }
      ]
    }
  ]
};

export function Interviews() {
  const { caseId } = useParams<{ caseId: string }>();
  const [selectedInterviewId, setSelectedInterviewId] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentSeconds, setCurrentSeconds] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [taggedContradictions, setTaggedContradictions] = useState<Set<number>>(new Set());
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [newInterviewee, setNewInterviewee] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('');

  // Find interviews for active case
  const availableInterviews = useMemo(() => {
    if (!caseId) return [];
    for (const [key, list] of Object.entries(CASE_INTERVIEWS_MAP)) {
      if (matchesCase(key, caseId) || key === String(caseId)) {
        return list;
      }
    }
    return CASE_INTERVIEWS_MAP['1'];
  }, [caseId]);

  const activeInterview = useMemo(() => {
    return availableInterviews.find(i => i.id === selectedInterviewId) || availableInterviews[0];
  }, [availableInterviews, selectedInterviewId]);

  useEffect(() => {
    if (availableInterviews.length > 0 && !selectedInterviewId) {
      setSelectedInterviewId(availableInterviews[0].id);
    }
  }, [availableInterviews, selectedInterviewId]);

  // Audio simulation timer
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentSeconds(prev => (prev >= 200 ? 0 : prev + 1));
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  const filteredTranscript = useMemo(() => {
    if (!activeInterview) return [];
    if (!searchQuery.trim()) return activeInterview.transcript;
    return activeInterview.transcript.filter(t => 
      t.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.speaker.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [activeInterview, searchQuery]);

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleTagContradiction = (idx: number) => {
    setTaggedContradictions(prev => {
      const updated = new Set(prev);
      if (updated.has(idx)) updated.delete(idx);
      else updated.add(idx);
      return updated;
    });
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-20 text-[#191410]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[#eae4d9] pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#d93829]" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#d93829]">Audio Forensics & Deposition Analysis</span>
          </div>
          <h1 className="text-2xl font-serif font-bold text-[#191410]">Interviews & Judicial Statements</h1>
          <p className="text-xs text-[#6e665d] mt-1">Review transcribed interrogations, Sec 164 CrPC statements, and cross-reference testimonies against case evidence.</p>
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-[#d93829] text-white rounded-full hover:bg-[#bf2b1d] transition-all font-semibold text-xs shadow-sm flex items-center gap-2 cursor-pointer"
          >
            <Mic className="w-4 h-4" />
            <span>+ Upload Recording</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Recording Catalog */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between mb-2 px-1">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#6e665d]">Case Recordings ({availableInterviews.length})</h2>
            <span className="text-[10px] text-[#6e665d] bg-white px-2 py-0.5 rounded-md border border-[#eae4d9]">Sec 65B Certified</span>
          </div>
          
          <div className="space-y-2.5">
            {availableInterviews.map((rec) => {
              const isSelected = activeInterview?.id === rec.id;
              return (
                <div
                  key={rec.id}
                  onClick={() => {
                    setSelectedInterviewId(rec.id);
                    setCurrentSeconds(0);
                    setIsPlaying(false);
                  }}
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
                        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                        isSelected ? "bg-[#d93829]/10 text-[#d93829]" : "bg-[#f5f0e6] text-[#6e665d]"
                      )}>
                        <Mic className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="text-xs font-serif font-bold text-[#191410] leading-snug">{rec.interviewee}</h3>
                        <p className="text-[11px] text-[#6e665d]">{rec.role}</p>
                      </div>
                    </div>
                    <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#15803d]/10 text-[#15803d] border border-[#15803d]/20">
                      {rec.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-2.5 border-t border-[#f0ebe1] text-[10px] text-[#6e665d]">
                    <span className="font-mono">{rec.id} • {rec.date}</span>
                    <span className="font-semibold text-[#191410] bg-[#faf7f2] px-2 py-0.5 rounded border border-[#eae4d9]">{rec.duration}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Audio Player & Synced Transcript */}
        <div className="lg:col-span-8 space-y-4">
          {activeInterview && (
            <Card className="border border-[#eae4d9] shadow-sm bg-white overflow-hidden">
              {/* Header */}
              <div className="px-6 py-4 bg-[#faf7f2]/60 border-b border-[#eae4d9] flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-[10px] font-mono text-[#6e665d] uppercase tracking-wider">{activeInterview.id} • Recorded by {activeInterview.interviewer}</div>
                  <h2 className="text-base font-serif font-bold text-[#191410]">{activeInterview.interviewee} ({activeInterview.role})</h2>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => window.print()}
                    className="px-3 py-1.5 rounded-lg border border-[#eae4d9] bg-white text-xs font-semibold text-[#191410] hover:bg-[#f5f0e6] transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
                  >
                    <FileText className="w-3.5 h-3.5 text-[#6e665d]" />
                    <span>Print Transcript</span>
                  </button>
                </div>
              </div>

              {/* Functional Audio Scrubber */}
              <div className="p-5 bg-white border-b border-[#eae4d9] flex flex-col gap-3">
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="w-12 h-12 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white flex items-center justify-center shadow-md transition-transform active:scale-95 cursor-pointer shrink-0"
                    title={isPlaying ? "Pause" : "Play"}
                  >
                    {isPlaying ? <PauseCircle className="w-7 h-7" /> : <PlayCircle className="w-7 h-7" />}
                  </button>

                  <div className="flex-1 space-y-1.5">
                    <div className="flex justify-between text-xs font-mono text-[#6e665d]">
                      <span className="font-bold text-[#d93829]">{formatSeconds(currentSeconds)}</span>
                      <span>{activeInterview.duration}</span>
                    </div>

                    <input 
                      type="range"
                      min="0"
                      max="200"
                      value={currentSeconds}
                      onChange={(e) => setCurrentSeconds(Number(e.target.value))}
                      className="w-full h-2 bg-[#eae4d9] rounded-lg appearance-none cursor-pointer accent-[#d93829]"
                    />
                  </div>

                  <div className="hidden sm:flex items-center gap-1 text-xs text-[#6e665d] px-2.5 py-1 rounded bg-[#faf7f2] border border-[#eae4d9]">
                    <Volume2 className="w-3.5 h-3.5 text-[#d93829]" />
                    <span className="font-mono">1.0x</span>
                  </div>
                </div>
              </div>

              {/* Transcript Search Toolbar */}
              <div className="p-3 bg-[#faf7f2]/40 border-b border-[#eae4d9] flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#6e665d]" />
                  <input 
                    type="text" 
                    placeholder="Search inside testimony..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 bg-white border border-[#eae4d9] rounded-lg text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                  />
                </div>
                <span className="text-[10px] text-[#6e665d] whitespace-nowrap font-mono">{filteredTranscript.length} lines</span>
              </div>

              {/* Synchronized Transcript Body */}
              <div className="p-6 space-y-4 max-h-[460px] overflow-y-auto bg-white">
                {filteredTranscript.map((line, idx) => {
                  const isCurrent = currentSeconds >= line.seconds && (idx === filteredTranscript.length - 1 || currentSeconds < filteredTranscript[idx + 1].seconds);
                  const isTagged = taggedContradictions.has(idx) || line.isContradictionFlag;

                  return (
                    <div 
                      key={idx}
                      className={cn(
                        "p-4 rounded-xl border transition-all text-xs",
                        isCurrent 
                          ? "bg-[#d93829]/5 border-[#d93829]/30 shadow-xs" 
                          : "bg-[#faf7f2]/30 border-[#eae4d9] hover:bg-[#faf7f2]/70",
                        isTagged && "border-l-4 border-l-[#d93829]"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-[10px] bg-white px-2 py-0.5 rounded border border-[#eae4d9] text-[#6e665d]">
                            {line.timestamp}
                          </span>
                          <span className={cn(
                            "font-bold uppercase tracking-wider text-[11px]",
                            line.role === 'investigator' ? "text-[#191410]" : "text-[#d93829]"
                          )}>
                            {line.speaker}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {line.tag && (
                            <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                              {line.tag}
                            </span>
                          )}
                          <button
                            onClick={() => handleTagContradiction(idx)}
                            className={cn(
                              "text-[10px] font-bold px-2 py-0.5 rounded transition-colors cursor-pointer",
                              isTagged 
                                ? "bg-[#d93829] text-white" 
                                : "bg-white border border-[#eae4d9] text-[#6e665d] hover:text-[#d93829]"
                            )}
                          >
                            {isTagged ? "Flagged Contradiction" : "+ Flag Statement"}
                          </button>
                        </div>
                      </div>

                      <p className="text-xs text-[#191410] leading-relaxed pl-1 font-sans">
                        {line.text}
                      </p>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Modal: Upload Recording */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 border border-[#eae4d9] shadow-xl text-[#191410] animate-in fade-in-50 zoom-in-95">
            <h3 className="text-base font-serif font-bold text-[#191410] mb-1">Add Judicial Recording / Transcript</h3>
            <p className="text-xs text-[#6e665d] mb-4">Attach digital audio (WAV, MP3, MP4) or judicial statement document for automated NLP transcription.</p>
            
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1">Subject Name</label>
                <input 
                  type="text" 
                  placeholder="e.g. Ramesh Kumar (Suspect)"
                  value={newInterviewee}
                  onChange={(e) => setNewInterviewee(e.target.value)}
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1">Role / Designation</label>
                <input 
                  type="text" 
                  placeholder="e.g. Witness / Eye-witness"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div className="border-2 border-dashed border-[#eae4d9] rounded-xl p-6 text-center bg-[#faf7f2]/50 hover:bg-[#faf7f2] transition-colors cursor-pointer">
                <Upload className="w-6 h-6 text-[#d93829] mx-auto mb-1.5" />
                <p className="text-xs font-semibold text-[#191410]">Select Audio or Video Recording</p>
                <p className="text-[10px] text-[#6e665d]">Supports WAV, MP3, M4A, MP4 up to 250MB</p>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-[#eae4d9]">
              <button 
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 text-xs font-semibold text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button 
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 bg-[#d93829] text-white rounded-full text-xs font-semibold hover:bg-[#bf2b1d] transition-colors cursor-pointer"
              >
                Begin Transcription
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
