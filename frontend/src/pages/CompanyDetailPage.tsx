import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useCompany } from '../hooks/useCompany';
import { fetchCompanyIntelligence, fetchCompanyMatches, fetchCuratedNews, fetchIndustryCuratedNews } from '../api/companies';
import CompanyForm from '../components/companies/CompanyForm';
import CompanyFilings from '../components/companies/CompanyFilings';
import CompanyNews from '../components/companies/CompanyNews';
import IndustryNews from '../components/companies/IndustryNews';
import CompanyWeeklyReport from '../components/companies/CompanyWeeklyReport';
import CompanyProfile from '../components/companies/CompanyProfile';
import CompanyEnrichments from '../components/companies/CompanyEnrichments';
import CompanyRelationships from '../components/companies/CompanyRelationships';
import ContactForm from '../components/contacts/ContactForm';
import EngagementForm from '../components/engagements/EngagementForm';
import type { Signal, MatchedSignal, CuratedCompanyNews, CuratedIndustryNews } from '../types/signal';
import SignalSummaryBadge, { MatchSummaryBadge } from '../components/common/SignalSummaryBadge';
import { INDUSTRY_LABELS, SIZE_LABELS } from '../utils/constants';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  past: 'bg-slate-100 text-slate-600',
  target: 'bg-orange-100 text-orange-800',
};

const STRENGTH_LABELS = ['', 'Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong'];

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'relationships', label: 'Relationships' },
  { key: 'profile', label: 'Profile' },
  { key: 'intelligence', label: 'Intelligence' },
  { key: 'filings', label: 'Filings' },
  { key: 'company_news', label: 'Company News' },
  { key: 'industry_news', label: 'Industry News' },
  { key: 'weekly_report', label: 'Weekly Report' },
] as const;

