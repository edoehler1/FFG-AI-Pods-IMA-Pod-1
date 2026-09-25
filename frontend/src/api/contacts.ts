import client from './client';
import type { Contact } from '../types/contact';

interface ContactCreateData {
  name: string;
  title?: string | null;
  email?: string | null;
  relationship_strength?: number | null;
  last_interaction_date?: string | null;
  notes?: string | null;
}

export async function createContact(companyId: string, data: ContactCreateData): Promise<Contact> {
  const { data: result } = await client.post<Contact>(`/companies/${companyId}/contacts`, data);
  return result;
}
