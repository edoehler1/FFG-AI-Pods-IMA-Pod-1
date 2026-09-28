import client from './client';
import type { OutreachResponse } from '../types/outreach';

export async function fetchOutreach(show: string, limit: number = 50): Promise<OutreachResponse> {
  const { data } = await client.get<OutreachResponse>('/outreach', { params: { show, limit } });
  return data;
}

export async function submitFeedback(matchId: string, status: string): Promise<void> {
  await client.post(`/outreach/${matchId}/feedback`, { status });
}
