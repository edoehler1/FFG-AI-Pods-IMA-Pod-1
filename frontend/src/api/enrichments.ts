import client from './client';

export interface Enrichment {
  id: string;
  entity_type: string;
  entity_id: string;
  mcp_source: string;
  query_prompt: string;
  response_markdown: string;
  response_summary: string | null;
  citations: string | null;
  fetched_at: string;
  stale_after: string | null;
}

interface EnrichmentListResponse {
  enrichments: Enrichment[];
  total: number;
}

export async function fetchCompanyEnrichments(companyId: string): Promise<EnrichmentListResponse> {
  const { data } = await client.get<EnrichmentListResponse>(`/enrichments/company/${companyId}`);
  return data;
}

export async function fetchEnrichments(params: {
  entity_type?: string;
  entity_id?: string;
  mcp_source?: string;
}): Promise<EnrichmentListResponse> {
  const searchParams = new URLSearchParams();
  if (params.entity_type) searchParams.set('entity_type', params.entity_type);
  if (params.entity_id) searchParams.set('entity_id', params.entity_id);
  if (params.mcp_source) searchParams.set('mcp_source', params.mcp_source);
  const { data } = await client.get<EnrichmentListResponse>(`/enrichments?${searchParams}`);
  return data;
}
