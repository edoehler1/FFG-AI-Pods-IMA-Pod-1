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
  period_start?: string;
  period_end?: string;
}

export async function generateReport(options: ReportOptions = {}): Promise<ReportResponse> {
  const params = new URLSearchParams();
  if (options.industry) params.set('industry', options.industry);
  if (options.client_status) params.set('client_status', options.client_status);
  if (options.days) params.set('days', String(options.days));

  const { data } = await client.post<ReportResponse>(`/reports/generate?${params}`);
  return data;
}

export interface WeeklyReportSummary {
  id: string;
  company_id: string;
  company_name: string;
  week_start: string;
  week_end: string;
  signal_count: number;
  has_opportunity: boolean;
  urgency: string | null;
  opportunity_summary: string | null;
  suggested_lead: string | null;
  top_signal_title: string | null;
  generated_at: string;
}

export interface WeeklyReportFull extends WeeklyReportSummary {
  content: string;
  financial_cross_ref: string | null;
}

export interface WeeklyReportsResponse {
  reports: WeeklyReportSummary[];
  total: number;
}

export interface GenerateWeeklyResponse {
  total_companies: number;
  reports_created: number;
  opportunities_found: number;
  results: { company: string; status: string; has_opportunity?: boolean }[];
}

export async function generateWeeklyReports(daysBack: number = 7): Promise<GenerateWeeklyResponse> {
  const { data } = await client.post<GenerateWeeklyResponse>(`/reports/weekly/generate?days_back=${daysBack}`);
  return data;
}

export async function fetchWeeklyReports(hasOpportunity?: boolean): Promise<WeeklyReportsResponse> {
  const params = new URLSearchParams();
  if (hasOpportunity !== undefined) params.set('has_opportunity', String(hasOpportunity));
  params.set('limit', '50');
  const { data } = await client.get<WeeklyReportsResponse>(`/reports/weekly/summary?${params}`);
  return data;
}

export async function fetchWeeklyReportDetail(reportId: string): Promise<WeeklyReportFull> {
  const { data } = await client.get<WeeklyReportFull>(`/reports/weekly/${reportId}`);
  return data;
}
