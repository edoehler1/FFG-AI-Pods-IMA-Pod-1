import type { MatchedSignal } from '../../types/signal';
import SignalCard from '../signals/SignalCard';

interface CompanyNewsProps {
  matches: MatchedSignal[];
}

export default function CompanyNews({ matches }: CompanyNewsProps) {
  if (matches.length === 0) {
    return <p className="text-sm text-slate-500 py-4">No news signals matched to this company yet.</p>;
  }

  return (
    <div className="space-y-3">
      {matches.map((m) => (
        <SignalCard
          key={m.signal.id}
          signal={m.signal}
          matchMeta={{
            match_score: m.match_score,
            match_type: m.match_type,
            talking_points: m.talking_points,
          }}
        />
      ))}
    </div>
  );
}
