import { useEffect, useState } from 'react';
import {
  generateReport,
  generateWeeklyReports,
  fetchWeeklyReports,
  fetchWeeklyReportDetail,
  type ReportResponse,
  type WeeklyReportSummary,
  type GenerateWeeklyResponse,
} from '../api/reports';

import { markdownToHtml } from '../utils/formatters';

type Tab = 'weekly' | 'brief';

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>('weekly');

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
      <div className="flex gap-1 border-b border-slate-200">
        <button
          onClick={() => setTab('weekly')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === 'weekly'
              ? 'border-slate-900 text-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Weekly Reports
        </button>
        <button
          onClick={() => setTab('brief')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === 'brief'
              ? 'border-slate-900 text-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Generate Brief
        </button>
      </div>

      {tab === 'weekly' && <WeeklyReportsTab />}
      {tab === 'brief' && <GenerateBriefTab />}
    </div>
  );
}

function WeeklyReportsTab() {
  const [reports, setReports] = useState<WeeklyReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateWeeklyResponse | null>(null);
  const [filter, setFilter] = useState<'all' | 'opportunities'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedContent, setExpandedContent] = useState<Record<string, string>>({});
  const [expandedCrossRef, setExpandedCrossRef] = useState<Record<string, string>>({});
  const [contentLoading, setContentLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadReports = async () => {
    setLoading(true);
    try {
      const hasOpp = filter === 'opportunities' ? true : undefined;
      const data = await fetchWeeklyReports(hasOpp);
      setReports(data.reports);
    } catch {
      setError('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadReports(); }, [filter]);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenResult(null);
    setError(null);
    try {
      const result = await generateWeeklyReports(7);
      setGenResult(result);
      await loadReports();
    } catch (err: any) {
      setError(err.message || 'Failed to generate reports');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === 'all'
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('opportunities')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === 'opportunities'
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            With Opportunities Only
          </button>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-slate-900 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate Weekly Reports'}
        </button>
      </div>

      {genResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
          {genResult.reports_created} of {genResult.total_companies} companies had signals — {genResult.opportunities_found} opportunities found.
          {genResult.reports_created === 0 && (
            <span className="block mt-1 text-green-700">No companies had recent signals to report on. Try running ingestion first.</span>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          No weekly reports yet. Click "Generate Weekly Reports" to create them.
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => {
            const isExpanded = expandedId === r.id;
            const hasStructured = !!(r.urgency || r.opportunity_summary || r.suggested_lead);
            const lead = r.suggested_lead ? (() => { try { return JSON.parse(r.suggested_lead); } catch { return null; } })() : null;

            const urgencyColors: Record<string, string> = {
              high: 'bg-red-100 text-red-800',
              medium: 'bg-amber-100 text-amber-800',
              low: 'bg-blue-100 text-blue-800',
            };

            return (
              <div key={r.id} className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => {
                    if (isExpanded) {
                      setExpandedId(null);
                    } else {
                      setExpandedId(r.id);
                      if (!expandedContent[r.id]) {
                        setContentLoading(r.id);
                        fetchWeeklyReportDetail(r.id)
                          .then((detail) => {
                            setExpandedContent((prev) => ({ ...prev, [r.id]: detail.content }));
                            if (detail.financial_cross_ref) {
                              setExpandedCrossRef((prev) => ({ ...prev, [r.id]: detail.financial_cross_ref! }));
                            }
                          })
                          .catch(() => setExpandedContent((prev) => ({ ...prev, [r.id]: 'Failed to load report content.' })))
                          .finally(() => setContentLoading(null));
                      }
                    }
                  }}
                  className="w-full px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-900">{r.company_name}</span>
                      {hasStructured && r.urgency ? (
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${urgencyColors[r.urgency] || 'bg-slate-100 text-slate-600'}`}>
                          {r.urgency.toUpperCase()}
                        </span>
                      ) : r.has_opportunity ? (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-800">
                          Opportunity identified
                        </span>
                      ) : (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          No action needed
                        </span>
                      )}
                      <span className="text-xs text-slate-400">
                        {r.signal_count} signal{r.signal_count !== 1 ? 's' : ''} analyzed
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-400">
                        {r.week_start} — {r.week_end}
                      </span>
                      <span className="text-slate-400 text-sm">{isExpanded ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {hasStructured && !isExpanded && (
                    <div className="mt-2 space-y-1">
                      {r.opportunity_summary && (
                        <p className="text-sm text-slate-600 line-clamp-2">{r.opportunity_summary}</p>
                      )}
                      <div className="flex items-center gap-3">
                        {lead && (
                          <span className="text-xs text-slate-500">
                            Lead: <span className="font-medium text-slate-700">{lead.name}</span>
                            {lead.role ? ` (${lead.role}${lead.office ? ', ' + lead.office : ''})` : ''}
                          </span>
                        )}
                        {r.top_signal_title && (
                          <span className="text-xs text-slate-400 truncate max-w-xs">
                            Signal: {r.top_signal_title}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </button>
                {isExpanded && (
                  <div className="border-t border-slate-100 px-4 py-4">
                    {contentLoading === r.id ? (
                      <p className="text-sm text-slate-500">Loading report...</p>
                    ) : expandedContent[r.id] ? (
                      <>
                      {expandedCrossRef[r.id] && (
                        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <p className="text-xs font-semibold text-blue-800 mb-1">Why It Matters</p>
                          <p className="text-sm text-blue-900">{expandedCrossRef[r.id]}</p>
                        </div>
                      )}
                      <div
                        className="prose prose-slate prose-sm max-w-none
                          prose-headings:text-slate-900 prose-headings:font-semibold
                          prose-h1:text-lg prose-h1:mb-2
                          prose-h2:text-sm prose-h2:mt-4 prose-h2:mb-1
                          prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1
                          prose-li:my-0.5 prose-p:my-1.5
                          prose-strong:text-slate-700
                          prose-em:text-slate-500"
                        dangerouslySetInnerHTML={{ __html: markdownToHtml(expandedContent[r.id]) }}
                      />
                      </>
                    ) : (
                      <p className="text-sm text-slate-500">No content available.</p>
                    )}
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

function GenerateBriefTab() {
  const [industry, setIndustry] = useState('');
  const [clientStatus, setClientStatus] = useState('');
  const [days, setDays] = useState(7);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateReport({
        industry: industry || undefined,
        client_status: clientStatus || undefined,
        days,
      });
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Generate Weekly Brief</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Industry</label>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
            >
              <option value="">All Industries</option>
              <option value="automotive">Automotive</option>
              <option value="aerospace_defense">Aerospace & Defense</option>
              <option value="energy">Energy</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Client Status</label>
            <select
              value={clientStatus}
              onChange={(e) => setClientStatus(e.target.value)}
              className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
            >
              <option value="">All</option>
              <option value="active">Active Clients</option>
              <option value="past">Past Clients</option>
              <option value="target">Targets</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Period</label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="bg-slate-900 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Generating...' : 'Generate Brief'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error}</div>
      )}

      {report && (
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-center gap-4 mb-4 pb-4 border-b border-slate-100 text-sm text-slate-500">
            <span>{report.period_start && report.period_end ? `${report.period_start} — ${report.period_end}` : `Last ${report.period_days} days`}</span>
            <span>{report.company_count} companies</span>
            <span>{report.total_matched_signals} matched signals</span>
          </div>
          <div
            className="prose prose-slate prose-sm max-w-none
              prose-headings:text-slate-900 prose-headings:font-semibold
              prose-h1:text-xl prose-h1:mb-3
              prose-h2:text-base prose-h2:mt-6 prose-h2:mb-2
              prose-h3:text-sm prose-h3:mt-4 prose-h3:mb-1
              prose-li:my-0.5 prose-p:my-2
              prose-strong:text-slate-700
              prose-em:text-slate-500"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(report.markdown) }}
          />
        </div>
      )}

      {!report && !loading && (
        <div className="text-center py-12 text-slate-500">
          Select filters and click "Generate Brief" to create a personalized signal report.
        </div>
      )}
    </div>
  );
}
