import { useEffect, useState } from 'react';
import { fetchCompanies } from '../api/companies';
import type { Company } from '../types/company';

interface UseCompaniesOptions {
  industry?: string;
  sub_sector?: string;
  client_status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  _refresh?: number;
}

export function useCompanies(options: UseCompaniesOptions = {}) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCompanies({
      industry: options.industry,
      sub_sector: options.sub_sector,
      client_status: options.client_status,
      search: options.search,
      sort_by: options.sort_by,
      sort_order: options.sort_order,
      page: options.page,
    })
      .then((data) => {
        if (!cancelled) {
          setCompanies(data.companies);
          setTotal(data.total);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Failed to fetch companies');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [options.industry, options.sub_sector, options.client_status, options.search, options.sort_by, options.sort_order, options.page, options._refresh]);

  return { companies, total, loading, error };
}
