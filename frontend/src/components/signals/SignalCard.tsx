import type { Signal } from '../../types/signal';

const TYPE_COLORS: Record<string, string> = {
  news: 'bg-blue-100 text-blue-800',
  regulatory: 'bg-amber-100 text-amber-800',
  earnings: 'bg-green-100 text-green-800',
  leadership: 'bg-purple-100 text-purple-800',
  ma: 'bg-red-100 text-red-800',
  gov_contract: 'bg-indigo-100 text-indigo-800',
};

const INDUSTRY_LABELS: Record<string, string> = {
  automotive: 'Auto',
  aerospace_defense: 'A&D',
  energy: 'Energy',
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

interface SignalCardProps {
  signal: Signal;
}

export default function SignalCard({ signal }: SignalCardProps) {
  const typeColor = TYPE_COLORS[signal.signal_type || ''] || 'bg-slate-100 text-slate-800';
  const industryLabel = INDUSTRY_LABELS[signal.industry || ''] || signal.industry;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            {signal.signal_type && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeColor}`}>
                {signal.signal_type.replace('_', ' ')}
              </span>
            )}
            {industryLabel && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {industryLabel}
              </span>
            )}
            {signal.sub_sector && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-50 text-slate-500 border border-slate-200">
                {signal.sub_sector.replace(/_/g, ' ')}
              </span>
            )}
          </div>

          <h3 className="text-sm font-semibold text-slate-900 leading-snug mb-1">
            {signal.url ? (
              <a
                href={signal.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 hover:underline"
              >
                {signal.title}
              </a>
            ) : (
              signal.title
            )}
          </h3>

          {signal.body && !signal.body.startsWith('<') && (
            <p className="text-sm text-slate-600 line-clamp-2 mb-2">{signal.body}</p>
          )}

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>{signal.source_name}</span>
            {signal.published_at && <span>{formatDate(signal.published_at)}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
