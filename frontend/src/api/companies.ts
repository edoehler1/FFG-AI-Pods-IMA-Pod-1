import client from './client';
import type { Company, CompanyDetail, CompanyListResponse } from '../types/company';

interface CompanyFilters {
  industry?: string;
  sub_sector?: string;
  client_status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export async function fetchCompanies(filters: CompanyFilters = {}): Promise<CompanyListResponse> {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.sub_sector) params.set('sub_sector', filters.sub_sector);
  if (filters.client_status) params.set('client_status', filters.client_status);
  if (filters.search) params.set('search', filters.search);
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
