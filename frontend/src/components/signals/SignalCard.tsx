import { useState } from 'react';
import type { Signal } from '../../types/signal';

const TYPE_COLORS: Record<string, string> = {
  news: 'bg-blue-100 text-blue-800',
  regulatory: 'bg-amber-100 text-amber-800',
  earnings: 'bg-green-100 text-green-800',
  leadership: 'bg-purple-100 text-purple-800',
  ma: 'bg-red-100 text-red-800',
  gov_contract: 'bg-indigo-100 text-indigo-800',
};

const INDUSTRY_LABELS: Record<string, string> = {
  automotive: 'Auto',
  aerospace_defense: 'A&D',
  energy: 'Energy',
};

const MATCH_TYPE_COLORS: Record<string, string> = {
  name: 'bg-green-50 text-green-700 border-green-200',
  industry: 'bg-orange-50 text-orange-700 border-orange-200',
  semantic: 'bg-violet-50 text-violet-700 border-violet-200',
};

const MATCH_TYPE_LABELS: Record<string, string> = {
  name: 'name match',
  industry: 'industry match',
  semantic: 'semantic match',
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

interface MatchMeta {
  match_score: number | null;
  match_type: string | null;
  talking_points: string | null;
}

interface SignalCardProps {
  signal: Signal;
  matchMeta?: MatchMeta;
}

export default function SignalCard({ signal, matchMeta }: SignalCardProps) {
  const [showTalkingPoints, setShowTalkingPoints] = useState(false);
  const typeColor = TYPE_COLORS[signal.signal_type || ''] || 'bg-slate-100 text-slate-800';
  const industryLabel = INDUSTRY_LABELS[signal.industry || ''] || signal.industry;

  const matchTypeColor = matchMeta?.match_type
    ? MATCH_TYPE_COLORS[matchMeta.match_type] || 'bg-slate-50 text-slate-600 border-slate-200'
    : '';
  const matchTypeLabel = matchMeta?.match_type
    ? MATCH_TYPE_LABELS[matchMeta.match_type] || matchMeta.match_type
    : '';

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {signal.signal_type && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeColor}`}>
                {signal.signal_type.replace('_', ' ')}
              </span>
            )}
            {industryLabel && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {industryLabel}
              </span>
            )}
            {signal.sub_sector && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-50 text-slate-500 border border-slate-200">
                {signal.sub_sector.replace(/_/g, ' ')}
              </span>
            )}
            {matchMeta?.match_type && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${matchTypeColor}`}>
                {matchTypeLabel}
              </span>
            )}
            {matchMeta?.match_score != null && (
              <span className="text-xs text-slate-400">
                {Math.round(matchMeta.match_score * 100)}% relevance
              </span>
            )}
          </div>

          <h3 className="text-sm font-semibold text-slate-900 leading-snug mb-1">
            {signal.url ? (
              <a
                href={signal.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 hover:underline"
              >
                {signal.title}
              </a>
            ) : (
              signal.title
            )}
          </h3>

          {signal.body && (
            <p className="text-sm text-slate-600 line-clamp-2 mb-2">{signal.body}</p>
          )}

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>{signal.source_name}</span>
            {signal.published_at && <span>{formatDate(signal.published_at)}</span>}
          </div>

          {matchMeta?.talking_points && (
            <div className="mt-3">
              <button
                onClick={() => setShowTalkingPoints(!showTalkingPoints)}
                className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
              >
                {showTalkingPoints ? 'Hide talking points' : 'Show talking points'}
              </button>
              {showTalkingPoints && (
                <div className="mt-2 pl-3 border-l-2 border-blue-200 text-sm text-slate-700 whitespace-pre-line">
                  {matchMeta.talking_points}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
