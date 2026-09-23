import client from './client';

interface UploadCompaniesResult {
  created: number;
  skipped: number;
  total_in_file: number;
}

interface UploadContactsResult {
  created: number;
  skipped: number;
  company_not_found: number;
  total_in_file: number;
}

export async function uploadCompanies(file: File): Promise<UploadCompaniesResult> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post<UploadCompaniesResult>('/upload/companies', formData);
  return data;
}

export async function uploadContacts(file: File): Promise<UploadContactsResult> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post<UploadContactsResult>('/upload/contacts', formData);
  return data;
}
