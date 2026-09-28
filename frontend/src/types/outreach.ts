export interface OutreachItem {
  outreach_id: string | null;
  match_id: string;
  status: string;
  composite_score: number;
  urgency: 'high' | 'medium' | 'low';
  signal_id: string;
  signal_title: string;
  signal_source: string;
  signal_published_at: string | null;
  signal_type: string | null;
  company_id: string;
  company_name: string;
  client_status: string;
  industry: string | null;
  match_score: number | null;
  match_type: string | null;
  talking_points: string | null;
  suggested_contact: {
    name: string;
    title: string | null;
    relationship_strength: number | null;
  } | null;
  pwc_engagement_summary: string | null;
  has_active_pipeline: boolean;
  pipeline_summary: string | null;
}

export interface OutreachResponse {
  items: OutreachItem[];
  count: number;
  lookback_days: number;
}
