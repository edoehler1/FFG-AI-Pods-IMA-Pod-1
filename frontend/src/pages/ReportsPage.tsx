import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCompanies } from '../api/companies';
import {
  generatePortfolioReport,
  savePortfolioReport,
  fetchSavedPortfolios,
  fetchSavedPortfolio,
  type PortfolioReportResponse,
  type PortfolioCard,
  type SavedPortfolioSummary,
} from '../api/reports';
import { INDUSTRY_LABELS } from '../utils/constants';
import type { Company } from '../types/company';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  past: 'bg-slate-100 text-slate-600',
  target: 'bg-orange-100 text-orange-800',
};

const TIER_STYLES: Record<string, { border: string; bg: string; badge: string; text: string }> = {
  'Act Now': { border: 'border-red-300', bg: 'bg-red-50', badge: 'bg-red-600 text-white', text: 'text-red-800' },
  'Strong Signal': { border: 'border-amber-300', bg: 'bg-amber-50', badge: 'bg-amber-500 text-white', text: 'text-amber-800' },
  'Monitor': { border: 'border-blue-200', bg: 'bg-blue-50', badge: 'bg-blue-500 text-white', text: 'text-blue-800' },
  'Noted': { border: 'border-slate-200', bg: 'bg-slate-50', badge: 'bg-slate-400 text-white', text: 'text-slate-600' },
};

function CompanyCard({ card }: { card: PortfolioCard }) {
  const tier = TIER_STYLES[card.confidence_tier] || TIER_STYLES['Noted'];
  const hasContent = card.confidence_score > 0;

  return (
    <div className={`border ${tier.border} ${tier.bg} rounded-lg p-4`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <Link
            to={`/companies/${card.company_id}`}
            className="text-sm font-semibold text-slate-900 hover:text-blue-600"
          >
            {card.company_name}
          </Link>
          {card.industry && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
              {INDUSTRY_LABELS[card.industry] || card.industry}
            </span>
          )}
        </div>
        {hasContent && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full shrink-0 ${tier.badge}`}>
            {card.confidence_tier} ({card.confidence_score}/10)
          </span>
        )}
      </div>

      {hasContent ? (
        <>
          <p className="text-sm text-slate-800 mb-2">{card.headline}</p>

          {card.opportunity && (
            <div className="bg-white/60 rounded p-2.5 mb-2">
              <p className="text-xs font-medium text-slate-500 mb-0.5">Opportunity</p>
              <p className="text-sm text-slate-700">{card.opportunity}</p>
            </div>
          )}

          <div className="flex items-center justify-between">
            {card.taxonomy_tag && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800">
                {card.taxonomy_tag}
              </span>
            )}
            {card.action && (
              <p className="text-xs text-slate-500 italic flex-1 ml-3 text-right">{card.action}</p>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-slate-400">{card.headline}</p>
      )}
    </div>
  );
}

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

  const [savedReports, setSavedReports] = useState<SavedPortfolioSummary[]>([]);

  const loadSaved = () => {
    fetchSavedPortfolios()
      .then((data) => setSavedReports(data.reports))
      .catch(() => {});
  };

  useEffect(() => {
    fetchCompanies({ page_size: 100 })
      .then((data) => setCompanies(data.companies))
      .catch(() => {})
      .finally(() => setLoading(false));
    loadSaved();
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
      loadSaved();
    } catch (err: any) {
      setError(err.message || 'Failed to generate portfolio report');
    } finally {
      setGenerating(false);
    }
  };

  const handleLoadSaved = async (reportId: string) => {
    try {
      const data = await fetchSavedPortfolio(reportId);
      setReport(data);
    } catch {
    }
  };

  const industries = [...new Set(companies.map((c) => c.industry).filter(Boolean))].sort();

  const tiers = ['Act Now', 'Strong Signal', 'Monitor', 'Noted'];
  const groupedCards: Record<string, PortfolioCard[]> = {};
  if (report) {
    for (const card of report.cards) {
      const tier = card.confidence_tier || 'Noted';
      if (!groupedCards[tier]) groupedCards[tier] = [];
      groupedCards[tier].push(card);
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-xl font-semibold text-slate-900 mb-6">Portfolio Reports</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-900">Select Companies</h2>
              <span className="text-xs text-slate-400">
                {selected.size} of {filtered.length}
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
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-2 mb-3">
                {[7, 14, 30].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDays(d)}
                    className={`text-xs px-2.5 py-1 rounded ${
                      days === d ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-100'
                    }`}
                  >
                    {d}d
                  </button>
                ))}
              </div>
              <button
                onClick={handleGenerate}
                disabled={generating || selected.size === 0}
                className="w-full bg-slate-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
              >
                {generating ? 'Generating...' : `Generate Briefing (${selected.size})`}
              </button>
            </div>
          </div>

          {savedReports.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-lg p-4 mt-4">
              <h2 className="text-sm font-semibold text-slate-900 mb-3">Saved Reports</h2>
              <div className="space-y-2">
                {savedReports.map((saved) => (
                  <button
                    key={saved.id}
                    onClick={() => handleLoadSaved(saved.id)}
                    className="w-full text-left px-3 py-2 rounded border border-slate-100 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-700">
                        {saved.company_names.join(', ')}
                      </span>
                      <span className="text-xs text-slate-400">{saved.days_back}d</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {saved.generated_at ? new Date(saved.generated_at + 'Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/Chicago' }) : ''}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

          {!report && !generating && (
            <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
              <p className="text-slate-400 text-sm">
                Select companies and generate a portfolio briefing.
              </p>
            </div>
          )}

          {generating && (
            <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
              <p className="text-slate-500 text-sm">Generating portfolio briefing for {selected.size} companies...</p>
            </div>
          )}

          {report && !generating && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>{report.company_count} companies</span>
                  <span>{report.industries.map(i => INDUSTRY_LABELS[i] || i).join(', ')}</span>
                </div>
                <button
                  onClick={async () => {
                    await savePortfolioReport(report);
                    loadSaved();
                  }}
                  className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50"
                >
                  Save Report
                </button>
              </div>

              {tiers.map((tier) => {
                const tierCards = groupedCards[tier];
                if (!tierCards || tierCards.length === 0) return null;
                return (
                  <div key={tier}>
                    <h3 className={`text-xs font-semibold uppercase tracking-wide mb-2 ${TIER_STYLES[tier]?.text || 'text-slate-500'}`}>
                      {tier}
                    </h3>
                    <div className="space-y-3">
                      {tierCards.map((card) => (
                        <CompanyCard key={card.company_id} card={card} />
                      ))}
                    </div>
                  </div>
                );
              })}

              {report.themes.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-lg p-4 mt-4">
                  <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wide mb-2">Cross-Portfolio Themes</h3>
                  <ul className="space-y-1.5">
                    {report.themes.map((theme, i) => (
                      <li key={i} className="text-sm text-slate-700">• {theme}</li>
                    ))}
                  </ul>
                </div>
              )}

              {report.actions.length > 0 && (
                <div className="bg-slate-900 text-white rounded-lg p-4 mt-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide mb-2 text-slate-300">This Week's Actions</h3>
                  <ul className="space-y-1.5">
                    {report.actions.map((action, i) => (
                      <li key={i} className="text-sm">• {action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
