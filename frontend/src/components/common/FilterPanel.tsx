interface FilterPanelProps {
  industry: string;
  signalType: string;
  onIndustryChange: (value: string) => void;
  onSignalTypeChange: (value: string) => void;
  total: number;
}

export default function FilterPanel({
  industry,
  signalType,
  onIndustryChange,
  onSignalTypeChange,
  total,
}: FilterPanelProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-slate-600">Industry</label>
        <select
          value={industry}
          onChange={(e) => onIndustryChange(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All</option>
          <option value="automotive">Automotive</option>
          <option value="aerospace_defense">Aerospace & Defense</option>
        </select>
      </div>

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
