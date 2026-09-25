import client from './client';
import type { Engagement } from '../types/engagement';

interface EngagementCreateData {
  date?: string | null;
  capabilities_pitched?: string | null;
  project_type?: string | null;
  outcome?: string | null;
  team?: string | null;
  notes?: string | null;
}

export async function createEngagement(companyId: string, data: EngagementCreateData): Promise<Engagement> {
  const { data: result } = await client.post<Engagement>(`/companies/${companyId}/engagements`, data);
  return result;
}
