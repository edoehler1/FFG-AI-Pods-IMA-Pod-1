import { useState } from 'react';
import FilterPanel from '../components/common/FilterPanel';
import SignalList from '../components/signals/SignalList';
import { useSignals } from '../hooks/useSignals';

export default function SignalsPage() {
  const [industry, setIndustry] = useState('');
  const [subSector, setSubSector] = useState('');
  const [signalType, setSignalType] = useState('');

  const { signals, total, loading, error } = useSignals({
    industry: industry || undefined,
    sub_sector: subSector || undefined,
    signal_type: signalType || undefined,
  });

  const handleIndustryChange = (value: string) => {
    setIndustry(value);
    setSubSector('');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
      <FilterPanel
        industry={industry}
        subSector={subSector}
        signalType={signalType}
        onIndustryChange={handleIndustryChange}
        onSubSectorChange={setSubSector}
        onSignalTypeChange={setSignalType}
        total={total}
      />
      <SignalList signals={signals} loading={loading} error={error} />
    </div>
  );
}
