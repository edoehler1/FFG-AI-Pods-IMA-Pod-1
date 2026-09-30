export interface Signal {
  id: string;
  title: string;
  body: string | null;
  url: string | null;
  source_name: string;
  published_at: string | null;
  industry: string | null;
  sub_sector: string | null;
  signal_type: string | null;
  news_category: string | null;
  created_at: string;
}

export interface SignalListResponse {
  signals: Signal[];
  total: number;
  page: number;
  page_size: number;
}

export interface MatchedSignal {
  signal: Signal;
  match_score: number | null;
  match_type: string | null;
  match_reason: string | null;
  talking_points: string | null;
}

export interface CuratedCompanyNews {
  signal: Signal;
  importance_score: number;
  taxonomy_tag: string;
  why_it_matters: string;
  suggested_action: string;
  highlighted: boolean;
}

export interface CuratedIndustryNews {
  signal: Signal;
  category: string;
  importance_score: number;
  partner_relevance: string;
}
