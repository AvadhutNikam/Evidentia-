import React, { useState, useEffect, useRef } from 'react';
import { Languages } from 'lucide-react';
import { API_BASE_URL } from '../../config/api';

interface IndicInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  value: string;
  onValueChange: (val: string) => void;
  targetScript?: 'devanagari' | 'latin';
  label?: string;
  helperText?: string;
}

// Built-in offline common phoneme mapping for instant latency-free suggestions
const OFFLINE_SUGGESTIONS: Record<string, string[]> = {
  'rahul': ['राहुल'],
  'yogesh': ['योगेश'],
  'mahesh': ['महेश'],
  'rajesh': ['राजेश'],
  'suresh': ['सुरेश'],
  'ramesh': ['रमेश'],
  'dinesh': ['दिनेश'],
  'patil': ['पाटील', 'पाटिल'],
  'raut': ['राउत', 'राऊत'],
  'thakur': ['ठाकूर', 'ठाकुर'],
  'kadam': ['कदम'],
  'shinde': ['शिंदे'],
  'pawar': ['पवार'],
  'jadhav': ['जाधव'],
  'deshmukh': ['देशमुख'],
  'pune': ['पुणे'],
  'swargate': ['स्वारगेट'],
  'yerwada': ['येरवडा'],
  'kharadi': ['खराडी'],
  'hadapsar': ['हडपसर'],
  'kothrud': ['कोथरूड'],
};

export const IndicInput: React.FC<IndicInputProps> = ({
  value,
  onValueChange,
  targetScript = 'devanagari',
  label,
  helperText,
  className = '',
  placeholder,
  ...rest
}) => {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<any>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchTransliteration = async (text: string) => {
    if (!text || text.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    const lastToken = text.split(/\s+/).pop()?.toLowerCase() || '';
    if (!lastToken) return;

    // First check instant offline map
    const instant = OFFLINE_SUGGESTIONS[lastToken];
    if (instant) {
      setSuggestions(instant);
      setIsOpen(true);
      setSelectedIndex(0);
      return;
    }

    // Otherwise call backend transliteration endpoint
    try {
      const res = await fetch(`${API_BASE_URL}/intake/transliterate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: lastToken, target_script: targetScript })
      });
      if (res.ok) {
        const data = await res.json();
        const items = data.suggestions || data.candidates || [];
        if (items.length > 0) {
          setSuggestions(items);
          setIsOpen(true);
          setSelectedIndex(0);
        }
      }
    } catch {
      // Graceful offline fallback
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    onValueChange(val);

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      fetchTransliteration(val);
    }, 150);
  };

  const applySuggestion = (suggested: string) => {
    const tokens = value.split(/\s+/);
    tokens.pop(); // Replace the active token being typed
    tokens.push(suggested);
    const newValue = tokens.join(' ') + ' ';
    onValueChange(newValue);
    setIsOpen(false);
    setSuggestions([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      if (suggestions[selectedIndex]) {
        e.preventDefault();
        applySuggestion(suggestions[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative w-full">
      {label && (
        <label className="block text-xs font-semibold text-[#70685e] uppercase tracking-wider mb-1">
          {label}
        </label>
      )}

      <div className="relative flex items-center">
        <input
          {...rest}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`w-full px-3 py-2 pr-9 bg-white border border-[#eae4d9] rounded-lg text-sm text-[#191410] focus:outline-none focus:ring-2 focus:ring-[#d93829]/20 focus:border-[#d93829] transition-all font-sans ${className}`}
        />
        <div 
          className="absolute right-2.5 text-[#b0a89d] hover:text-[#d93829] transition-colors pointer-events-none"
          title="Transliteration Enabled (उदा. 'rahul' टाईप केल्यावर 'राहुल' सुचवले जाईल)"
        >
          <Languages className="w-4 h-4" />
        </div>
      </div>

      {isOpen && suggestions.length > 0 && (
        <div className="absolute left-0 right-0 mt-1 bg-white border border-[#eae4d9] rounded-lg shadow-lg z-50 overflow-hidden py-1">
          <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-[#b0a89d] tracking-wider border-b border-[#eae4d9]/50 flex justify-between items-center">
            <span>Devanagari Suggestions</span>
            <span className="font-mono text-[9px] text-[#70685e]">↵ Enter / Tab</span>
          </div>
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applySuggestion(s)}
              className={`w-full text-left px-3 py-1.5 text-sm font-medium transition-colors flex items-center justify-between ${
                idx === selectedIndex ? 'bg-[#fdeee9] text-[#d93829]' : 'text-[#191410] hover:bg-[#faf7f2]'
              }`}
            >
              <span>{s}</span>
              <span className="text-[10px] text-[#70685e] font-mono">#{idx + 1}</span>
            </button>
          ))}
        </div>
      )}

      {helperText && (
        <p className="mt-1 text-xs text-[#70685e]">{helperText}</p>
      )}
    </div>
  );
};
