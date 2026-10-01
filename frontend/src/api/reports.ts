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
  opportunities_found: number;
  results: { company: string; status: string; has_opportunity?: boolean }[];
}

export async function generateWeeklyReports(daysBack: number = 7): Promise<GenerateWeeklyResponse> {
  const { data } = await client.post<GenerateWeeklyResponse>(`/reports/weekly/generate?days_back=${daysBack}`);
  return data;
}

export async function fetchWeeklyReports(options: {
  companyId?: string;
  hasOpportunity?: boolean;
  urgency?: string;
  limit?: number;
} = {}): Promise<WeeklyReportsResponse> {
  const params = new URLSearchParams();
  if (options.companyId) params.set('company_id', options.companyId);
  if (options.hasOpportunity !== undefined) params.set('has_opportunity', String(options.hasOpportunity));
  if (options.urgency) params.set('urgency', options.urgency);
  params.set('limit', String(options.limit || 50));
  const { data } = await client.get<WeeklyReportsResponse>(`/reports/weekly/summary?${params}`);
  return data;
}

export async function generateCompanyWeeklyReport(companyId: string, daysBack: number = 7): Promise<GenerateWeeklyResponse> {
  const { data } = await client.post<GenerateWeeklyResponse>(
    `/reports/weekly/generate?days_back=${daysBack}`,
    { company_ids: [companyId] }
  );
  return data;
}

export async function fetchWeeklyReportDetail(reportId: string): Promise<WeeklyReportFull> {
  const { data } = await client.get<WeeklyReportFull>(`/reports/weekly/${reportId}`);
  return data;
}

export interface BriefingCard {
  headline: string;
  confidence_score: number;
  confidence_tier: string;
  opportunity: string;
  taxonomy_tag: string;
  lead: { name?: string; role?: string; email?: string };
  action: string;
}

export interface BriefingResponse {
  card: BriefingCard | null;
  full_report: string | null;
  company_id: string;
  company_name: string;
  week_start: string;
  week_end: string;
  signal_count: number;
  generated_at: string;
  report_id: string | null;
}

export async function generateBriefing(companyId: string, daysBack: number = 7): Promise<BriefingResponse> {
  const { data } = await client.post<BriefingResponse>('/reports/briefing/generate', {
    company_id: companyId,
    days_back: daysBack,
  });
  return data;
}

export async function fetchLatestBriefing(companyId: string): Promise<BriefingResponse> {
  const { data } = await client.get<BriefingResponse>(`/reports/briefing/${companyId}`);
  return data;
}

export interface PortfolioCard {
  company_name: string;
  company_id: string;
  industry: string | null;
  client_status: string;
  headline: string;
  confidence_score: number;
  confidence_tier: string;
  opportunity: string;
  taxonomy_tag: string;
  action: string;
  week_start: string;
  week_end: string;
  signal_count: number;
}

export interface PortfolioReportResponse {
  cards: PortfolioCard[];
  themes: string[];
  actions: string[];
  company_count: number;
  industries: string[];
}

export interface SavedPortfolioSummary {
  id: string;
  company_count: number;
  industries: string[];
  company_names: string[];
  days_back: number;
  generated_at: string;
}

export async function fetchSavedPortfolios(limit: number = 20): Promise<{ reports: SavedPortfolioSummary[] }> {
  const { data } = await client.get<{ reports: SavedPortfolioSummary[] }>(`/reports/portfolio/saved?limit=${limit}`);
  return data;
}

export async function fetchSavedPortfolio(reportId: string): Promise<PortfolioReportResponse> {
  const { data } = await client.get<PortfolioReportResponse>(`/reports/portfolio/saved/${reportId}`);
  return data;
}

export async function savePortfolioReport(reportData: PortfolioReportResponse): Promise<{ report_id: string }> {
  const { data } = await client.post<{ report_id: string }>('/reports/portfolio/save', reportData);
  return data;
}

export async function generatePortfolioReport(
  companyIds: string[],
  daysBack: number = 7,
): Promise<PortfolioReportResponse> {
  const { data } = await client.post<PortfolioReportResponse>('/reports/portfolio/generate', {
    company_ids: companyIds,
    days_back: daysBack,
  });
  return data;
}
