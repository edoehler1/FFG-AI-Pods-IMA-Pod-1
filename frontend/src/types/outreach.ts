import type { SuggestedContact, PipelineData } from './dashboard';

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
  signal_url: string | null;
  company_id: string;
  company_name: string;
  client_status: string;
  industry: string | null;
  match_score: number | null;
  match_type: string | null;
  talking_points: string | null;
  suggested_contact: SuggestedContact | null;
  has_grp: boolean;
  has_account_team: boolean;
  has_active_pipeline: boolean;
  pipeline: PipelineData | null;
}

export interface OutreachResponse {
  items: OutreachItem[];
  count: number;
  lookback_days: number;
}
