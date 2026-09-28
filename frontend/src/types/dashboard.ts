export interface TopAction {
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
  urgency: 'high' | 'medium' | 'low';
}

export interface PortfolioCompany {
  company_id: string;
  company_name: string;
  client_status: string;
  industry: string | null;
  signal_count: number;
  has_opportunity: boolean;
  last_report_date: string | null;
  last_interaction_date: string | null;
}

export interface PipelineSummary {
  available: boolean;
  companies_with_data: number;
  companies?: {
    company_id: string;
    company_name: string;
    summary: string;
    fetched_at: string | null;
  }[];
}

export interface DashboardData {
  top_actions: TopAction[];
  portfolio_pulse: PortfolioCompany[];
  pipeline_summary: PipelineSummary;
  generated_at: string;
  lookback_days: number;
}
