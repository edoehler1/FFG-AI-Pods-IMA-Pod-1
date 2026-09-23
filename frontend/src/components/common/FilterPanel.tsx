const SUB_SECTORS: Record<string, { value: string; label: string }[]> = {
  automotive: [
    { value: 'oem', label: 'OEMs' },
    { value: 'ev', label: 'EV' },
    { value: 'tier1_supplier', label: 'Tier 1 Suppliers' },
    { value: 'aftermarket', label: 'Aftermarket' },
  ],
  aerospace_defense: [
    { value: 'defense_prime', label: 'Defense Primes' },
    { value: 'defense_electronics', label: 'Defense Electronics' },
    { value: 'commercial_aerospace', label: 'Commercial Aerospace' },
    { value: 'space', label: 'Space' },
  ],
  energy: [
    { value: 'upstream', label: 'Upstream' },
    { value: 'midstream', label: 'Midstream' },
    { value: 'downstream', label: 'Downstream' },
    { value: 'renewables', label: 'Renewables' },
    { value: 'utilities', label: 'Utilities' },
    { value: 'nuclear', label: 'Nuclear' },
  ],
};

interface FilterPanelProps {
  industry: string;
  subSector: string;
  signalType: string;
  onIndustryChange: (value: string) => void;
  onSubSectorChange: (value: string) => void;
  onSignalTypeChange: (value: string) => void;
  total: number;
}

export default function FilterPanel({
  industry,
  subSector,
  signalType,
  onIndustryChange,
  onSubSectorChange,
  onSignalTypeChange,
  total,
}: FilterPanelProps) {
  const subSectorOptions = industry ? SUB_SECTORS[industry] || [] : [];

  return (
    <div className="flex flex-wrap items-center gap-4 bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-slate-600">Industry</label>
        <select
          value={industry}
          onChange={(e) => onIndustryChange(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All Industries</option>
          <option value="automotive">Automotive</option>
          <option value="aerospace_defense">Aerospace & Defense</option>
          <option value="energy">Energy</option>
        </select>
      </div>

      {subSectorOptions.length > 0 && (
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Sub-sector</label>
          <select
            value={subSector}
            onChange={(e) => onSubSectorChange(e.target.value)}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="">All</option>
            {subSectorOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      )}

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-slate-600">Type</label>
        <select
          value={signalType}
          onChange={(e) => onSignalTypeChange(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All</option>
          <option value="news">News</option>
          <option value="regulatory">Regulatory</option>
          <option value="earnings">Earnings</option>
          <option value="leadership">Leadership</option>
          <option value="ma">M&A</option>
          <option value="gov_contract">Gov Contract</option>
        </select>
      </div>

      <div className="ml-auto text-sm text-slate-500">
        {total} signal{total !== 1 ? 's' : ''}
      </div>
    </div>
  );
}
