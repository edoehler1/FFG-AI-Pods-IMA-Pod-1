import type { Company } from '../../types/company';
import CompanyCard from './CompanyCard';

interface CompanyListProps {
  companies: Company[];
  loading: boolean;
  error: string | null;
}

export default function CompanyList({ companies, loading, error }: CompanyListProps) {
  if (loading) {
    return <div className="text-center py-12 text-slate-500">Loading companies...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 font-medium">Failed to load companies</p>
        <p className="text-sm text-slate-500 mt-1">{error}</p>
      </div>
    );
  }

  if (companies.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        No companies found. Upload a CSV or add companies manually.
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {companies.map((company) => (
        <CompanyCard key={company.id} company={company} />
      ))}
    </div>
  );
}
