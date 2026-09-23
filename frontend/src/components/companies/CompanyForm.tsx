import { useState, useEffect } from 'react';
import { createCompany, updateCompany } from '../../api/companies';
import type { Company } from '../../types/company';

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

interface CompanyFormProps {
  company?: Company | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function CompanyForm({ company, onClose, onSaved }: CompanyFormProps) {
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [subSector, setSubSector] = useState('');
  const [size, setSize] = useState('');
  const [geography, setGeography] = useState('');
  const [clientStatus, setClientStatus] = useState('target');
  const [website, setWebsite] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (company) {
      setName(company.name);
      setIndustry(company.industry || '');
      setSubSector(company.sub_sector || '');
      setSize(company.size || '');
      setGeography(company.geography || '');
      setClientStatus(company.client_status);
      setWebsite(company.website || '');
      setNotes(company.notes || '');
    }
  }, [company]);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Company name is required');
      return;
    }

    setSaving(true);
    setError(null);

    const data = {
      name: name.trim(),
      industry: industry || null,
      sub_sector: subSector || null,
      size: size || null,
      geography: geography || null,
      client_status: clientStatus,
      website: website || null,
      notes: notes || null,
    };

    try {
      if (company) {
        await updateCompany(company.id, data);
      } else {
        await createCompany(data);
      }
      onSaved();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleIndustryChange = (value: string) => {
    setIndustry(value);
    setSubSector('');
  };

  const subSectorOptions = industry ? SUB_SECTORS[industry] || [] : [];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            {company ? 'Edit Company' : 'Add Company'}
          </h2>
        </div>

        <div className="px-6 py-4 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Company Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
              placeholder="e.g. Ford Motor Company"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Industry</label>
              <select
                value={industry}
                onChange={(e) => handleIndustryChange(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white"
              >
                <option value="">Select...</option>
                <option value="automotive">Automotive</option>
                <option value="aerospace_defense">Aerospace & Defense</option>
                <option value="energy">Energy</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sub-sector</label>
              <select
                value={subSector}
                onChange={(e) => setSubSector(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white"
                disabled={subSectorOptions.length === 0}
              >
                <option value="">{subSectorOptions.length === 0 ? 'Select industry first' : 'Select...'}</option>
                {subSectorOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Size</label>
              <select
                value={size}
                onChange={(e) => setSize(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white"
              >
                <option value="">Select...</option>
                <option value="small">Small</option>
                <option value="mid">Mid</option>
                <option value="large">Large</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Client Status</label>
              <select
                value={clientStatus}
                onChange={(e) => setClientStatus(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white"
              >
                <option value="active">Active</option>
                <option value="past">Past</option>
                <option value="target">Target</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Geography</label>
            <input
              type="text"
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
              placeholder="e.g. United States"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Website</label>
            <input
              type="text"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
              placeholder="https://..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm h-20 resize-none"
              placeholder="Any relevant context..."
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded hover:bg-slate-800 disabled:opacity-50"
          >
            {saving ? 'Saving...' : company ? 'Update' : 'Add Company'}
          </button>
        </div>
      </div>
    </div>
  );
}
