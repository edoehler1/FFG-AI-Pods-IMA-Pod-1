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
  importance_score: number | null;
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
