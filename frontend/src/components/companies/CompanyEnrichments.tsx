import { useEffect, useState } from 'react';
import { fetchCompanyEnrichments, fetchEnrichments, type Enrichment } from '../../api/enrichments';
import { markdownToHtml, formatDate } from '../../utils/formatters';

const SOURCE_LABELS: Record<string, string> = {
  capiq: 'Capital IQ',
  boardex: 'BoardEx',
  earnings: 'Earnings Call',
  emis: 'EMIS Ownership',
  ibis: 'IBISWorld',
  factiva: 'Factiva',
  web: 'Web Search',
  sec_mcp_risk: 'SEC Risk Factors',
  sec_mcp_mda: 'SEC MD&A',
  connectedsource: 'PwC Insights',
  vim: 'Value in Motion',
  ceo_survey: 'CEO Survey',
  salesforce: 'Salesforce Pipeline',
  people_engagements: 'PwC Engagement History',
};

const SOURCE_COLORS: Record<string, string> = {
  capiq: 'bg-blue-50 text-blue-700 border-blue-200',
  boardex: 'bg-purple-50 text-purple-700 border-purple-200',
  earnings: 'bg-green-50 text-green-700 border-green-200',
  emis: 'bg-amber-50 text-amber-700 border-amber-200',
  ibis: 'bg-teal-50 text-teal-700 border-teal-200',
  factiva: 'bg-red-50 text-red-700 border-red-200',
  sec_mcp_risk: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  sec_mcp_mda: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  connectedsource: 'bg-orange-50 text-orange-700 border-orange-200',
  vim: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  ceo_survey: 'bg-rose-50 text-rose-700 border-rose-200',
  web: 'bg-slate-50 text-slate-700 border-slate-200',
  salesforce: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  people_engagements: 'bg-violet-50 text-violet-700 border-violet-200',
};

interface Props {
  companyId: string;
  companyIndustry?: string | null;
}

export default function CompanyEnrichments({ companyId, companyIndustry }: Props) {
  const [enrichments, setEnrichments] = useState<Enrichment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    setError(false);

    const fetches: Promise<Enrichment[]>[] = [
      fetchCompanyEnrichments(companyId).then((res) => res.enrichments),
    ];

    if (companyIndustry) {
      fetches.push(
        fetchEnrichments({ entity_type: 'industry', entity_id: companyIndustry })
          .then((res) => res.enrichments)
      );
    }

    Promise.all(fetches)
      .then((results) => {
        const merged = results.flat();
        const seen = new Set<string>();
        const deduped = merged.filter((e) => {
          if (seen.has(e.id)) return false;
          seen.add(e.id);
          return true;
        });
        setEnrichments(deduped);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [companyId, companyIndustry]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (loading) return <p className="text-sm text-slate-500">Loading enrichments...</p>;
  if (error) return <p className="text-sm text-red-500">Failed to load enrichments. Refresh to try again.</p>;

  if (enrichments.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-slate-500">No MCP enrichment data available yet.</p>
        <p className="text-xs text-slate-400 mt-2">
          Run enrichment from Claude Code to populate this section with data from
          Capital IQ, Factiva, SEC filings, BoardEx, and PwC thought leadership.
        </p>
      </div>
    );
  }

  const companyEnrichments = enrichments.filter((e) => e.entity_type === 'company');
  const industryEnrichments = enrichments.filter((e) => e.entity_type === 'industry');

  return (
    <div className="space-y-6">
      {companyEnrichments.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">
            Company Intelligence ({companyEnrichments.length})
          </h2>
          {companyEnrichments.map((e) => renderCard(e, expanded, toggle))}
        </div>
      )}

      {industryEnrichments.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">
            Industry Intelligence ({industryEnrichments.length})
          </h2>
          {industryEnrichments.map((e) => renderCard(e, expanded, toggle))}
        </div>
      )}
    </div>
  );
}

function renderCard(e: Enrichment, expanded: Set<string>, toggle: (id: string) => void) {
  const isOpen = expanded.has(e.id);
  const color = SOURCE_COLORS[e.mcp_source] || 'bg-slate-50 text-slate-700 border-slate-200';
  return (
    <div key={e.id} className={`border rounded-lg ${isOpen ? 'border-slate-300' : 'border-slate-200'}`}>
      <button
        onClick={() => toggle(e.id)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 rounded-lg"
      >
        <div className="flex items-center gap-3">
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${color}`}>
            {SOURCE_LABELS[e.mcp_source] || e.mcp_source}
          </span>
          <span className="text-xs text-slate-400">
            {formatDate(e.fetched_at)}
          </span>
        </div>
        <span className="text-slate-400 text-xs">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 border-t border-slate-100">
          <div
            className="prose prose-sm max-w-none mt-3 text-slate-700"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(e.response_markdown) }}
          />
          {e.citations && (() => {
            try {
              const parsed = JSON.parse(e.citations);
              if (Array.isArray(parsed) && parsed.length > 0) {
                return (
                  <div className="mt-3 pt-2 border-t border-slate-100">
                    <p className="text-xs font-medium text-slate-500 mb-1">Sources</p>
                    <div className="flex flex-wrap gap-1">
                      {parsed.map((cite: string, i: number) => (
                        <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{cite}</span>
                      ))}
                    </div>
                  </div>
                );
              }
            } catch { /* not valid JSON */ }
            return null;
          })()}
        </div>
      )}
    </div>
  );
}
