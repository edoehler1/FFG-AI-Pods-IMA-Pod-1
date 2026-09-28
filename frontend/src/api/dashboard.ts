import client from './client';
import type { DashboardData } from '../types/dashboard';

export async function fetchDashboard(): Promise<DashboardData> {
  const { data } = await client.get<DashboardData>('/dashboard');
  return data;
}
