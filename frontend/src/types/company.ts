import type { Contact } from './contact';
import type { Engagement } from './engagement';
import type { Signal } from './signal';

export interface Company {
  id: string;
  name: string;
  industry: string | null;
  sub_sector: string | null;
  size: string | null;
  geography: string | null;
  client_status: string;
  website: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CompanyDetail extends Company {
  contacts: Contact[];
  engagements: Engagement[];
  matched_signals: Signal[];
}

export interface CompanyListResponse {
  companies: Company[];
  total: number;
  page: number;
  page_size: number;
}
