import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import { formatDate } from '../utils/formatters';
import { INDUSTRY_LABELS_SHORT } from '../utils/constants';

interface TopAction {
  signal_id: string;
  signal_title: string;
  signal_source: string;
  signal_published_at: string | null;
  signal_type: string | null;
  company_id: string;
  company_name: string;
  client_status: string;
  industry: string | null;
  match_score: number | null;
  match_type: string | null;
  talking_points: string | null;
  suggested_contact: {
    name: string;
    title: string | null;
    relationship_strength: number | null;
  } | null;
  pwc_engagement_summary: string | null;
  has_active_pipeline: boolean;
  urgency: 'high' | 'medium' | 'low';
}

interface PortfolioCompany {
  company_id: string;
  company_name: string;
  client_status: string;
  industry: string | null;
  signal_count: number;
  has_opportunity: boolean;
  last_report_date: string | null;
  last_interaction_date: string | null;
}

interface PipelineSummary {
  available: boolean;
  companies_with_data: number;
  companies?: {
    company_id: string;
    company_name: string;
    summary: string;
    fetched_at: string | null;
  }[];
}

interface DashboardData {
  top_actions: TopAction[];
  portfolio_pulse: PortfolioCompany[];
  pipeline_summary: PipelineSummary;
  generated_at: string;
  lookback_days: number;
}

const URGENCY_STYLES: Record<string, string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-slate-100 text-slate-600',
};

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  target: 'bg-blue-100 text-blue-800',
  past: 'bg-slate-100 text-slate-600',
};

const MATCH_TYPE_LABELS: Record<string, string> = {
  name: 'name match',
  industry: 'industry match',
  semantic: 'semantic match',
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expandedAction, setExpandedAction] = useState<string | null>(null);

  useEffect(() => {
    client
      .get<DashboardData>('/dashboard')
      .then((res) => setData(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <p className="text-sm text-slate-500">Loading dashboard...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-500">Failed to load dashboard. Is the backend running?</p>
      </div>
    );
  }

  const { top_actions, portfolio_pulse, pipeline_summary } = data;

  const activeCompanies = portfolio_pulse.filter((c) => c.client_status === 'active');
  const targetCompanies = portfolio_pulse.filter((c) => c.client_status === 'target');
  const pastCompanies = portfolio_pulse.filter((c) => c.client_status === 'past');

  return (
    <div className="p-6 space-y-8 max-w-6xl">
      {/* Top Actions */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Top Actions Today</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Highest-priority outreach opportunities from the past {data.lookback_days} days
            </p>
          </div>
        </div>

        {top_actions.length === 0 ? (
          <div className="text-center py-8 border border-dashed border-slate-200 rounded-lg">
            <p className="text-sm text-slate-500">No high-priority matches in the past {data.lookback_days} days.</p>
            <p className="text-xs text-slate-400 mt-1">Run ingestion + matching to populate.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {top_actions.map((action) => (
              <div
                key={action.signal_id + action.company_id}
                className={`bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow ${
                  action.urgency === 'high'
                    ? 'border-l-4 border-l-red-400'
                    : action.urgency === 'medium'
                    ? 'border-l-4 border-l-amber-400'
                    : 'border-l-4 border-l-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${URGENCY_STYLES[action.urgency]}`}>
                        {action.urgency} priority
                      </span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[action.client_status] || 'bg-slate-100 text-slate-600'}`}>
                        {action.client_status}
                      </span>
                      {action.match_type && (
                        <span className="text-xs text-slate-500">
                          {MATCH_TYPE_LABELS[action.match_type] || action.match_type}
                          {action.match_score != null && ` · ${Math.round(action.match_score * 100)}%`}
                        </span>
                      )}
                      {action.has_active_pipeline && (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          active pipeline
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-semibold text-slate-900 mb-1">{action.signal_title}</h3>

                    <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                      <Link
                        to={`/companies/${action.company_id}`}
                        className="font-medium text-blue-600 hover:underline"
                      >
                        {action.company_name}
                      </Link>
                      {action.industry && (
                        <span className="text-slate-400">
                          {INDUSTRY_LABELS_SHORT[action.industry] || action.industry}
                        </span>
                      )}
                      <span className="text-slate-300">·</span>
                      <span>{action.signal_source}</span>
                      {action.signal_published_at && (
                        <>
                          <span className="text-slate-300">·</span>
                          <span>{formatDate(action.signal_published_at)}</span>
                        </>
                      )}
                    </div>

                    {action.suggested_contact && (
                      <p className="text-xs text-slate-600 mb-1">
                        <span className="font-medium">Contact:</span> {action.suggested_contact.name}
                        {action.suggested_contact.title && ` — ${action.suggested_contact.title}`}
                      </p>
                    )}

                    {action.talking_points && (
                      <div className="mt-2">
                        <button
                          onClick={() =>
                            setExpandedAction(
                              expandedAction === action.signal_id + action.company_id
                                ? null
                                : action.signal_id + action.company_id
                            )
                          }
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          {expandedAction === action.signal_id + action.company_id
                            ? 'Hide talking points'
                            : 'Show talking points'}
                        </button>
                        {expandedAction === action.signal_id + action.company_id && (
                          <div className="mt-2 pl-3 border-l-2 border-blue-200 text-sm text-slate-700 whitespace-pre-line">
                            {action.talking_points}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Portfolio Pulse */}
      <section>
        <h2 className="text-lg font-semibold text-slate-900 mb-1">Portfolio Pulse</h2>
        <p className="text-xs text-slate-400 mb-4">Signal activity and opportunity flags per company</p>

        {portfolio_pulse.length === 0 ? (
          <p className="text-sm text-slate-500">No companies in portfolio.</p>
        ) : (
          <div className="space-y-4">
            {[
              { label: 'Active Clients', companies: activeCompanies },
              { label: 'Targets', companies: targetCompanies },
              { label: 'Past Clients', companies: pastCompanies },
            ]
              .filter((g) => g.companies.length > 0)
              .map((group) => (
                <div key={group.label}>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                    {group.label} ({group.companies.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {group.companies.map((company) => (
                      <Link
                        key={company.company_id}
                        to={`/companies/${company.company_id}`}
                        className="block bg-white border border-slate-200 rounded-lg p-3 hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-slate-900 truncate">
                            {company.company_name}
                          </span>
                          {company.has_opportunity && (
                            <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 shrink-0 ml-2">
                              opportunity
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          {company.industry && (
                            <span>{INDUSTRY_LABELS_SHORT[company.industry] || company.industry}</span>
                          )}
                          <span>
                            {company.signal_count} signal{company.signal_count !== 1 ? 's' : ''} this week
                          </span>
                        </div>
                        {company.last_interaction_date && (
                          <p className="text-xs text-slate-400 mt-1">
                            Last interaction: {company.last_interaction_date}
                          </p>
                        )}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        )}
      </section>

      {/* Pipeline Summary */}
      {pipeline_summary.available && (
        <section>
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Pipeline Summary</h2>
          <p className="text-xs text-slate-400 mb-4">
            Salesforce data for {pipeline_summary.companies_with_data} compan{pipeline_summary.companies_with_data === 1 ? 'y' : 'ies'}
          </p>

          <div className="space-y-3">
            {pipeline_summary.companies?.map((co) => (
              <div
                key={co.company_id}
                className="bg-white border border-slate-200 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <Link
                    to={`/companies/${co.company_id}`}
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    {co.company_name}
                  </Link>
                  {co.fetched_at && (
                    <span className="text-xs text-slate-400">
                      Updated {formatDate(co.fetched_at)}
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-600">{co.summary}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
