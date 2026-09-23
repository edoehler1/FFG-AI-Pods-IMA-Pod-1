import { useEffect, useState } from 'react';
import { fetchSignals } from '../api/signals';
import type { Signal } from '../types/signal';

interface UseSignalsOptions {
  industry?: string;
  sub_sector?: string;
  signal_type?: string;
  source_name?: string;
  exclude_source?: string;
  page?: number;
  page_size?: number;
}

export function useSignals(options: UseSignalsOptions = {}) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSignals({
      industry: options.industry,
      sub_sector: options.sub_sector,
      signal_type: options.signal_type,
      source_name: options.source_name,
      exclude_source: options.exclude_source,
      page: options.page,
      page_size: options.page_size,
    })
      .then((data) => {
        if (!cancelled) {
          setSignals(data.signals);
          setTotal(data.total);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Failed to fetch signals');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [options.industry, options.sub_sector, options.signal_type, options.source_name, options.exclude_source, options.page, options.page_size]);

  return { signals, total, loading, error };
}
