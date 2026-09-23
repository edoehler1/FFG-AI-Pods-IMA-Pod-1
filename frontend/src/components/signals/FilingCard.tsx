import type { Signal } from '../../types/signal';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function parseFilingTitle(title: string): { company: string; filingType: string } {
  const match = title.match(/^(.+?)\s*[—–-]\s*(.+?)(?:\s+filing)?$/i);
  if (match) {
    return { company: match[1].trim(), filingType: match[2].trim() };
  }
  return { company: title, filingType: 'Filing' };
}

const FILING_TYPE_COLORS: Record<string, string> = {
  '8-K': 'bg-blue-100 text-blue-800',
  '10-K': 'bg-emerald-100 text-emerald-800',
  '10-Q': 'bg-violet-100 text-violet-800',
  '4': 'bg-slate-100 text-slate-700',
};

interface FilingCardProps {
  signal: Signal;
}

export default function FilingCard({ signal }: FilingCardProps) {
  const { company, filingType } = parseFilingTitle(signal.title);
  const typeColor = Object.entries(FILING_TYPE_COLORS).find(
    ([key]) => filingType.includes(key)
  )?.[1] || 'bg-slate-100 text-slate-700';

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${typeColor}`}>
              {filingType}
            </span>
            {signal.sub_sector && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-50 text-slate-500 border border-slate-200">
                {signal.sub_sector.replace(/_/g, ' ')}
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-slate-900">{company}</h3>
          {signal.body && (
            <p className="text-sm text-slate-500 mt-1 line-clamp-2">{signal.body}</p>
          )}
        </div>

        <div className="text-right shrink-0">
          <div className="text-sm font-medium text-slate-700">
            {formatDate(signal.published_at)}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
              Analysis coming soon
            </span>
          </div>
          {signal.url && (
            <a
              href={signal.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 text-xs text-blue-600 hover:underline"
            >
              View Filing
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
