import { formatDate } from '../../utils/formatters';
import type { CuratedCompanyNews } from '../../types/signal';

const TAG_COLORS: Record<string, string> = {
  'M&A': 'bg-red-100 text-red-800',
  'Restructuring': 'bg-purple-100 text-purple-800',
  'Leadership': 'bg-indigo-100 text-indigo-800',
  'Regulatory': 'bg-amber-100 text-amber-800',
  'Contract': 'bg-green-100 text-green-800',
  'Competitive': 'bg-orange-100 text-orange-800',
  'Financial': 'bg-blue-100 text-blue-800',
  'Operational': 'bg-slate-100 text-slate-700',
};

interface CompanyNewsProps {
  curatedNews: CuratedCompanyNews[];
  dateRange: { start: string; end: string } | null;
  loading: boolean;
  days: number;
  onDaysChange: (days: number) => void;
}

const DAY_OPTIONS = [7, 14, 30];

export default function CompanyNews({ curatedNews, dateRange, loading, days, onDaysChange }: CompanyNewsProps) {
  if (loading) {
    return <p className="text-sm text-slate-500 py-4">Curating this week's intelligence...</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">This Week's Intelligence</h3>
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
          <p className="text-slate-500 text-sm">No actionable company news in the past {days} days.</p>
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
        <div className="space-y-3">
          {curatedNews.map((item) => (
            <div key={item.signal.id} className="border border-slate-200 rounded-lg p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TAG_COLORS[item.strategic_tag] || TAG_COLORS['Operational']}`}>
                      {item.strategic_tag}
                    </span>
                    {item.importance_score >= 80 && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-50 text-red-700">
                        Critical
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
                </div>
              </div>

              {item.why_it_matters && (
                <div className="mt-3 bg-slate-50 rounded p-3">
                  <p className="text-xs font-medium text-slate-500 mb-1">Why it matters</p>
                  <p className="text-sm text-slate-700">{item.why_it_matters}</p>
                </div>
              )}

              {item.suggested_action && (
                <div className="mt-2 bg-blue-50 rounded p-3">
                  <p className="text-xs font-medium text-blue-600 mb-1">Suggested action</p>
                  <p className="text-sm text-slate-700">{item.suggested_action}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
