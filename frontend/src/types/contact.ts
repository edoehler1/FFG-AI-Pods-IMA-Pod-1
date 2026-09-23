export interface Contact {
  id: string;
  company_id: string;
  name: string;
  title: string | null;
  email: string | null;
  relationship_strength: number | null;
  last_interaction_date: string | null;
  notes: string | null;
  created_at: string;
}
