import { useState } from 'react';
import { generateReport, type ReportResponse } from '../api/reports';

export default function ReportsPage() {
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
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
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
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {report && (
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-center gap-4 mb-4 pb-4 border-b border-slate-100 text-sm text-slate-500">
            <span>{report.company_count} companies</span>
            <span>{report.total_matched_signals} matched signals</span>
            <span>Last {report.period_days} days</span>
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
