export interface Engagement {
  id: string;
  company_id: string;
  date: string | null;
  capabilities_pitched: string | null;
  project_type: string | null;
  outcome: string | null;
  team: string | null;
  notes: string | null;
  created_at: string;
}
