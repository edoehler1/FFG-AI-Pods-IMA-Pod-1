import { useCallback, useEffect, useState } from 'react';
import { fetchCompany } from '../api/companies';
import type { CompanyDetail } from '../types/company';

export function useCompany(id: string | undefined) {
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCompany(id)
      .then((data) => {
        if (!cancelled) setCompany(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to fetch company');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id, refreshKey]);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  return { company, loading, error, refresh };
}
