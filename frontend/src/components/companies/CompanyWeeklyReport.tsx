import { useEffect, useState } from 'react';
import {
  fetchWeeklyReports,
  fetchWeeklyReportDetail,
  generateCompanyWeeklyReport,
  type WeeklyReportSummary,
} from '../../api/reports';
import { markdownToHtml, formatDate } from '../../utils/formatters';

const URGENCY_STYLES: Record<string, string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-blue-100 text-blue-800',
};

interface CompanyWeeklyReportProps {
  companyId: string;
}

export default function CompanyWeeklyReport({ companyId }: CompanyWeeklyReportProps) {
  const [reports, setReports] = useState<WeeklyReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedContent, setExpandedContent] = useState<string | null>(null);
  const [expandedCrossRef, setExpandedCrossRef] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  const loadReports = () => {
    setLoading(true);
    fetchWeeklyReports({ companyId })
      .then((data) => {
        setReports(data.reports);
        if (data.reports.length > 0 && !expandedId) {
          handleExpand(data.reports[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadReports();
  }, [companyId]);

  const handleExpand = async (reportId: string) => {
    if (expandedId === reportId) {
      setExpandedId(null);
      setExpandedContent(null);
      setExpandedCrossRef(null);
      return;
    }
    setExpandedId(reportId);
    setContentLoading(true);
    try {
      const detail = await fetchWeeklyReportDetail(reportId);
      setExpandedContent(detail.content);
      setExpandedCrossRef(detail.financial_cross_ref);
    } catch {
      setExpandedContent('Failed to load report content.');
    } finally {
      setContentLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generateCompanyWeeklyReport(companyId);
      loadReports();
    } catch {
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-500 py-4">Loading weekly reports...</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-900">Weekly Intelligence Reports</h3>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
        >
          {generating ? 'Generating...' : "Generate This Week's Report"}
        </button>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-slate-500 text-sm mb-3">No weekly reports generated yet.</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-slate-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {generating ? 'Generating...' : 'Generate First Report'}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => {
            const isExpanded = expandedId === report.id;
            const lead = report.suggested_lead ? (() => {
              try { return JSON.parse(report.suggested_lead!); } catch { return null; }
            })() : null;

            return (
              <div key={report.id} className="border border-slate-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => handleExpand(report.id)}
                  className="w-full text-left p-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-900">
                        {report.week_start} — {report.week_end}
                      </span>
                      {report.urgency && (
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${URGENCY_STYLES[report.urgency] || 'bg-slate-100 text-slate-600'}`}>
                          {report.urgency}
                        </span>
                      )}
                      {report.has_opportunity ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700">
                          Opportunity
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                          No action
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span>{report.signal_count} signals</span>
                      <span>{isExpanded ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {!isExpanded && report.opportunity_summary && (
                    <p className="text-sm text-slate-600 mt-2 line-clamp-2">{report.opportunity_summary}</p>
                  )}

                  {!isExpanded && lead && (
                    <p className="text-xs text-slate-400 mt-1">
                      Lead: {lead.name}{lead.role ? ` (${lead.role})` : ''}
                    </p>
                  )}
                </button>

                {isExpanded && (
                  <div className="border-t border-slate-100 p-4">
                    {contentLoading ? (
                      <p className="text-sm text-slate-500">Loading report...</p>
                    ) : (
                      <>
                        {expandedCrossRef && (
                          <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
                            <p className="text-xs font-medium text-blue-700 mb-1">Why It Matters</p>
                            <p className="text-sm text-slate-700">{expandedCrossRef}</p>
                          </div>
                        )}
                        {expandedContent && (
                          <div
                            className="prose prose-slate prose-sm max-w-none
                              prose-headings:text-slate-900 prose-headings:font-semibold
                              prose-h2:text-sm prose-h2:mt-5 prose-h2:mb-2
                              prose-li:my-0.5 prose-p:my-2
                              prose-strong:text-slate-700"
                            dangerouslySetInnerHTML={{ __html: markdownToHtml(expandedContent) }}
                          />
                        )}
                      </>
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
