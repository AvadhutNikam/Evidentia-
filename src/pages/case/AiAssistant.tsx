// src/pages/case/AiAssistant.tsx
import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Bot, User, Loader2, FileText } from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  sources?: string[];
  timestamp: Date;
}

const SUGGESTED_QUESTIONS = [
  "Summarize this case.",
  "What are the major contradictions?",
  "What evidence supports each hypothesis?",
  "What information is missing?",
  "What should investigators examine next?",
  "Who are the key persons in this case?",
  "What is the timeline of events?",
  "Is there any conflicting evidence?"
];

export function AiAssistant() {
  const { caseId } = useParams<{ caseId: string }>();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `Hello! I'm your AI Investigation Assistant for this case. Ask me anything about the evidence, timeline, or persons involved. I'll provide answers based on the case data.`,
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
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`http://localhost:8000/cases/${caseId}/assistant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input })
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: data.answer,
        sources: data.sources || [],
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Assistant error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: 'Sorry, I encountered an error. Please make sure the backend is running and try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full pb-16">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center gap-3 bg-surface rounded-t-xl">
        <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Bot className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h2 className="font-semibold text-text">AI Investigation Assistant</h2>
          <p className="text-xs text-text-muted">Ask questions about the case</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface/50 border-x border-border min-h-[400px]">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[80%] ${message.sender === 'user' ? 'order-2' : 'order-1'}`}>
              <div className="flex items-start gap-2">
                {message.sender === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot className="w-3 h-3 text-primary" />
                  </div>
                )}
                <div
                  className={`rounded-lg px-4 py-3 ${
                    message.sender === 'user'
                      ? 'bg-primary text-white'
                      : 'bg-surface border border-border text-text'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-text-muted">
                      <FileText className="w-3 h-3 text-primary" />
                      <span>Sources: {message.sources.join(', ')}</span>
                    </div>
                  )}
                </div>
                {message.sender === 'user' && (
                  <div className="w-6 h-6 rounded-full bg-surface-hover border border-border flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="w-3 h-3 text-text-muted" />
                  </div>
                )}
              </div>
              <div className={`text-xs text-text-muted mt-1 ${message.sender === 'user' ? 'text-right' : ''}`}>
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="max-w-[80%]">
              <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-4 py-3">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span className="text-sm text-text-muted">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      <div className="px-4 py-2 border-t border-border bg-surface border-x">
        <p className="text-xs text-text-muted mb-2">Suggested questions:</p>
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q, index) => (
            <button
              key={index}
              onClick={() => {
                setInput(q);
                setTimeout(sendMessage, 100);
              }}
              className="text-xs px-3 py-1 bg-surface-hover hover:bg-border border border-border rounded-full text-text transition-colors cursor-pointer"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="p-4 border border-border rounded-b-xl flex gap-3 bg-surface">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Ask about the case..."
          className="flex-1 px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm text-text"
          disabled={loading}
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white rounded-lg transition-colors cursor-pointer"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}