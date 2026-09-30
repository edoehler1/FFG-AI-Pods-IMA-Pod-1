export interface BriefingCard {
  company_id: string;
  company_name: string;
  industry: string | null;
  client_status: string;
  headline: string;
  confidence_score: number;
  confidence_tier: string;
  opportunity: string;
  taxonomy_tag: string;
  action: string;
  week_start: string;
  week_end: string;
  generated_at: string | null;
}

export interface CompanyStub {
  company_id: string;
  company_name: string;
  industry: string | null;
  client_status: string;
}

export interface DashboardData {
  briefing_cards: BriefingCard[];
  companies_without_briefings: CompanyStub[];
  generated_at: string;
}
