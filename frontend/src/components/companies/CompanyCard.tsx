import { Link } from 'react-router-dom';
import type { Company } from '../../types/company';
import { INDUSTRY_LABELS_SHORT, SIZE_LABELS } from '../../utils/constants';

const INDUSTRY_COLORS: Record<string, string> = {
  automotive: 'bg-blue-100 text-blue-800',
  aerospace_defense: 'bg-indigo-100 text-indigo-800',
  energy: 'bg-amber-100 text-amber-800',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  past: 'bg-slate-100 text-slate-600',
  target: 'bg-orange-100 text-orange-800',
};

interface CompanyCardProps {
  company: Company;
}

export default function CompanyCard({ company }: CompanyCardProps) {
  const industryColor = INDUSTRY_COLORS[company.industry || ''] || 'bg-slate-100 text-slate-600';
  const statusColor = STATUS_COLORS[company.client_status] || 'bg-slate-100 text-slate-600';
  const industryLabel = INDUSTRY_LABELS_SHORT[company.industry || ''] || company.industry;

  return (
    <Link
      to={`/companies/${company.id}`}
      className="block bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-900">{company.name}</h3>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            {industryLabel && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${industryColor}`}>
                {industryLabel}
              </span>
            )}
            {company.sub_sector && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {company.sub_sector.replace('_', ' ')}
              </span>
            )}
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColor}`}>
              {company.client_status}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            {company.geography && <span>{company.geography}</span>}
            {company.size && <span>{SIZE_LABELS[company.size] || company.size}</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}
