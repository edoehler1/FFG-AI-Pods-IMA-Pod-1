import type { Signal } from '../../types/signal';
import SignalCard from './SignalCard';

interface SignalListProps {
  signals: Signal[];
  loading: boolean;
  error: string | null;
}

export default function SignalList({ signals, loading, error }: SignalListProps) {
  if (loading) {
    return (
      <div className="text-center py-12 text-slate-500">
        Loading signals...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 font-medium">Failed to load signals</p>
        <p className="text-sm text-slate-500 mt-1">{error}</p>
        <p className="text-sm text-slate-400 mt-2">
          Make sure the backend is running: <code className="bg-slate-100 px-1 rounded">cd backend && uvicorn app.main:app --reload</code>
        </p>
      </div>
    );
  }

  if (signals.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        No signals found. Try adjusting your filters or run the ingestion script.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {signals.map((signal) => (
        <SignalCard key={signal.id} signal={signal} />
      ))}
    </div>
  );
}
