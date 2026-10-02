import { useEffect, useState } from 'react';
import {
  generateBriefing,
  fetchLatestBriefing,
  type BriefingResponse,
  type BriefingCard,
} from '../../api/reports';
import { fetchCuratedNews } from '../../api/companies';
import type { CuratedCompanyNews } from '../../types/signal';
import { markdownToHtml, formatDate } from '../../utils/formatters';

const TIER_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  'Act Now': { bg: 'bg-red-100', text: 'text-red-800', label: 'Act Now' },
  'Strong Signal': { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Strong Signal' },
  'Monitor': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Monitor' },
  'Noted': { bg: 'bg-slate-100', text: 'text-slate-600', label: 'Noted' },
};

interface CompanyWeeklyReportProps {
  companyId: string;
}

export default function CompanyWeeklyReport({ companyId }: CompanyWeeklyReportProps) {
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [showSignals, setShowSignals] = useState(false);
  const [curatedSignals, setCuratedSignals] = useState<CuratedCompanyNews[]>([]);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchLatestBriefing(companyId),
      fetchCuratedNews(companyId, 7),
    ])
      .then(([briefingData, newsData]) => {
        if (briefingData.full_report) setBriefing(briefingData);
        setCuratedSignals(newsData.curated_news || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [companyId]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const data = await generateBriefing(companyId);
      setBriefing(data);
      setShowDetail(true);
    } catch {
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-500 py-4">Loading briefing...</p>;
  }

  if (!briefing) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-500 text-sm mb-3">No weekly briefing generated yet.</p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-slate-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {generating ? 'Generating Briefing...' : 'Generate Weekly Briefing'}
        </button>
      </div>
    );
  }

  const card = briefing.card;
  const tier = card ? TIER_STYLES[card.confidence_tier] || TIER_STYLES['Noted'] : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div className="text-xs text-slate-400">
          {briefing.week_start} — {briefing.week_end} · {briefing.signal_count} signals
          {briefing.generated_at && <span> · Generated {formatDate(briefing.generated_at, true)}</span>}
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Regenerate Briefing'}
        </button>
      </div>

      {card && (
        <div className={`rounded-lg p-5 mb-4 border ${tier ? `${tier.bg} border-${tier.bg.replace('bg-', '')}` : 'bg-slate-50 border-slate-200'}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                {tier && (
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${tier.bg} ${tier.text}`}>
                    {tier.label} ({card.confidence_score}/10)
                  </span>
                )}
                {card.taxonomy_tag && (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800">
                    {card.taxonomy_tag}
                  </span>
                )}
              </div>
              <p className="text-sm font-semibold text-slate-900 mb-1">{card.headline}</p>
              {card.opportunity && (
                <p className="text-sm text-slate-700 mb-2">{card.opportunity}</p>
              )}
              {card.action && (
                <div className="bg-white/60 rounded p-2 mt-2">
                  <p className="text-xs font-medium text-slate-500 mb-0.5">This week's action</p>
                  <p className="text-sm text-slate-800">{card.action}</p>
                </div>
              )}
            </div>
            {card.lead?.name && (
              <div className="text-right text-xs text-slate-500 shrink-0">
                <p className="font-medium text-slate-700">{card.lead.name}</p>
                {card.lead.role && <p>{card.lead.role}</p>}
                {card.lead.email && (
                  <a href={`mailto:${card.lead.email}`} className="text-blue-500 hover:underline">
                    {card.lead.email}
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <button
        onClick={() => setShowDetail(!showDetail)}
        className="text-xs text-blue-600 hover:text-blue-800 font-medium mb-4"
      >
        {showDetail ? 'Hide Full Report' : 'View Full Report'}
      </button>

      {showDetail && briefing.full_report && (
        <div className="border border-slate-200 rounded-lg p-5 mt-2">
          <div
            className="prose prose-slate prose-sm max-w-none
              prose-headings:text-slate-900 prose-headings:font-semibold
              prose-h1:text-lg prose-h1:mb-3
              prose-h2:text-sm prose-h2:mt-5 prose-h2:mb-2
              prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1
              prose-li:my-0.5 prose-p:my-2
              prose-strong:text-slate-700"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(briefing.full_report) }}
          />
        </div>
      )}

      {curatedSignals.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setShowSignals(!showSignals)}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            {showSignals ? 'Hide' : 'View'} This Week's Signals ({curatedSignals.length})
          </button>

          {showSignals && (
            <div className="mt-3 space-y-2">
              {curatedSignals.map((item) => (
                <div
                  key={item.signal.id}
                  className={`border rounded-lg p-3 ${item.highlighted ? 'border-indigo-300 bg-indigo-50/30' : 'border-slate-200'}`}
                >
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {item.highlighted && (
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-600 text-white">
                        Top Signal
                      </span>
                    )}
                    {item.taxonomy_tag && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800">
                        {item.taxonomy_tag}
                      </span>
                    )}
                    {item.importance_score != null && (
                      <span className="text-xs text-slate-400">{item.importance_score}/100</span>
                    )}
                  </div>
                  <a
                    href={item.signal.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-slate-900 hover:text-blue-600 leading-snug"
                  >
                    {item.signal.title}
                  </a>
                  <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                    <span>{item.signal.source_name}</span>
                    {item.signal.published_at && <span>{formatDate(item.signal.published_at)}</span>}
                  </div>
                  {item.why_it_matters && (
                    <p className="mt-2 text-xs text-slate-600 bg-slate-50 rounded p-2">{item.why_it_matters}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
