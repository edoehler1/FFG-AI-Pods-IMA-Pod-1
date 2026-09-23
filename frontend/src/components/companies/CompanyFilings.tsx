import type { Signal } from '../../types/signal';

const FORM_COLORS: Record<string, string> = {
  '10-K': 'bg-green-100 text-green-800',
  '10-K/A': 'bg-green-100 text-green-800',
  '10-Q': 'bg-blue-100 text-blue-800',
  '10-Q/A': 'bg-blue-100 text-blue-800',
  '8-K': 'bg-amber-100 text-amber-800',
};

function parseFormType(title: string): string {
  const match = title.match(/— (.+?) filing$/);
  return match ? match[1] : 'Filing';
}

function groupByYear(filings: Signal[]): Record<string, Signal[]> {
  const groups: Record<string, Signal[]> = {};
  for (const f of filings) {
    const year = f.published_at ? new Date(f.published_at).getFullYear().toString() : 'Unknown';
    if (!groups[year]) groups[year] = [];
    groups[year].push(f);
  }
  return groups;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

interface CompanyFilingsProps {
  filings: Signal[];
}

export default function CompanyFilings({ filings }: CompanyFilingsProps) {
  if (filings.length === 0) {
    return <p className="text-sm text-slate-500 py-4">No SEC filings found for this company.</p>;
  }

  const grouped = groupByYear(filings);
  const years = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  return (
    <div className="space-y-6">
      {years.map((year) => (
        <div key={year}>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">{year}</h3>
          <div className="space-y-2">
            {grouped[year].map((filing) => {
              const formType = parseFormType(filing.title);
              const badgeColor = FORM_COLORS[formType] || 'bg-slate-100 text-slate-700';
              const companyName = filing.title.split(' — ')[0];

              return (
                <div key={filing.id} className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-4 py-3">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badgeColor}`}>
                    {formType}
                  </span>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-slate-900">{companyName}</span>
                    {filing.body && (
                      <p className="text-xs text-slate-500 truncate mt-0.5">{filing.body}</p>
                    )}
                  </div>
                  <span className="text-xs text-slate-400 shrink-0">{formatDate(filing.published_at)}</span>
                  {filing.url && (
                    <a
                      href={filing.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline shrink-0"
                    >
                      View Filing
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
