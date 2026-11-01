import React, { useState, useEffect } from 'react';
import { 
  Check, X, Edit2, ShieldAlert, Sparkles, AlertCircle, 
  HelpCircle, CheckCircle2, ChevronRight, User, Calendar, 
  DollarSign, MapPin, Car, BookOpen, Quote, Clock, CheckCheck
} from 'lucide-react';
import { IntakeItemModel, ProposedField, FieldConfirmation } from '../../services/intakeService';
import { IndicInput } from '../common/IndicInput';
import { formatIndianCurrency, formatIndianDate } from '../../utils/indianFormatters';
import { useTranslation } from 'react-i18next';

interface ReadingCardProps {
  item: IntakeItemModel;
  onConfirm: (confirmations: FieldConfirmation[]) => Promise<void>;
  onRejectAll: (reason: string) => Promise<void>;
  isSubmitting?: boolean;
}

export const ReadingCard: React.FC<ReadingCardProps> = ({
  item,
  onConfirm,
  onRejectAll,
  isSubmitting = false
}) => {
  const { t } = useTranslation();

  // State of confirmations per field_key
  const [fieldDecisions, setFieldDecisions] = useState<Record<string, {
    action: 'confirm' | 'edit' | 'reject';
    value: any;
    notes?: string;
  }>>({});

  const [activeFieldKey, setActiveFieldKey] = useState<string | null>(null);
  const [editingFieldKey, setEditingFieldKey] = useState<string | null>(null);

  // Initialize decisions with default 'confirm' for high confidence or pending
  useEffect(() => {
    const initial: Record<string, any> = {};
    item.proposed_fields.forEach(f => {
      initial[f.field_key] = {
        action: f.confidence >= 0.85 ? 'confirm' : 'confirm',
        value: f.value,
        notes: ''
      };
    });
    setFieldDecisions(initial);
    if (item.proposed_fields.length > 0) {
      setActiveFieldKey(item.proposed_fields[0].field_key);
    }
  }, [item]);

  // Global Keyboard shortcuts listener: C, E, R, Tab
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if officer is typing in an input/textarea
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if (!activeFieldKey) return;

      const currentIdx = item.proposed_fields.findIndex(f => f.field_key === activeFieldKey);

      if (e.key.toLowerCase() === 'c') {
        e.preventDefault();
        setFieldDecisions(prev => ({
          ...prev,
          [activeFieldKey]: { ...prev[activeFieldKey], action: 'confirm' }
        }));
        setEditingFieldKey(null);
      } else if (e.key.toLowerCase() === 'e') {
        e.preventDefault();
        setEditingFieldKey(activeFieldKey);
        setFieldDecisions(prev => ({
          ...prev,
          [activeFieldKey]: { ...prev[activeFieldKey], action: 'edit' }
        }));
      } else if (e.key.toLowerCase() === 'r') {
        e.preventDefault();
        setFieldDecisions(prev => ({
          ...prev,
          [activeFieldKey]: { ...prev[activeFieldKey], action: 'reject' }
        }));
        setEditingFieldKey(null);
      } else if (e.key === 'Tab' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (currentIdx !== -1 && currentIdx < item.proposed_fields.length - 1) {
          setActiveFieldKey(item.proposed_fields[currentIdx + 1].field_key);
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (currentIdx > 0) {
          setActiveFieldKey(item.proposed_fields[currentIdx - 1].field_key);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeFieldKey, item.proposed_fields]);

  const handleFieldAction = (fieldKey: string, action: 'confirm' | 'edit' | 'reject') => {
    setFieldDecisions(prev => ({
      ...prev,
      [fieldKey]: { ...prev[fieldKey], action }
    }));
    if (action === 'edit') {
      setEditingFieldKey(fieldKey);
    } else {
      setEditingFieldKey(null);
    }
  };

  const handleValueChange = (fieldKey: string, newValue: any) => {
    setFieldDecisions(prev => ({
      ...prev,
      [fieldKey]: { ...prev[fieldKey], value: newValue, action: 'edit' }
    }));
  };

  const handleAcceptAllHigh = () => {
    const updated = { ...fieldDecisions };
    item.proposed_fields.forEach(f => {
      if (f.confidence >= 0.85) {
        updated[f.field_key] = { ...updated[f.field_key], action: 'confirm' };
      }
    });
    setFieldDecisions(updated);
  };

  const handleSubmitAll = async () => {
    const payload: FieldConfirmation[] = item.proposed_fields.map(f => {
      const decision = fieldDecisions[f.field_key] || { action: 'confirm', value: f.value };
      return {
        field_key: f.field_key,
        field_group: f.field_group,
        action: decision.action,
        confirmed_value: decision.action === 'reject' ? null : decision.value,
        ai_value: f.value,
        correction_notes: decision.notes
      };
    });
    await onConfirm(payload);
  };

  // Group fields
  const groupOrder: Array<{ group: ProposedField['field_group']; label: string; icon: any }> = [
    { group: 'people', label: 'People Mentioned (व्यक्ती व भूमिका)', icon: User },
    { group: 'dates', label: 'Dates & Times (दिनांक व वेळ)', icon: Calendar },
    { group: 'amounts', label: 'Amounts & Valuables (रक्कम व मुद्देमाल)', icon: DollarSign },
    { group: 'places', label: 'Locations & Jurisdiction (घटनास्थळ व ठाणे)', icon: MapPin },
    { group: 'vehicles', label: 'Vehicles (वाहने)', icon: Car },
    { group: 'sections', label: 'Penal Sections & Procedures (कलमे व तपास कार्य)', icon: BookOpen },
  ];

  const grouped = groupOrder.map(g => ({
    ...g,
    fields: item.proposed_fields.filter(f => f.field_group === g.group)
  })).filter(g => g.fields.length > 0);

  return (
    <div className="bg-white border border-[#eae4d9] rounded-xl shadow-sm overflow-hidden select-none">
      {/* Header Banner */}
      <div className="p-5 border-b border-[#eae4d9] bg-[#faf7f2]/70 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-[#fdeee9] text-[#d93829] border border-[#d93829]/20 uppercase">
              {item.channel.replace('_', ' ')}
            </span>
            <span className="text-xs text-[#70685e] font-mono">
              SHA-256: {item.file_hash.slice(0, 12)}...
            </span>
            <span className="text-xs text-[#b0a89d]">
              • {formatIndianDate(item.created_at)}
            </span>
          </div>
          <h2 className="text-xl font-bold font-serif text-[#191410] tracking-tight">
            {item.title}
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleAcceptAllHigh}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors cursor-pointer"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Accept All High Confidence (85%+)
          </button>
          <button
            onClick={handleSubmitAll}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-[#d93829] text-white hover:bg-[#bf2b1d] transition-all shadow-sm cursor-pointer disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            Commit Confirmed Fields
          </button>
        </div>
      </div>

      {/* Strict Isolation Notice */}
      <div className="px-5 py-2.5 bg-amber-50/70 border-b border-amber-200/60 flex items-center justify-between text-xs text-amber-900">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0" />
          <span className="font-medium">
            {t('unconfirmed_isolation_notice')}
          </span>
        </div>
        <div className="hidden md:flex items-center gap-3 font-mono text-[11px] text-amber-800">
          <span>Shortcuts:</span>
          <span className="px-1.5 py-0.5 bg-amber-100 rounded border border-amber-300 font-bold">[C] Confirm</span>
          <span className="px-1.5 py-0.5 bg-amber-100 rounded border border-amber-300 font-bold">[E] Edit</span>
          <span className="px-1.5 py-0.5 bg-amber-100 rounded border border-amber-300 font-bold">[R] Reject</span>
        </div>
      </div>

      {/* Main Grid View */}
      <div className="p-6 space-y-6">
        {grouped.map(({ group, label, icon: Icon, fields }) => (
          <div key={group} className="space-y-3">
            <div className="flex items-center gap-2 pb-1 border-b border-[#eae4d9]">
              <Icon className="w-4 h-4 text-[#d93829]" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-[#70685e]">
                {label} ({fields.length})
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {fields.map(field => {
                const decision = fieldDecisions[field.field_key] || { action: 'confirm', value: field.value };
                const isActive = activeFieldKey === field.field_key;
                const isEditing = editingFieldKey === field.field_key;

                // Confidence badge styling
                const confPercent = Math.round(field.confidence * 100);
                const confColor = field.confidence >= 0.85
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : field.confidence >= 0.60
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200';

                return (
                  <div
                    key={field.field_key}
                    onClick={() => setActiveFieldKey(field.field_key)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
                      isActive
                        ? 'border-[#d93829] shadow-sm bg-[#faf7f2]/50 ring-1 ring-[#d93829]/20'
                        : 'border-[#eae4d9] bg-white hover:border-[#b0a89d]'
                    }`}
                  >
                    {/* Top Row: Label, Confidence, Ambiguity Warning */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <span className="text-xs font-semibold text-[#70685e]">
                          {field.field_label}
                        </span>
                        {field.is_ambiguous && (
                          <span className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                            <AlertCircle className="w-3 h-3 text-amber-700" />
                            Date Ambiguity
                          </span>
                        )}
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-bold border ${confColor}`}>
                        {confPercent}%
                      </span>
                    </div>

                    {/* Value Display / Inline Edit with Transliteration */}
                    <div className="mb-2">
                      {isEditing ? (
                        <div className="space-y-1.5" onClick={(e) => e.stopPropagation()}>
                          <IndicInput
                            value={String(decision.value || '')}
                            onValueChange={(val) => handleValueChange(field.field_key, val)}
                            placeholder="Type corrected name or text..."
                            className="text-sm font-semibold"
                            autoFocus
                          />
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => setEditingFieldKey(null)}
                              className="px-2.5 py-1 text-[11px] font-bold bg-emerald-700 text-white rounded hover:bg-emerald-800"
                            >
                              Done Editing
                            </button>
                            <span className="text-[10px] text-[#70685e]">
                              (Devanagari transliteration supported)
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-baseline justify-between">
                          <p className={`text-base font-bold font-sans ${
                            decision.action === 'reject' ? 'line-through text-neutral-400' : 'text-[#191410]'
                          }`}>
                            {typeof decision.value === 'number' && field.field_group === 'amounts'
                              ? formatIndianCurrency(decision.value)
                              : String(decision.value)}
                          </p>
                          {decision.action === 'edit' && (
                            <span className="text-[11px] font-mono text-[#d93829] font-bold">
                              [Edited by Officer]
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Ambiguous Alternatives if present */}
                    {field.is_ambiguous && field.alternative_readings && field.alternative_readings.length > 0 && (
                      <div className="mb-2 p-2 bg-amber-50 rounded border border-amber-200 text-xs">
                        <span className="font-semibold text-amber-900">Alternative Reading: </span>
                        {field.alternative_readings.map((alt, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleValueChange(field.field_key, alt);
                            }}
                            className="underline text-amber-800 font-mono ml-1 hover:text-amber-950"
                          >
                            Use '{alt}'
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Source Citation / Bounding Quote */}
                    {field.source_quote && (
                      <div className="p-2 bg-[#f4efe6]/60 rounded-md text-[11px] text-[#6e665d] flex items-start gap-1.5 mb-3 font-mono">
                        <Quote className="w-3.5 h-3.5 text-[#b0a89d] shrink-0 mt-0.5" />
                        <span className="line-clamp-2 italic">"{field.source_quote}"</span>
                      </div>
                    )}

                    {/* Action Bar (Confirm, Edit, Reject) */}
                    <div className="flex items-center justify-between pt-2 border-t border-[#eae4d9]/70 text-xs">
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFieldAction(field.field_key, 'confirm');
                          }}
                          className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                            decision.action === 'confirm'
                              ? 'bg-emerald-600 text-white shadow-2xs'
                              : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                          }`}
                        >
                          <Check className="w-3.5 h-3.5" />
                          Confirm
                        </button>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFieldAction(field.field_key, 'edit');
                          }}
                          className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                            decision.action === 'edit'
                              ? 'bg-[#d93829] text-white shadow-2xs'
                              : 'bg-neutral-100 text-neutral-800 hover:bg-neutral-200'
                          }`}
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                          Edit
                        </button>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFieldAction(field.field_key, 'reject');
                          }}
                          className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                            decision.action === 'reject'
                              ? 'bg-rose-600 text-white shadow-2xs'
                              : 'bg-rose-50 text-rose-800 hover:bg-rose-100'
                          }`}
                        >
                          <X className="w-3.5 h-3.5" />
                          Reject
                        </button>
                      </div>

                      <span className="text-[11px] font-mono text-[#b0a89d]">
                        {decision.action === 'confirm' && '✓ Confirmed'}
                        {decision.action === 'edit' && '✏ Modified'}
                        {decision.action === 'reject' && '✕ Discarded'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Raw OCR / Text Accordion Drawer */}
      {item.raw_text && (
        <details className="border-t border-[#eae4d9] bg-[#faf7f2]/60 p-4">
          <summary className="text-xs font-bold uppercase tracking-wider text-[#70685e] cursor-pointer hover:text-[#191410] flex items-center gap-2">
            <span>View Original Document / Transcription Content</span>
            <span className="text-[10px] font-normal font-mono text-[#b0a89d]">
              ({item.raw_text.length} characters)
            </span>
          </summary>
          <pre className="mt-3 p-3 bg-white border border-[#eae4d9] rounded-lg text-xs font-mono text-[#191410] whitespace-pre-wrap overflow-x-auto max-h-60">
            {item.raw_text}
          </pre>
        </details>
      )}
    </div>
  );
};

