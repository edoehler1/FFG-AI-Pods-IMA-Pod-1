import client from './client';
import type { SignalListResponse } from '../types/signal';

interface SignalFilters {
  industry?: string;
  sub_sector?: string;
  signal_type?: string;
  source_name?: string;
  exclude_source?: string;
  page?: number;
  page_size?: number;
}

export async function fetchSignals(filters: SignalFilters = {}): Promise<SignalListResponse> {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.sub_sector) params.set('sub_sector', filters.sub_sector);
  if (filters.signal_type) params.set('signal_type', filters.signal_type);
  if (filters.source_name) params.set('source_name', filters.source_name);
  if (filters.exclude_source) params.set('exclude_source', filters.exclude_source);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));

  const { data } = await client.get<SignalListResponse>(`/signals?${params}`);
  return data;
}

function buildParams(filters: SignalFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.sub_sector) params.set('sub_sector', filters.sub_sector);
  if (filters.signal_type) params.set('signal_type', filters.signal_type);
  if (filters.source_name) params.set('source_name', filters.source_name);
  if (filters.exclude_source) params.set('exclude_source', filters.exclude_source);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  return params;
}

export async function fetchPortfolioSignals(filters: SignalFilters = {}): Promise<SignalListResponse> {
  const params = buildParams(filters);
  const { data } = await client.get<SignalListResponse>(`/signals/portfolio?${params}`);
  return data;
}

export async function fetchDiscoverySignals(filters: SignalFilters = {}): Promise<SignalListResponse> {
  const params = buildParams(filters);
  const { data } = await client.get<SignalListResponse>(`/signals/discovery?${params}`);
  return data;
}
