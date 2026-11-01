import React, { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Bot, X, Send, Loader2, Sparkles, User, FileText, ChevronRight, CornerDownLeft } from 'lucide-react';
import { apiRequest } from '../../services/apiClient';
import { cn } from '../../utils';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  sources?: string[];
  timestamp: Date;
}

const SUGGESTED_QUESTIONS = [
  "Summarize key suspects and case strength.",
  "What are the major timeline contradictions?",
  "What critical evidence is still missing before filing?",
  "Will this case hold up against reasonable doubt?"
];

export function FloatingAiAssistant() {
  const { caseId } = useParams<{ caseId: string }>();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `Hello, Investigator! I'm your AI Forensic Co-Pilot for this case. Ask me about exhibits, alibis, suspect theories, or gaps needed to secure trial conviction.`,
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [messages, isOpen]);

  const sendMessage = async (textToSend?: string) => {
    const prompt = (textToSend || input).trim();
    if (!prompt || loading || !caseId) return;

    const userMessage: Message = {
      id: String(Date.now()),
      sender: 'user',
      text: prompt,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await apiRequest<{ response: string; sources?: string[] }>(
        `/cases/${caseId}/assistant`,
        {
          method: 'POST',
          body: JSON.stringify({ question: prompt })
        }
      );

      const assistantMessage: Message = {
        id: String(Date.now() + 1),
        sender: 'assistant',
        text: response.response || 'No response generated.',
        sources: response.sources,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: String(Date.now() + 1),
        sender: 'assistant',
        text: "I couldn't reach the AI analysis engine right now. Please verify your connection or try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 bg-[#d93829] hover:bg-[#bf2b1d] text-white px-4 py-3 rounded-full shadow-xl flex items-center gap-2.5 transition-all hover:scale-105 cursor-pointer group border border-white/20"
          title="Open AI Case Co-Pilot"
        >
          <div className="relative">
            <Bot className="w-5 h-5 group-hover:rotate-6 transition-transform" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full ring-2 ring-[#d93829] animate-pulse" />
          </div>
          <span className="font-serif font-bold text-xs tracking-wide">
            AI Assistant
          </span>
        </button>
      )}

      {/* Slide-Over Panel */}
      {isOpen && (
        <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[440px] bg-white border-l border-[#eae4d9] shadow-2xl flex flex-col animate-in slide-in-from-right duration-200 text-[#191410]">
          {/* Header */}
          <div className="p-4 bg-[#faf7f2] border-b border-[#eae4d9] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center text-[#d93829]">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-serif font-bold text-[#191410]">
                  AI Investigation Co-Pilot
                </h3>
                <p className="text-[10px] font-mono text-[#6e665d]">
                  Case #{caseId} Intelligence
                </p>
              </div>
            </div>

            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-xl hover:bg-[#eae4d9] text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={cn(
                  "flex gap-2.5 max-w-[90%]",
                  msg.sender === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
                )}
              >
                <div className={cn(
                  "w-7 h-7 rounded-xl flex items-center justify-center shrink-0 mt-0.5",
                  msg.sender === 'user' ? "bg-[#191410] text-white" : "bg-red-50 text-[#d93829] border border-red-200"
                )}>
                  {msg.sender === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div className={cn(
                  "p-3 rounded-2xl leading-relaxed font-sans shadow-2xs",
                  msg.sender === 'user' 
                    ? "bg-[#191410] text-white rounded-tr-none" 
                    : "bg-[#faf7f2] border border-[#eae4d9] text-[#191410] rounded-tl-none"
                )}>
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-[#eae4d9] text-[10px] font-mono text-[#6e665d] space-y-0.5">
                      <div className="font-bold uppercase tracking-wider">Sources:</div>
                      {msg.sources.map((src, i) => (
                        <div key={i} className="flex items-center gap-1 text-blue-700 truncate">
                          <FileText className="w-3 h-3 shrink-0" />
                          <span className="truncate">{src}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-xs font-mono text-[#8c8276] p-2 bg-[#faf7f2] rounded-xl border border-[#eae4d9] w-fit">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#d93829]" />
                <span>Consulting exhibits and evidence matrix...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="px-4 py-2 border-t border-[#f0ebe1] bg-[#faf7f2]/60 overflow-x-auto flex gap-1.5 scrollbar-none">
            {SUGGESTED_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => sendMessage(q)}
                disabled={loading}
                className="px-2.5 py-1 rounded-full text-[10px] font-mono bg-white hover:bg-stone-100 text-stone-700 border border-[#eae4d9] transition-all whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-3 bg-white border-t border-[#eae4d9]">
            <form 
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask case co-pilot..."
                disabled={loading}
                className="flex-1 px-3.5 py-2 rounded-full border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono placeholder:text-[#8c8276] focus:bg-white focus:outline-hidden focus:border-[#d93829]"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="p-2 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white disabled:opacity-50 transition-all cursor-pointer shrink-0 shadow-xs"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

