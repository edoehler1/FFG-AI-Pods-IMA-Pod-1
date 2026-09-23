import type { Signal } from '../../types/signal';
import SignalCard from '../signals/SignalCard';

interface CompanyNewsProps {
  signals: Signal[];
}

export default function CompanyNews({ signals }: CompanyNewsProps) {
  if (signals.length === 0) {
    return <p className="text-sm text-slate-500 py-4">No news signals matched to this company yet.</p>;
  }

  return (
    <div className="space-y-3">
      {signals.map((signal) => (
        <SignalCard key={signal.id} signal={signal} />
      ))}
    </div>
  );
}
