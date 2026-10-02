import client from './client';
import type { SignalListResponse } from '../types/signal';

interface SignalFilters {
  industry?: string;
  sub_sector?: string;
  signal_type?: string;
  news_category?: string;
  source_name?: string;
  exclude_source?: string;
  news_scope?: string;
  page?: number;
  page_size?: number;
}

function buildParams(filters: SignalFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.sub_sector) params.set('sub_sector', filters.sub_sector);
  if (filters.signal_type) params.set('signal_type', filters.signal_type);
  if (filters.news_category) params.set('news_category', filters.news_category);
  if (filters.source_name) params.set('source_name', filters.source_name);
  if (filters.exclude_source) params.set('exclude_source', filters.exclude_source);
  if (filters.news_scope) params.set('news_scope', filters.news_scope);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  return params;
}

export async function fetchSignals(filters: SignalFilters = {}): Promise<SignalListResponse> {
  const params = buildParams(filters);
  const { data } = await client.get<SignalListResponse>(`/signals?${params}`);
  return data;
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
