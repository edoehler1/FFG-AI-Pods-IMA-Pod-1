import { useState } from 'react';
import { formatDate } from '../../utils/formatters';
import type { CuratedIndustryNews } from '../../types/signal';
import { INDUSTRY_LABELS } from '../../utils/constants';

const CATEGORIES = [
  { key: 'all', label: 'All' },
  { key: 'regulatory', label: 'Regulatory & Policy', color: 'bg-amber-100 text-amber-800' },
  { key: 'market', label: 'Market & Macro', color: 'bg-blue-100 text-blue-800' },
  { key: 'supply_chain', label: 'Supply Chain', color: 'bg-green-100 text-green-800' },
  { key: 'labor', label: 'Labor & Workforce', color: 'bg-orange-100 text-orange-800' },
  { key: 'technology', label: 'Technology & Innovation', color: 'bg-purple-100 text-purple-800' },
] as const;

function getCategoryColor(category: string): string {
  const found = CATEGORIES.find((c) => c.key === category);
  return found && 'color' in found ? found.color : 'bg-slate-100 text-slate-700';
}

function getCategoryLabel(category: string): string {
  const found = CATEGORIES.find((c) => c.key === category);
  return found ? found.label : category;
}

interface IndustryNewsProps {
  curatedNews: CuratedIndustryNews[];
  industry: string | null;
  dateRange: { start: string; end: string } | null;
  loading: boolean;
  days: number;
  onDaysChange: (days: number) => void;
}

const DAY_OPTIONS = [7, 14, 30];

export default function IndustryNews({ curatedNews, industry, dateRange, loading, days, onDaysChange }: IndustryNewsProps) {
  const [activeCategory, setActiveCategory] = useState<string>('all');

  if (loading) {
    return <p className="text-sm text-slate-500 py-4">Curating sector intelligence...</p>;
  }

  const categoryCounts: Record<string, number> = {};
  for (const item of curatedNews) {
    categoryCounts[item.category] = (categoryCounts[item.category] || 0) + 1;
  }

  const filtered = activeCategory === 'all'
    ? curatedNews
    : curatedNews.filter((item) => item.category === activeCategory);

  const visibleCategories = CATEGORIES.filter(
    (c) => c.key === 'all' || (categoryCounts[c.key] || 0) > 0
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Sector Intelligence{industry ? `: ${INDUSTRY_LABELS[industry] || industry}` : ''}
          </h3>
          {dateRange && (
            <p className="text-xs text-slate-400 mt-0.5">
              {formatDate(dateRange.start)} — {formatDate(dateRange.end)}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => onDaysChange(d)}
              className={`text-xs px-2.5 py-1 rounded ${
                days === d
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-500 hover:bg-slate-100'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {curatedNews.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-slate-500 text-sm">No sector intelligence in the past {days} days.</p>
          {days < 30 && (
            <button
              onClick={() => onDaysChange(days === 7 ? 14 : 30)}
              className="text-xs text-blue-600 hover:text-blue-800 mt-2"
            >
              Try expanding to {days === 7 ? 14 : 30} days
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 mb-4">
            {visibleCategories.map((cat) => {
              const count = cat.key === 'all' ? curatedNews.length : (categoryCounts[cat.key] || 0);
              return (
                <button
                  key={cat.key}
                  onClick={() => setActiveCategory(cat.key)}
                  className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                    activeCategory === cat.key
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {cat.label} ({count})
                </button>
              );
            })}
          </div>

          <div className="space-y-3">
            {filtered.map((item) => (
              <div key={item.signal.id} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${getCategoryColor(item.category)}`}>
                    {getCategoryLabel(item.category)}
                  </span>
                  {item.signal.source_name?.includes('federal_register') && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                      Federal Register
                    </span>
                  )}
                </div>
                <a
                  href={item.signal.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-slate-900 hover:text-blue-600 leading-snug"
                >
                  {item.signal.title}
                </a>
                <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                  <span>{item.signal.source_name}</span>
                  {item.signal.published_at && <span>{formatDate(item.signal.published_at)}</span>}
                </div>
                {item.partner_relevance && (
                  <p className="mt-2 text-sm text-slate-600 bg-slate-50 rounded p-2">
                    {item.partner_relevance}
                  </p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
