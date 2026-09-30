import client from './client';
import type { Company, CompanyDetail, CompanyListResponse } from '../types/company';

interface CompanyFilters {
  industry?: string;
  sub_sector?: string;
  client_status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}

export async function fetchCompanies(filters: CompanyFilters = {}): Promise<CompanyListResponse> {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.sub_sector) params.set('sub_sector', filters.sub_sector);
  if (filters.client_status) params.set('client_status', filters.client_status);
  if (filters.search) params.set('search', filters.search);
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));

  const { data } = await client.get<CompanyListResponse>(`/companies?${params}`);
  return data;
}

export async function fetchCompany(id: string): Promise<CompanyDetail> {
  const { data } = await client.get<CompanyDetail>(`/companies/${id}`);
  return data;
}

export async function createCompany(companyData: Partial<Company>): Promise<Company> {
  const { data } = await client.post<Company>('/companies', companyData);
  return data;
}

export async function updateCompany(id: string, companyData: Partial<Company>): Promise<Company> {
  const { data } = await client.put<Company>(`/companies/${id}`, companyData);
  return data;
}

export async function deleteCompany(id: string): Promise<void> {
  await client.delete(`/companies/${id}`);
}

interface CompanyIntelligence {
  filings: import('../types/signal').Signal[];
  company_news: import('../types/signal').Signal[];
  industry_news: import('../types/signal').Signal[];
}

interface CompanyAnalysisResponse {
  narrative: string | null;
  signal_count?: number;
  filing_count?: number;
  generated_at: string | null;
}

export async function fetchCompanyIntelligence(id: string): Promise<CompanyIntelligence> {
  const { data } = await client.get<CompanyIntelligence>(`/companies/${id}/intelligence`);
  return data;
}

export async function fetchCompanyAnalysis(id: string): Promise<CompanyAnalysisResponse> {
  const { data } = await client.get<CompanyAnalysisResponse>(`/companies/${id}/analysis`);
  return data;
}

export async function triggerCompanyAnalysis(id: string): Promise<CompanyAnalysisResponse> {
  const { data } = await client.post<CompanyAnalysisResponse>(`/companies/${id}/analyze`);
  return data;
}

interface FinancialAnalysisResponse {
  content: string | null;
  key_metrics: string | null;
  peer_comparison: string | null;
  fiscal_year: string | null;
  generated_at: string | null;
}

export async function fetchFinancialAnalysis(id: string): Promise<FinancialAnalysisResponse> {
  const { data } = await client.get<FinancialAnalysisResponse>(`/companies/${id}/financial-analysis`);
  return data;
}

export async function triggerFinancialAnalysis(id: string): Promise<FinancialAnalysisResponse> {
  const { data } = await client.post<FinancialAnalysisResponse>(`/companies/${id}/financial-analysis/generate`);
  return data;
}

interface AnnualBaselineResponse {
  timeline_content: string | null;
  key_themes: string | null;
  signal_count: number | null;
  fiscal_year: string | null;
  generated_at: string | null;
}

export async function fetchAnnualBaseline(id: string): Promise<AnnualBaselineResponse> {
  const { data } = await client.get<AnnualBaselineResponse>(`/companies/${id}/annual-baseline`);
  return data;
}

export async function triggerBaselineGeneration(id: string): Promise<AnnualBaselineResponse> {
  const { data } = await client.post<AnnualBaselineResponse>(`/companies/${id}/annual-baseline/generate`);
  return data;
}

interface CompanyProfileResponse {
  profile_narrative: string | null;
  financial_summary: string | null;
  news_summary: string | null;
  generated_at: string | null;
}

export async function fetchCompanyProfile(id: string): Promise<CompanyProfileResponse> {
  const { data } = await client.get<CompanyProfileResponse>(`/companies/${id}/profile`);
  return data;
}

export async function triggerProfileGeneration(id: string): Promise<CompanyProfileResponse> {
  const { data } = await client.post<CompanyProfileResponse>(`/companies/${id}/profile/generate`);
  return data;
}

export async function fetchCompanyMatches(id: string): Promise<import('../types/signal').MatchedSignal[]> {
  const { data } = await client.get<import('../types/signal').MatchedSignal[]>(`/companies/${id}/matches`);
  return data;
}
