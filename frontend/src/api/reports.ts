import client from './client';

interface ReportOptions {
  industry?: string;
  client_status?: string;
  days?: number;
}

export interface ReportResponse {
  markdown: string;
  company_count: number;
  total_matched_signals: number;
  period_days: number;
}

export async function generateReport(options: ReportOptions = {}): Promise<ReportResponse> {
  const params = new URLSearchParams();
  if (options.industry) params.set('industry', options.industry);
  if (options.client_status) params.set('client_status', options.client_status);
  if (options.days) params.set('days', String(options.days));

  const { data } = await client.post<ReportResponse>(`/reports/generate?${params}`);
  return data;
}
