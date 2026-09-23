import type { Signal } from '../../types/signal';
import SignalCard from '../signals/SignalCard';

interface IndustryNewsProps {
  signals: Signal[];
  industry: string | null;
  subSector: string | null;
}

const INDUSTRY_LABELS: Record<string, string> = {
  automotive: 'Automotive',
  aerospace_defense: 'Aerospace & Defense',
  energy: 'Energy',
};

export default function IndustryNews({ signals, industry, subSector }: IndustryNewsProps) {
  const label = industry ? (INDUSTRY_LABELS[industry] || industry) : 'General';
  const subLabel = subSector ? ` / ${subSector.replace(/_/g, ' ')}` : '';

  return (
    <div>
      <p className="text-xs text-slate-400 mb-3">
        Signals from the {label}{subLabel} sector (not company-specific)
      </p>
      {signals.length === 0 ? (
        <p className="text-sm text-slate-500 py-4">No industry signals found.</p>
      ) : (
        <div className="space-y-3">
          {signals.map((signal) => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      )}
    </div>
  );
}