type TabKey = typeof TABS[number]['key'];

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { company, loading, error, refresh } = useCompany(id);
  const [showEdit, setShowEdit] = useState(false);
  const [showAddContact, setShowAddContact] = useState(false);
  const [showAddEngagement, setShowAddEngagement] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const [filings, setFilings] = useState<Signal[]>([]);
  const [companyMatches, setCompanyMatches] = useState<MatchedSignal[]>([]);
  const [industryNews, setIndustryNews] = useState<Signal[]>([]);
  const [intelLoading, setIntelLoading] = useState(true);
  const [intelError, setIntelError] = useState<string | null>(null);

  const [curatedCompanyNews, setCuratedCompanyNews] = useState<CuratedCompanyNews[]>([]);
  const [curatedCompanyDateRange, setCuratedCompanyDateRange] = useState<{ start: string; end: string } | null>(null);
  const [curatedCompanyLoading, setCuratedCompanyLoading] = useState(true);
  const [companyNewsDays, setCompanyNewsDays] = useState(7);

  const [curatedIndustryNews, setCuratedIndustryNews] = useState<CuratedIndustryNews[]>([]);
  const [curatedIndustryDateRange, setCuratedIndustryDateRange] = useState<{ start: string; end: string } | null>(null);
  const [curatedIndustryLoading, setCuratedIndustryLoading] = useState(true);
  const [industryNewsDays, setIndustryNewsDays] = useState(7);

  useEffect(() => {
    if (!id) return;
    setIntelLoading(true);
    setIntelError(null);
    Promise.all([
      fetchCompanyIntelligence(id),
      fetchCompanyMatches(id),
    ])
      .then(([intel, matches]) => {
        setFilings(intel.filings);
        setIndustryNews(intel.industry_news);
        const nonFilingMatches = matches.filter(
          (m) => m.signal.source_name !== 'sec_edgar'
        );
        setCompanyMatches(nonFilingMatches);
      })
      .catch(() => setIntelError('Failed to load intelligence data.'))
      .finally(() => setIntelLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setCuratedCompanyLoading(true);
    fetchCuratedNews(id, companyNewsDays)
      .then((data) => {
        setCuratedCompanyNews(data.curated_news);
        setCuratedCompanyDateRange(data.date_range);
      })
      .catch(() => setCuratedCompanyNews([]))
      .finally(() => setCuratedCompanyLoading(false));
  }, [id, companyNewsDays]);

  useEffect(() => {
    if (!company?.industry) return;
    setCuratedIndustryLoading(true);
    fetchIndustryCuratedNews(company.industry, industryNewsDays)
      .then((data) => {
        setCuratedIndustryNews(data.curated_news);
        setCuratedIndustryDateRange(data.date_range);
      })
      .catch(() => setCuratedIndustryNews([]))
      .finally(() => setCuratedIndustryLoading(false));
  }, [company?.industry, industryNewsDays]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>;
  if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
  if (!company) return <div className="p-8 text-center text-slate-500">Company not found</div>;

  const statusColor = STATUS_COLORS[company.client_status] || 'bg-slate-100 text-slate-600';

  const handleSaved = () => {
    setShowEdit(false);
    refresh();
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
      <Link to="/companies" className="text-sm text-blue-600 hover:underline">&larr; Back to companies</Link>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{company.name}</h1>
            <div className="flex items-center gap-2 mt-2">
              {company.industry && (
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {INDUSTRY_LABELS[company.industry] || company.industry}
                </span>
              )}
              {company.sub_sector && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {company.sub_sector.replace(/_/g, ' ')}
                </span>
              )}
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColor}`}>
                {company.client_status}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowEdit(true)}
              className="text-sm text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50"
            >
              Edit
            </button>
            {company.website && (
              <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                Website
              </a>
            )}
          </div>
        </div>
        <div className="flex gap-6 mt-4 text-sm text-slate-500">
          {company.geography && <span>{company.geography}</span>}
          {company.size && <span>{SIZE_LABELS[company.size] || company.size}</span>}
        </div>
        {company.notes && <p className="mt-3 text-sm text-slate-600">{company.notes}</p>}
      </div>

      <div className="border-b border-slate-200">
        <div className="flex">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm transition-colors ${
                activeTab === tab.key
                  ? 'border-b-2 border-slate-900 text-slate-900 font-medium'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.label}
              {tab.key === 'filings' && filings.length > 0 && (
                <span className="ml-2"><SignalSummaryBadge signals={filings} maxTypes={2} /></span>
              )}
              {tab.key === 'company_news' && curatedCompanyNews.length > 0 && (
                <span className="ml-2 text-xs text-slate-400">{curatedCompanyNews.length} curated</span>
              )}
              {tab.key === 'industry_news' && curatedIndustryNews.length > 0 && (
                <span className="ml-2 text-xs text-slate-400">{curatedIndustryNews.length} signals</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-900">
                  Contacts ({company.contacts.length})
                </h2>
                <button
                  onClick={() => setShowAddContact(true)}
                  className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50"
                >
                  + Add Contact
                </button>
              </div>
              {company.contacts.length === 0 ? (
                <p className="text-sm text-slate-500">No contacts yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-left text-slate-500">
                        <th className="pb-2 font-medium">Name</th>
                        <th className="pb-2 font-medium">Title</th>
                        <th className="pb-2 font-medium">Email</th>
                      </tr>
                    </thead>
                    <tbody>
                      {company.contacts.map((contact) => (
                        <tr key={contact.id} className="border-b border-slate-100">
                          <td className="py-2 font-medium text-slate-900">{contact.name}</td>
                          <td className="py-2 text-slate-600">{contact.title || '—'}</td>
                          <td className="py-2">
                            {contact.email ? (
                              <a href={`mailto:${contact.email}`} className="text-xs text-blue-500 hover:underline">{contact.email}</a>
                            ) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>



          </div>
        )}

        {activeTab === 'relationships' && id && (
          <CompanyRelationships companyId={id} />
        )}

        {activeTab === 'profile' && id && (
          <CompanyProfile companyId={id} />
        )}

        {activeTab === 'intelligence' && id && (
          <CompanyEnrichments companyId={id} companyIndustry={company.industry} />
        )}

        {activeTab === 'filings' && (
          intelLoading ? <p className="text-sm text-slate-500">Loading filings...</p>
          : intelError ? <p className="text-sm text-red-500">{intelError}</p>
          : <CompanyFilings filings={filings} companyId={id} />
        )}

        {activeTab === 'company_news' && (
          <CompanyNews
            curatedNews={curatedCompanyNews}
            dateRange={curatedCompanyDateRange}
            loading={curatedCompanyLoading}
            days={companyNewsDays}
            onDaysChange={setCompanyNewsDays}
          />
        )}

        {activeTab === 'industry_news' && (
          <IndustryNews
            curatedNews={curatedIndustryNews}
            industry={company.industry}
            dateRange={curatedIndustryDateRange}
            loading={curatedIndustryLoading}
            days={industryNewsDays}
            onDaysChange={setIndustryNewsDays}
          />
        )}

        {activeTab === 'weekly_report' && id && (
          <CompanyWeeklyReport companyId={id} />
        )}
      </div>

      {showEdit && (
        <CompanyForm company={company} onClose={() => setShowEdit(false)} onSaved={handleSaved} />
      )}

      {showAddContact && id && (
        <ContactForm
          companyId={id}
          onClose={() => setShowAddContact(false)}
          onSaved={() => { setShowAddContact(false); refresh(); }}
        />
      )}



    </div>
  );
}
