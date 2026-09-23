import { useState } from 'react';
import type { Signal } from '../../types/signal';
import { triggerFinancialAnalysis } from '../../api/companies';

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

function markdownToHtml(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*\[(.+?)\]\*\*/g, '<strong>[$1]</strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul\/>])/gm, '<p>')
    .replace(/<p><\/p>/g, '')
    .replace(/<p>(<[hul])/g, '$1')
    .replace(/(<\/[hul].*?>)<\/p>/g, '$1');
}

interface CompanyFilingsProps {
  filings: Signal[];
  companyId?: string;
}

export default function CompanyFilings({ filings, companyId }: CompanyFilingsProps) {
  const [financialNarrative, setFinancialNarrative] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const handleGenerateFinancial = async () => {
    if (!companyId) return;
    setGenerating(true);
    setGenError(null);
    try {
      const data = await triggerFinancialAnalysis(companyId);
      setFinancialNarrative(data.narrative);
    } catch (err: any) {
      setGenError(err.message || 'Failed to generate financial analysis');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {companyId && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-900">Financial Analysis</h3>
            <button
              onClick={handleGenerateFinancial}
              disabled={generating}
              className="bg-slate-900 text-white px-3 py-1 rounded text-xs font-medium hover:bg-slate-800 disabled:opacity-50"
            >
              {generating ? 'Analyzing...' : financialNarrative ? 'Refresh Analysis' : 'Generate Financial Analysis'}
            </button>
          </div>
          {genError && <p className="text-red-600 text-sm mb-2">{genError}</p>}
          {financialNarrative ? (
            <div
              className="prose prose-slate prose-sm max-w-none
                prose-headings:text-slate-900 prose-headings:font-semibold
                prose-h1:text-lg prose-h1:mb-2
                prose-h2:text-sm prose-h2:mt-4 prose-h2:mb-1
                prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1
                prose-li:my-0.5 prose-p:my-1.5
                prose-strong:text-slate-700
                prose-em:text-slate-500"
              dangerouslySetInnerHTML={{ __html: markdownToHtml(financialNarrative) }}
            />
          ) : !generating ? (
            <p className="text-sm text-slate-500">
              Click "Generate Financial Analysis" to get an AI-powered review of this company's SEC filings,
              cross-referenced with recent news signals.
            </p>
          ) : null}
        </div>
      )}

      {filings.length === 0 ? (
        <p className="text-sm text-slate-500 py-4">No SEC filings found for this company.</p>
      ) : (
        (() => {
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
        })()
      )}
    </div>
  );
}
