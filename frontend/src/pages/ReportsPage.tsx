import { useEffect, useState } from 'react';
import { fetchCompanies } from '../api/companies';
import { generatePortfolioReport, type PortfolioReportResponse } from '../api/reports';
import { markdownToHtml } from '../utils/formatters';
import { INDUSTRY_LABELS } from '../utils/constants';
import type { Company } from '../types/company';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  past: 'bg-slate-100 text-slate-600',
  target: 'bg-orange-100 text-orange-800',
};

export default function ReportsPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const [industryFilter, setIndustryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const [days, setDays] = useState(7);
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCompanies({ page_size: 100 })
      .then((data) => setCompanies(data.companies))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = companies.filter((c) => {
    if (industryFilter && c.industry !== industryFilter) return false;
    if (statusFilter && c.client_status !== statusFilter) return false;
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const toggleCompany = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelected(new Set(filtered.map((c) => c.id)));
  const selectNone = () => setSelected(new Set());

  const handleGenerate = async () => {
    if (selected.size === 0) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generatePortfolioReport(Array.from(selected), days);
      setReport(result);
    } catch (err: any) {
      setError(err.message || 'Failed to generate portfolio report');
    } finally {
      setGenerating(false);
    }
  };

  const industries = [...new Set(companies.map((c) => c.industry).filter(Boolean))].sort();

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-xl font-semibold text-slate-900 mb-6">Portfolio Reports</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-900">Select Companies</h2>
              <span className="text-xs text-slate-400">
                {selected.size} of {filtered.length} selected
              </span>
            </div>

            <input
              type="text"
              placeholder="Search companies..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded px-3 py-1.5 mb-2 focus:outline-none focus:ring-1 focus:ring-slate-400"
            />

            <div className="flex gap-2 mb-2">
              <select
                value={industryFilter}
                onChange={(e) => setIndustryFilter(e.target.value)}
                className="text-xs border border-slate-200 rounded px-2 py-1 flex-1"
              >
                <option value="">All Industries</option>
                {industries.map((ind) => (
                  <option key={ind} value={ind}>{INDUSTRY_LABELS[ind!] || ind}</option>
                ))}
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-slate-200 rounded px-2 py-1 flex-1"
              >
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="past">Past</option>
                <option value="target">Target</option>
              </select>
            </div>

            <div className="flex gap-2 mb-3">
              <button onClick={selectAll} className="text-xs text-blue-600 hover:text-blue-800">Select all</button>
              <span className="text-xs text-slate-300">|</span>
              <button onClick={selectNone} className="text-xs text-blue-600 hover:text-blue-800">Clear</button>
            </div>

            {loading ? (
              <p className="text-xs text-slate-400 py-4">Loading companies...</p>
            ) : (
              <div className="max-h-96 overflow-y-auto space-y-1">
                {filtered.map((company) => (
                  <label
                    key={company.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(company.id)}
                      onChange={() => toggleCompany(company.id)}
                      className="rounded border-slate-300"
                    />
                    <span className="text-sm text-slate-700 flex-1">{company.name}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${STATUS_COLORS[company.client_status] || 'bg-slate-100 text-slate-500'}`}>
                      {company.client_status}
                    </span>
                  </label>
                ))}
                {filtered.length === 0 && (
                  <p className="text-xs text-slate-400 py-2">No companies match filters.</p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-900">Portfolio Briefing</h2>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1">
                  {[7, 14, 30].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      className={`text-xs px-2.5 py-1 rounded ${
                        days === d
                          ? 'bg-slate-900 text-white'
                          : 'text-slate-500 hover:bg-slate-100'
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleGenerate}
                  disabled={generating || selected.size === 0}
                  className="bg-slate-900 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
                >
                  {generating ? 'Generating...' : `Generate Report (${selected.size} companies)`}
                </button>
              </div>
            </div>

            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

            {!report && !generating && (
              <div className="text-center py-12">
                <p className="text-slate-400 text-sm">
                  Select companies from the left panel, then generate a portfolio briefing.
                </p>
              </div>
            )}

            {generating && (
              <div className="text-center py-12">
                <p className="text-slate-500 text-sm">Generating portfolio briefing for {selected.size} companies...</p>
              </div>
            )}

            {report && !generating && (
              <div>
                <div className="flex items-center gap-3 mb-4 text-xs text-slate-400">
                  <span>{report.company_count} companies</span>
                  <span>{report.industries.join(', ')}</span>
                </div>
                <div
                  className="prose prose-slate prose-sm max-w-none
                    prose-headings:text-slate-900 prose-headings:font-semibold
                    prose-h1:text-lg prose-h1:mb-3
                    prose-h2:text-sm prose-h2:mt-5 prose-h2:mb-2
                    prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1
                    prose-li:my-0.5 prose-p:my-2
                    prose-strong:text-slate-700"
                  dangerouslySetInnerHTML={{ __html: markdownToHtml(report.markdown) }}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
