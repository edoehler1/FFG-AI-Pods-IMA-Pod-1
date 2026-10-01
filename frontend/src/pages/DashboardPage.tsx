import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchDashboard } from '../api/dashboard';
import { INDUSTRY_LABELS } from '../utils/constants';
import type { DashboardData, BriefingCard } from '../types/dashboard';

function BriefingCardItem({ card }: { card: BriefingCard }) {
  return (
    <Link
      to={`/companies/${card.company_id}`}
      className="block bg-white border border-slate-200 rounded-lg p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-semibold text-slate-900">{card.company_name}</span>
        {card.industry && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
            {INDUSTRY_LABELS[card.industry] || card.industry}
          </span>
        )}
        <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
          {card.client_status}
        </span>
      </div>

      <p className="text-sm text-slate-700 mb-3 leading-relaxed">{card.headline}</p>

      {card.opportunity && (
        <div className="bg-slate-50 rounded p-3 mb-3">
          <p className="text-xs font-medium text-slate-500 mb-0.5">Opportunity</p>
          <p className="text-sm text-slate-700">{card.opportunity}</p>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-600">
            {card.confidence_tier} · {card.confidence_score}/10
          </span>
        </div>
        {card.taxonomy_tag && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
            {card.taxonomy_tag}
          </span>
        )}
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-red-600">Failed to load dashboard.</div>;
  }

  const { briefing_cards, companies_without_briefings } = data;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Portfolio Overview</h1>
        {briefing_cards.length > 0 && (
          <span className="text-xs text-slate-400">
            {briefing_cards.length} companies with briefings
          </span>
        )}
      </div>

      {briefing_cards.length === 0 && companies_without_briefings.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
          <p className="text-slate-500 text-sm">No companies yet. Add companies to get started.</p>
        </div>
      )}

      {briefing_cards.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {briefing_cards.map((card) => (
            <BriefingCardItem key={card.company_id} card={card} />
          ))}
        </div>
      )}

      {companies_without_briefings.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">
            Companies without briefings ({companies_without_briefings.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {companies_without_briefings.map((c) => (
              <Link
                key={c.company_id}
                to={`/companies/${c.company_id}`}
                className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              >
                {c.company_name}
              </Link>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">
            Open a company and go to the Weekly Report tab to generate a briefing.
          </p>
        </div>
      )}
    </div>
  );
}
