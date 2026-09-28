import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchOutreach, submitFeedback } from '../api/outreach';
import { formatDate } from '../utils/formatters';
import { INDUSTRY_LABELS_SHORT } from '../utils/constants';
import type { OutreachItem } from '../types/outreach';

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

const STRENGTH_LABELS = ['', 'Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong'];

type ViewFilter = 'pending' | 'saved' | 'acted_on' | 'dismissed';

const VIEW_TABS: { key: ViewFilter; label: string }[] = [
  { key: 'pending', label: 'Queue' },
  { key: 'saved', label: 'Saved' },
  { key: 'acted_on', label: 'Acted On' },
  { key: 'dismissed', label: 'Dismissed' },
];

export default function OutreachPage() {
  const [items, setItems] = useState<OutreachItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [view, setView] = useState<ViewFilter>('pending');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState<string | null>(null);

  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const loadOutreach = (show: string) => {
    setLoading(true);
    setError(false);
    fetchOutreach(show)
      .then((res) => setItems(res.items))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadOutreach(view);
  }, [view]);

  const handleFeedback = async (matchId: string, status: string) => {
    setFeedbackLoading(matchId);
    setFeedbackError(null);
    try {
      await submitFeedback(matchId, status);
      setItems((prev) => prev.filter((item) => item.match_id !== matchId));
    } catch {
      setFeedbackError(`Failed to update status for this item. Please try again.`);
    } finally {
      setFeedbackLoading(null);
    }
  };

  return (
    <div className="p-6 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-slate-900">Outreach Queue</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Prioritized outreach recommendations ranked by match strength, signal recency, and relationship warmth
        </p>
      </div>

      {/* View tabs */}
      <div className="flex gap-1 mb-5 border-b border-slate-200">
        {VIEW_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setView(tab.key)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              view === tab.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-slate-500">Loading outreach queue...</p>}
      {error && <p className="text-sm text-red-500">Failed to load outreach data.</p>}
      {feedbackError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{feedbackError}</div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="text-center py-12 border border-dashed border-slate-200 rounded-lg">
          <p className="text-sm text-slate-500">
            {view === 'pending'
              ? 'No pending outreach recommendations. Run ingestion + matching to populate.'
              : `No ${view.replace('_', ' ')} items.`}
          </p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.match_id}
              className={`bg-white border border-slate-200 rounded-lg p-4 transition-shadow hover:shadow-md ${
                item.urgency === 'high'
                  ? 'border-l-4 border-l-red-400'
                  : item.urgency === 'medium'
                  ? 'border-l-4 border-l-amber-400'
                  : 'border-l-4 border-l-slate-300'
              }`}
            >
              {/* Header badges */}
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${URGENCY_STYLES[item.urgency]}`}>
                  {item.urgency} priority
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[item.client_status] || 'bg-slate-100 text-slate-600'}`}>
                  {item.client_status}
                </span>
                {item.match_score != null && (
                  <span className="text-xs text-slate-500">
                    {Math.round(item.match_score * 100)}% match
                  </span>
                )}
                {item.has_active_pipeline && (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    active pipeline
                  </span>
                )}
              </div>

              {/* Signal title */}
              <h3 className="text-sm font-semibold mb-1">
                {item.signal_url ? (
                  <a
                    href={item.signal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-700 hover:text-blue-900 hover:underline"
                  >
                    {item.signal_title}
                  </a>
                ) : (
                  <span className="text-slate-900">{item.signal_title}</span>
                )}
              </h3>

              {/* Company + meta line */}
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                <Link
                  to={`/companies/${item.company_id}`}
                  className="font-medium text-blue-600 hover:underline"
                >
                  {item.company_name}
                </Link>
                {item.industry && (
                  <span className="text-slate-400">
                    {INDUSTRY_LABELS_SHORT[item.industry] || item.industry}
                  </span>
                )}
                <span className="text-slate-300">·</span>
                <span>{item.signal_source}</span>
                {item.signal_published_at && (
                  <>
                    <span className="text-slate-300">·</span>
                    <span>{formatDate(item.signal_published_at)}</span>
                  </>
                )}
              </div>

              {/* Contact */}
              {item.suggested_contact && (
                <p className="text-xs text-slate-600 mb-2">
                  <span className="font-medium">Contact:</span> {item.suggested_contact.name}
                  {item.suggested_contact.title && ` — ${item.suggested_contact.title}`}
                  {item.suggested_contact.relationship_strength != null && (
                    <span className="text-slate-400 ml-1">
                      ({STRENGTH_LABELS[item.suggested_contact.relationship_strength] || 'Unknown'})
                    </span>
                  )}
                </p>
              )}

              {/* PwC engagement summary */}
              {item.pwc_engagement_summary && (
                <p className="text-xs text-violet-600 mb-2">
                  <span className="font-medium">PwC history:</span>{' '}
                  {item.pwc_engagement_summary.slice(0, 150)}
                  {item.pwc_engagement_summary.length > 150 ? '...' : ''}
                </p>
              )}

              {/* Pipeline summary */}
              {item.pipeline_summary && (
                <p className="text-xs text-emerald-600 mb-2">
                  <span className="font-medium">Pipeline:</span>{' '}
                  {item.pipeline_summary}
                </p>
              )}

              {/* Talking points */}
              {item.talking_points && (
                <div className="mb-3">
                  <button
                    onClick={() =>
                      setExpandedId(expandedId === item.match_id ? null : item.match_id)
                    }
                    className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    {expandedId === item.match_id ? 'Hide talking points' : 'Show talking points'}
                  </button>
                  {expandedId === item.match_id && (
                    <div className="mt-2 pl-3 border-l-2 border-blue-200 text-sm text-slate-700 whitespace-pre-line">
                      {item.talking_points}
                    </div>
                  )}
                </div>
              )}

              {/* Action buttons */}
              {view === 'pending' && (
                <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                  <button
                    onClick={() => handleFeedback(item.match_id, 'acted_on')}
                    disabled={feedbackLoading === item.match_id}
                    className="text-xs font-medium px-3 py-1.5 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    Acted On
                  </button>
                  <button
                    onClick={() => handleFeedback(item.match_id, 'saved')}
                    disabled={feedbackLoading === item.match_id}
                    className="text-xs font-medium px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    Save for Later
                  </button>
                  <button
                    onClick={() => handleFeedback(item.match_id, 'dismissed')}
                    disabled={feedbackLoading === item.match_id}
                    className="text-xs font-medium px-3 py-1.5 rounded bg-slate-200 text-slate-600 hover:bg-slate-300 disabled:opacity-50 transition-colors"
                  >
                    Not Relevant
                  </button>
                </div>
              )}

              {/* Status indicator for non-pending views */}
              {view !== 'pending' && (
                <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    item.status === 'acted_on' ? 'bg-green-100 text-green-800' :
                    item.status === 'saved' ? 'bg-blue-100 text-blue-800' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {item.status.replace('_', ' ')}
                  </span>
                  {view === 'saved' && (
                    <button
                      onClick={() => handleFeedback(item.match_id, 'acted_on')}
                      disabled={feedbackLoading === item.match_id}
                      className="text-xs font-medium px-3 py-1.5 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      Mark Acted On
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
