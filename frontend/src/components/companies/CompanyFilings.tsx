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

function getQuarterLabel(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `Q${q} ${d.getFullYear()}`;
}

function getAnnualLabel(dateStr: string | null): string {
  if (!dateStr) return '';
  return `FY ${new Date(dateStr).getFullYear()}`;
}

const FILING_TYPE_ORDER = ['10-K', '10-K/A', '10-Q', '10-Q/A', '8-K', 'DEF 14A'];
const FILING_TYPE_DESCRIPTIONS: Record<string, string> = {
  '10-K': 'Annual Reports',
  '10-K/A': 'Amended Annual Reports',
  '10-Q': 'Quarterly Reports',
  '10-Q/A': 'Amended Quarterly Reports',
  '8-K': 'Current Reports (Material Events)',
  'DEF 14A': 'Proxy Statements',
};

interface FilingGroup {
  formType: string;
  label: string;
  filings: Signal[];
}

function groupByFilingType(filings: Signal[]): FilingGroup[] {
  const groups: Record<string, Signal[]> = {};
  for (const f of filings) {
    const formType = parseFormType(f.title);
    if (!groups[formType]) groups[formType] = [];
    groups[formType].push(f);
  }

  for (const arr of Object.values(groups)) {
    arr.sort((a, b) => {
      const da = a.published_at ? new Date(a.published_at).getTime() : 0;
      const db = b.published_at ? new Date(b.published_at).getTime() : 0;
      return db - da;
    });
  }

  return FILING_TYPE_ORDER
    .filter((ft) => groups[ft])
    .map((ft) => ({
      formType: ft,
      label: FILING_TYPE_DESCRIPTIONS[ft] || ft,
      filings: groups[ft],
    }));
}

import { markdownToHtml, formatDate } from '../../utils/formatters';

interface CompanyFilingsProps {
  filings: Signal[];
  companyId?: string;
}

export default function CompanyFilings({ filings, companyId }: CompanyFilingsProps) {
  const [financialNarrative, setFinancialNarrative] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === filings.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filings.map((f) => f.id)));
    }
  };

  const handleGenerate = async (useSelected: boolean) => {
    if (!companyId) return;
    setGenerating(true);
    setGenError(null);
    try {
      const ids = useSelected && selectedIds.size > 0 ? Array.from(selectedIds) : undefined;
      const data = await triggerFinancialAnalysis(companyId, ids);
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
            <div className="flex items-center gap-2">
              {selectedIds.size > 0 && (
                <button
                  onClick={() => handleGenerate(true)}
                  disabled={generating}
                  className="bg-blue-600 text-white px-3 py-1 rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {generating ? 'Analyzing...' : `Analyze Selected (${selectedIds.size})`}
                </button>
              )}
              <button
                onClick={() => handleGenerate(false)}
                disabled={generating}
                className="bg-slate-900 text-white px-3 py-1 rounded text-xs font-medium hover:bg-slate-800 disabled:opacity-50"
              >
                {generating ? 'Analyzing...' : financialNarrative ? 'Refresh All' : 'Analyze All Filings'}
              </button>
            </div>
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
              Click "Analyze All Filings" for a full review, or check specific filings below and click "Analyze Selected" for a focused analysis.
            </p>
          ) : null}
        </div>
      )}

      {filings.length === 0 ? (
        <p className="text-sm text-slate-500 py-4">No SEC filings found for this company.</p>
      ) : (
        <>
          {filings.length > 1 && (
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedIds.size === filings.length}
                  onChange={selectAll}
                  className="w-3.5 h-3.5 rounded border-slate-300"
                />
                Select all ({filings.length})
              </label>
              {selectedIds.size > 0 && (
                <span className="text-xs text-slate-400">{selectedIds.size} selected</span>
              )}
            </div>
          )}

          {groupByFilingType(filings).map((group) => {
            const badgeColor = FORM_COLORS[group.formType] || 'bg-slate-100 text-slate-700';
            const isAnnual = group.formType.startsWith('10-K');

            return (
              <div key={group.formType} className="border border-slate-200 rounded-lg overflow-hidden">
                <div className="bg-slate-50 px-4 py-3 flex items-center gap-3">
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${badgeColor}`}>
                    {group.formType}
                  </span>
                  <span className="text-sm font-semibold text-slate-700">{group.label}</span>
                  <span className="text-xs text-slate-400">{group.filings.length} filing{group.filings.length !== 1 ? 's' : ''}</span>
                </div>
                <div className="divide-y divide-slate-100">
                  {group.filings.map((filing) => {
                    const periodLabel = isAnnual
                      ? getAnnualLabel(filing.published_at)
                      : getQuarterLabel(filing.published_at);
                    const isSelected = selectedIds.has(filing.id);

                    return (
                      <div
                        key={filing.id}
                        className={`flex items-center gap-3 px-4 py-2.5 ${
                          isSelected ? 'bg-blue-50/50' : 'hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelection(filing.id)}
                          className="w-3.5 h-3.5 rounded border-slate-300 shrink-0"
                        />
                        <span className="text-sm font-medium text-slate-900 w-24 shrink-0">
                          {periodLabel}
                        </span>
                        <span className="text-xs text-slate-400 w-32 shrink-0">
                          {formatDate(filing.published_at)}
                        </span>
                        <span className="text-xs text-slate-500 flex-1 truncate">
                          {filing.body || '—'}
                        </span>
                        {filing.url && (
                          <a
                            href={filing.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 hover:underline shrink-0"
                          >
                            View
                          </a>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
