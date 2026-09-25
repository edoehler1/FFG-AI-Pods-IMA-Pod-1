import type { Signal } from '../../types/signal';

const TYPE_LABELS: Record<string, string> = {
  regulatory: 'Regulatory',
  earnings: 'Earnings',
  leadership: 'Leadership',
  ma: 'M&A',
  gov_contract: 'Gov Contract',
  news: 'News',
};

const TYPE_COLORS: Record<string, string> = {
  regulatory: 'text-amber-700',
  earnings: 'text-green-700',
  leadership: 'text-purple-700',
  ma: 'text-red-700',
  gov_contract: 'text-indigo-700',
  news: 'text-blue-700',
};

const TYPE_PRIORITY = ['regulatory', 'ma', 'leadership', 'earnings', 'gov_contract', 'news'];

interface SignalSummaryBadgeProps {
  signals: Signal[];
  maxTypes?: number;
}

export default function SignalSummaryBadge({ signals, maxTypes = 3 }: SignalSummaryBadgeProps) {
  if (signals.length === 0) return null;

  const byType: Record<string, number> = {};
  for (const s of signals) {
    const t = s.signal_type || 'news';
    byType[t] = (byType[t] || 0) + 1;
  }

  const sorted = TYPE_PRIORITY
    .filter((t) => byType[t])
    .map((t) => ({ type: t, count: byType[t] }));

  const shown = sorted.slice(0, maxTypes);
  const remaining = signals.length - shown.reduce((sum, s) => sum + s.count, 0);

  return (
    <span className="text-xs text-slate-500">
      {shown.map((s, i) => (
        <span key={s.type}>
          {i > 0 && ' · '}
          <span className={TYPE_COLORS[s.type] || 'text-slate-600'}>
            {s.count} {TYPE_LABELS[s.type] || s.type}
          </span>
        </span>
      ))}
      {remaining > 0 && <span> · {remaining} other</span>}
    </span>
  );
}

interface MatchSummaryBadgeProps {
  matchCount: number;
  highRelevanceCount: number;
}

export function MatchSummaryBadge({ matchCount, highRelevanceCount }: MatchSummaryBadgeProps) {
  if (matchCount === 0) return null;

  return (
    <span className="text-xs text-slate-500">
      {matchCount} matched
      {highRelevanceCount > 0 && (
        <span className="text-green-700"> · {highRelevanceCount} high relevance</span>
      )}
    </span>
  );
}
