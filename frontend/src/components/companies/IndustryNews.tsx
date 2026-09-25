import { useState } from 'react';
import type { Signal } from '../../types/signal';
import SignalCard from '../signals/SignalCard';
import { INDUSTRY_LABELS } from '../../utils/constants';

interface IndustryNewsSignal extends Signal {
  news_category?: string;
}

interface IndustryNewsProps {
  signals: IndustryNewsSignal[];
  industry: string | null;
  subSector: string | null;
}

const CATEGORIES = [
  { key: 'all', label: 'All' },
  { key: 'regulatory', label: 'Regulatory' },
  { key: 'macro', label: 'Macro' },
  { key: 'company_moves', label: 'Company Moves' },
  { key: 'trends', label: 'Trends' },
];

const CATEGORY_COLORS: Record<string, string> = {
  regulatory: 'bg-amber-100 text-amber-800',
  macro: 'bg-blue-100 text-blue-800',
  company_moves: 'bg-red-100 text-red-800',
  trends: 'bg-purple-100 text-purple-800',
};

export default function IndustryNews({ signals, industry, subSector }: IndustryNewsProps) {
  const [activeCategory, setActiveCategory] = useState('all');

  const label = industry ? (INDUSTRY_LABELS[industry] || industry) : 'General';
  const subLabel = subSector ? ` / ${subSector.replace(/_/g, ' ')}` : '';

  const filtered = activeCategory === 'all'
    ? signals
    : signals.filter((s) => s.news_category === activeCategory);

  const categoryCounts: Record<string, number> = {};
  for (const s of signals) {
    const cat = s.news_category || 'general';
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  }

  return (
    <div>
      <p className="text-xs text-slate-400 mb-3">
        Signals from the {label}{subLabel} sector (not company-specific)
      </p>

      <div className="flex flex-wrap gap-2 mb-4">
        {CATEGORIES.map((cat) => {
          const count = cat.key === 'all' ? signals.length : (categoryCounts[cat.key] || 0);
          if (cat.key !== 'all' && count === 0) return null;
          const isActive = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              onClick={() => setActiveCategory(cat.key)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-slate-900 text-white'
                  : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
              }`}
            >
              {cat.label}{count > 0 ? ` (${count})` : ''}
            </button>
          );
        })}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-slate-500 py-4">No signals in this category.</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((signal) => (
            <div key={signal.id}>
              {signal.news_category && signal.news_category !== 'general' && (
                <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full mb-1 ${CATEGORY_COLORS[signal.news_category] || 'bg-slate-100 text-slate-600'}`}>
                  {signal.news_category}
                </span>
              )}
              <SignalCard signal={signal} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
