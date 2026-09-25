import { useState } from 'react';
import CompanyList from '../components/companies/CompanyList';
import CompanyForm from '../components/companies/CompanyForm';
import { useCompanies } from '../hooks/useCompanies';
import { useDebouncedValue } from '../hooks/useDebouncedValue';

export default function CompaniesPage() {
  const [industry, setIndustry] = useState('');
  const [clientStatus, setClientStatus] = useState('');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [showForm, setShowForm] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const debouncedSearch = useDebouncedValue(search, 300);

  const { companies, total, loading, error } = useCompanies({
    industry: industry || undefined,
    client_status: clientStatus || undefined,
    search: debouncedSearch || undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    _refresh: refreshKey,
  });

  const handleSaved = () => {
    setShowForm(false);
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
      <div className="flex flex-wrap items-center gap-4 bg-white border border-slate-200 rounded-lg p-4">
        <input
          type="text"
          placeholder="Search companies..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm flex-1 min-w-[180px]"
        />

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Industry</label>
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="">All Industries</option>
            <option value="automotive">Automotive</option>
            <option value="aerospace_defense">Aerospace & Defense</option>
            <option value="energy">Energy</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Status</label>
          <select
            value={clientStatus}
            onChange={(e) => setClientStatus(e.target.value)}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="past">Past</option>
            <option value="target">Target</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600">Sort</label>
          <select
            value={`${sortBy}_${sortOrder}`}
            onChange={(e) => {
              const [field, order] = e.target.value.split('_');
              setSortBy(field);
              setSortOrder(order);
            }}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="name_asc">A — Z</option>
            <option value="name_desc">Z — A</option>
            <option value="industry_asc">Industry</option>
            <option value="client_status_asc">Status</option>
            <option value="created_at_desc">Newest First</option>
          </select>
        </div>

        <div className="text-sm text-slate-500">
          {total} compan{total !== 1 ? 'ies' : 'y'}
        </div>

        <button
          onClick={() => setShowForm(true)}
          className="ml-auto bg-slate-900 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-slate-800"
        >
          + Add Company
        </button>
      </div>

      <CompanyList companies={companies} loading={loading} error={error} />

      {showForm && (
        <CompanyForm onClose={() => setShowForm(false)} onSaved={handleSaved} />
      )}
    </div>
  );
}
