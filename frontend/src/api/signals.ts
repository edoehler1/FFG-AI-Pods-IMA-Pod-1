import client from './client';
import type { SignalListResponse } from '../types/signal';

interface SignalFilters {
  industry?: string;
  signal_type?: string;
  page?: number;
  page_size?: number;
}

export async function fetchSignals(filters: SignalFilters = {}): Promise<SignalListResponse> {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.signal_type) params.set('signal_type', filters.signal_type);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));

  const { data } = await client.get<SignalListResponse>(`/signals?${params}`);
  return data;
}
