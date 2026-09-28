export interface SuggestedContact {
  name: string;
  role: string | null;
  office: string | null;
  source: 'people_connector' | 'manual' | 'unknown';
}

export interface PipelineData {
  total_value: number | null;
  opportunity_count: number;
  nearest_close: string | null;
  top_opportunity: {
    name: string;
    value: number | null;
    stage: string | null;
    close_date: string | null;
    owner: string | null;
  } | null;
}

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
  suggested_contact: SuggestedContact | null;
  has_grp: boolean;
  has_account_team: boolean;
  has_active_pipeline: boolean;
  pipeline: PipelineData | null;
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
    total_pipeline_value: number | null;
    opportunity_count: number;
    opportunities: { name: string; value: number | null; stage: string | null; close_date: string | null; owner: string | null }[];
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
