import { useEffect, useState } from 'react';
import { fetchSignals, fetchPortfolioSignals, fetchDiscoverySignals } from '../api/signals';
import type { Signal } from '../types/signal';

interface UseSignalsOptions {
  industry?: string;
  sub_sector?: string;
  signal_type?: string;
  news_category?: string;
  source_name?: string;
  exclude_source?: string;
  news_scope?: string;
  page?: number;
  page_size?: number;
  mode?: 'all' | 'portfolio' | 'discovery';
}

export function useSignals(options: UseSignalsOptions = {}) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mode = options.mode || 'all';

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const filters = {
      industry: options.industry,
      sub_sector: options.sub_sector,
      signal_type: options.signal_type,
      news_category: options.news_category,
      source_name: options.source_name,
      exclude_source: options.exclude_source,
      news_scope: options.news_scope,
      page: options.page,
      page_size: options.page_size,
    };

    const fetcher =
      mode === 'portfolio' ? fetchPortfolioSignals :
      mode === 'discovery' ? fetchDiscoverySignals :
      fetchSignals;

    fetcher(filters)
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
  }, [options.industry, options.sub_sector, options.signal_type, options.news_category, options.source_name, options.exclude_source, options.news_scope, options.page, options.page_size, mode]);

  return { signals, total, loading, error };
}
