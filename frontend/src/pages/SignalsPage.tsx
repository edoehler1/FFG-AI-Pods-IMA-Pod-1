import { useState } from 'react';
import FilterPanel from '../components/common/FilterPanel';
import SignalList from '../components/signals/SignalList';
import FilingsView from '../components/signals/FilingsView';
import { useSignals } from '../hooks/useSignals';

type ViewMode = 'all' | 'portfolio' | 'discovery';
type Tab = 'news' | 'filings';

const VIEW_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: 'all', label: 'All Signals' },
  { value: 'portfolio', label: 'My Portfolio' },
  { value: 'discovery', label: 'Discovery' },
];

const CATEGORY_OPTIONS = [
  { key: '', label: 'All' },
  { key: 'regulatory', label: 'Regulatory' },
  { key: 'macro', label: 'Macro' },
  { key: 'competitors', label: 'Competitors' },
  { key: 'trends', label: 'Trends' },
];

export default function SignalsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [tab, setTab] = useState<Tab>('news');
  const [industry, setIndustry] = useState('');
  const [subSector, setSubSector] = useState('');
  const [signalType, setSignalType] = useState('');
  const [newsCategory, setNewsCategory] = useState('');

  const newsSignals = useSignals({
    industry: industry || undefined,
    sub_sector: subSector || undefined,
    signal_type: signalType || undefined,
    news_category: newsCategory || undefined,
    exclude_source: 'sec_edgar',
    mode: viewMode,
  });

  const filingSignals = useSignals({
    industry: industry || undefined,
    sub_sector: subSector || undefined,
    source_name: 'sec_edgar',
    page_size: 400,
    mode: viewMode,
  });

  const handleIndustryChange = (value: string) => {
    setIndustry(value);
    setSubSector('');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
      <div className="flex gap-2">
        {VIEW_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setViewMode(opt.value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              viewMode === opt.value
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        <button
          onClick={() => setTab('news')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === 'news'
              ? 'border-slate-900 text-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          News & Regulatory
        </button>
        <button
          onClick={() => setTab('filings')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === 'filings'
              ? 'border-slate-900 text-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          SEC Filings
        </button>
      </div>

      {tab === 'news' && (
        <>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setNewsCategory(cat.key)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  newsCategory === cat.key
                    ? 'bg-slate-900 text-white'
                    : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <FilterPanel
            industry={industry}
            subSector={subSector}
            signalType={signalType}
            onIndustryChange={handleIndustryChange}
            onSubSectorChange={setSubSector}
            onSignalTypeChange={setSignalType}
            total={newsSignals.total}
          />
          <SignalList signals={newsSignals.signals} loading={newsSignals.loading} error={newsSignals.error} />
        </>
      )}

      {tab === 'filings' && (
        <FilingsView
          signals={filingSignals.signals}
          loading={filingSignals.loading}
          error={filingSignals.error}
        />
      )}
    </div>
  );
}
