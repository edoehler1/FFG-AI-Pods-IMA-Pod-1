import { useEffect, useState } from 'react';
import client from '../api/client';

interface TaxonomyGroup {
  name: string;
  path: string;
  capabilities: string[];
  sectors: string[];
}

type TaxonomyData = Record<string, TaxonomyGroup>;

const SECTOR_LABELS: Record<string, string> = {
  automotive: 'Auto',
  aerospace_defense: 'A&D',
  energy: 'Energy',
};

const SECTOR_COLORS: Record<string, string> = {
  automotive: 'bg-blue-100 text-blue-700',
  aerospace_defense: 'bg-amber-100 text-amber-700',
  energy: 'bg-emerald-100 text-emerald-700',
};

export default function TaxonomyPage() {
  const [data, setData] = useState<TaxonomyData | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    client
      .get<TaxonomyData>('/taxonomy')
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><p className="text-sm text-slate-500">Loading taxonomy...</p></div>;
  if (!data) return <div className="p-6"><p className="text-sm text-red-500">Failed to load taxonomy.</p></div>;

  const VISIBLE_GROUPS = ['enterprise_and_functional_strategy', 'operations_strategy', 'corporate_technology_strategy', 'deals'];
  const groups = Object.entries(data).filter(([key]) => VISIBLE_GROUPS.includes(key));
  const totalCapabilities = groups.reduce((sum, [_, g]) => sum + g.capabilities.length, 0);

  return (
    <div className="p-6 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-slate-900">Strategy& Capability Taxonomy</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Derived from PwC engagement data — {groups.length} practice areas, {totalCapabilities} capabilities
        </p>
        <p className="text-[11px] text-slate-400 mt-1">
          Source: People Connector sub-practice hierarchy + 130+ engagement service lines across 21 companies
        </p>
      </div>

      {/* Taxonomy tree */}
      <div className="space-y-4">
        {groups.map(([key, group]) => (
          <div key={key} className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="mb-2">
              <h2 className="text-sm font-semibold text-slate-900">{group.name}</h2>
              <p className="text-[10px] text-slate-400 font-mono mt-0.5">{group.path}</p>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {group.capabilities.map((cap) => (
                <span
                  key={cap}
                  className="text-xs px-2.5 py-1 rounded-md bg-slate-50 text-slate-700 border border-slate-200"
                >
                  {cap}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
