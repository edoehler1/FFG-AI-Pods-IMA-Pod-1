import { useState, useMemo } from 'react';
import type { Signal } from '../../types/signal';

function parseFilingTitle(title: string): { company: string; filingType: string } {
  const match = title.match(/^(.+?)\s*[—–-]\s*(.+?)(?:\s+filing)?$/i);
  if (match) return { company: match[1].trim(), filingType: match[2].trim() };
  return { company: title, filingType: 'Filing' };
}

function getQuarter(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const month = date.getMonth();
  const q = Math.floor(month / 3) + 1;
  return `Q${q} ${date.getFullYear()}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const FILING_TYPE_COLORS: Record<string, string> = {
  '10-K': 'bg-emerald-100 text-emerald-800',
  '10-K/A': 'bg-emerald-100 text-emerald-800',
  '10-Q': 'bg-violet-100 text-violet-800',
  '10-Q/A': 'bg-violet-100 text-violet-800',
  '8-K': 'bg-blue-100 text-blue-800',
  '4': 'bg-slate-100 text-slate-700',
  'DEF 14A': 'bg-amber-100 text-amber-800',
};

const FILING_TYPES = ['All', '10-K', '10-Q', '8-K', '4', 'DEF 14A'];

interface FilingsViewProps {
  signals: Signal[];
  loading: boolean;
  error: string | null;
}

interface CompanyFilingGroup {
  company: string;
  filingType: string;
  filings: Signal[];
}

export default function FilingsView({ signals, loading, error }: FilingsViewProps) {
  const [filterType, setFilterType] = useState('All');
  const [filterCompany, setFilterCompany] = useState('');
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

  const companies = useMemo(() => {
    const set = new Set<string>();
    signals.forEach((s) => {
      const { company } = parseFilingTitle(s.title);
      set.add(company);
    });
    return Array.from(set).sort();
  }, [signals]);

  const grouped = useMemo(() => {
    const groups: Record<string, CompanyFilingGroup> = {};

    for (const signal of signals) {
      const { company, filingType } = parseFilingTitle(signal.title);

      if (filterType !== 'All' && !filingType.includes(filterType)) continue;
      if (filterCompany && company !== filterCompany) continue;

      const key = `${company}|||${filingType}`;
      if (!groups[key]) {
        groups[key] = { company, filingType, filings: [] };
      }
      groups[key].filings.push(signal);
    }

    for (const group of Object.values(groups)) {
      group.filings.sort((a, b) => {
        const da = a.published_at ? new Date(a.published_at).getTime() : 0;
        const db = b.published_at ? new Date(b.published_at).getTime() : 0;
        return db - da;
      });
    }

    return Object.values(groups).sort((a, b) => {
      if (a.company !== b.company) return a.company.localeCompare(b.company);
      const typeOrder = ['10-K', '10-Q', '8-K', '4', 'DEF 14A'];
      const ai = typeOrder.findIndex((t) => a.filingType.includes(t));
      const bi = typeOrder.findIndex((t) => b.filingType.includes(t));
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
  }, [signals, filterType, filterCompany]);

  if (loading) return <div className="text-center py-12 text-slate-500">Loading filings...</div>;
  if (error) return <div className="text-center py-12 text-red-600">{error}</div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4 bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Company</label>
          <select
            value={filterCompany}
            onChange={(e) => setFilterCompany(e.target.value)}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="">All Companies</option>
            {companies.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Filing Type</label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            {FILING_TYPES.map((t) => (
              <option key={t} value={t}>{t === 'All' ? 'All Types' : t}</option>
            ))}
          </select>
        </div>

        <div className="ml-auto text-sm text-slate-500">
          {grouped.length} group{grouped.length !== 1 ? 's' : ''} · {signals.length} total filings
        </div>
      </div>

      {grouped.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No filings match your filters.</div>
      ) : (
        <div className="space-y-3">
          {grouped.map((group) => {
            const key = `${group.company}|||${group.filingType}`;
            const isExpanded = expandedGroup === key;
            const typeColor = Object.entries(FILING_TYPE_COLORS).find(
              ([k]) => group.filingType.includes(k)
            )?.[1] || 'bg-slate-100 text-slate-700';

            return (
              <div key={key} className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedGroup(isExpanded ? null : key)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${typeColor}`}>
                      {group.filingType}
                    </span>
                    <span className="text-sm font-semibold text-slate-900">{group.company}</span>
                    <span className="text-xs text-slate-400">{group.filings.length} filing{group.filings.length !== 1 ? 's' : ''}</span>
                  </div>
                  <span className="text-slate-400 text-sm">{isExpanded ? '▲' : '▼'}</span>
                </button>

                {isExpanded && (
                  <div className="border-t border-slate-100">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-slate-50 text-left text-xs text-slate-500 uppercase tracking-wide">
                          <th className="px-4 py-2 font-medium">Quarter</th>
                          <th className="px-4 py-2 font-medium">Filed Date</th>
                          <th className="px-4 py-2 font-medium">Description</th>
                          <th className="px-4 py-2 font-medium text-right">Link</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.filings.map((filing) => (
                          <tr key={filing.id} className="border-t border-slate-50 hover:bg-slate-50">
                            <td className="px-4 py-2.5 font-medium text-slate-700">
                              {getQuarter(filing.published_at)}
                            </td>
                            <td className="px-4 py-2.5 text-slate-600">
                              {formatDate(filing.published_at)}
                            </td>
                            <td className="px-4 py-2.5 text-slate-500 max-w-xs truncate">
                              {filing.body || '—'}
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              {filing.url ? (
                                <a
                                  href={filing.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline"
                                >
                                  View
                                </a>
                              ) : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
