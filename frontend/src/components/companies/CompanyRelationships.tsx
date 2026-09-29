import { useEffect, useState } from 'react';
import client from '../../api/client';
import { markdownToHtml, formatDate } from '../../utils/formatters';

interface PersonRecord {
  name: string;
  role: string | null;
  office: string | null;
  email: string | null;
}

interface StaffMember {
  name: string;
  role: string | null;
  email: string | null;
}

interface EngagementRecord {
  name: string;
  service_line: string | null;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  status: 'open' | 'closed' | null;
  staff_count: number;
  key_staff: (string | StaffMember)[];
}

interface GroupedEngagements {
  strategy: EngagementRecord[];
  other: { service_line: string; engagements: EngagementRecord[] }[];
}

interface StructuredData {
  summary_text: string;
  grp: PersonRecord | null;
  account_team: PersonRecord[];
  engagement_staff: PersonRecord[];
  engagements?: EngagementRecord[];
  total_people_count: number;
  has_grp: boolean;
  has_account_team: boolean;
}

interface RelationshipData {
  company_id: string;
  company_name: string;
  pwc_engagement_history: string | null;
  pwc_engagement_fetched_at: string | null;
  pwc_structured: StructuredData | null;
  pwc_grouped_engagements: GroupedEngagements | null;
  manual_contacts: {
    name: string;
    title: string | null;
    email: string | null;
    relationship_strength: number | null;
    last_interaction_date: string | null;
    notes: string | null;
  }[];
  manual_engagements: {
    date: string | null;
    project_type: string | null;
    capabilities_pitched: string | null;
    outcome: string | null;
    team: string | null;
    notes: string | null;
  }[];
  has_pwc_data: boolean;
}

const STRENGTH_LABELS = ['', 'Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong'];
const STRENGTH_COLORS = ['', 'text-red-600', 'text-orange-600', 'text-amber-600', 'text-green-600', 'text-emerald-700'];

interface Props {
  companyId: string;
}

function PersonBadge({ person, highlight }: { person: PersonRecord; highlight?: boolean }) {
  return (
    <div className="flex items-center gap-2 py-1.5 flex-wrap">
      <span className={`text-sm ${highlight ? 'font-semibold text-slate-900' : 'font-medium text-slate-700'}`}>
        {person.name}
      </span>
      {person.role && (
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
          highlight ? 'bg-violet-100 text-violet-700' : 'bg-slate-100 text-slate-600'
        }`}>
          {person.role}
        </span>
      )}
      {person.office && (
        <span className="text-xs text-slate-400">{person.office}</span>
      )}
      {person.email && (
        <a href={`mailto:${person.email}`} className="text-xs text-blue-500 hover:underline">
          {person.email}
        </a>
      )}
    </div>
  );
}

const ADVISORY_LINE_MAP: [RegExp, string, string][] = [
  [/deal|ddv|separation|divestiture|integration|fdd|m&a|merger|acquisition/i, 'Deals', 'bg-orange-100 text-orange-700'],
  [/cyber|security|identity|resilience|cloud security|nist|cmmc/i, 'Cyber', 'bg-red-100 text-red-700'],
  [/risk|regulatory|compliance|forensic|investigation|sox|internal audit|abac|fcpa/i, 'Risk & Forensics', 'bg-amber-100 text-amber-700'],
  [/workforce|workday|hcm|hr |human capital/i, 'Workforce', 'bg-teal-100 text-teal-700'],
  [/cmaas|technical accounting|restructur/i, 'CMAAS', 'bg-indigo-100 text-indigo-700'],
  [/dat|sap|erp|digital core|digital assurance/i, 'Digital & Tech', 'bg-cyan-100 text-cyan-700'],
  [/valuat|impair|purchase price/i, 'Valuations', 'bg-purple-100 text-purple-700'],
  [/tax|salt|transfer pricing|excise/i, 'Tax Advisory', 'bg-yellow-100 text-yellow-700'],
  [/sustainab|esg|climate|flaring/i, 'Sustainability', 'bg-emerald-100 text-emerald-700'],
  [/finance|fp&a|treasury|onestream/i, 'Finance & Operations', 'bg-sky-100 text-sky-700'],
  [/data|analytics|databricks|ai |governance.*ai/i, 'Data & AI', 'bg-violet-100 text-violet-700'],
  [/managed.*svcs|managed.*service/i, 'Managed Services', 'bg-slate-100 text-slate-600'],
];

function getAdvisoryLine(eng: EngagementRecord): { label: string; className: string } | null {
  const text = `${eng.name || ''} ${eng.service_line || ''} ${eng.description || ''}`;
  for (const [pattern, label, className] of ADVISORY_LINE_MAP) {
    if (pattern.test(text)) return { label, className };
  }
  return null;
}

function EngagementCard({ eng }: { eng: EngagementRecord }) {
  const dates = [eng.start_date, eng.end_date].filter(Boolean).join(' — ');
  const advisoryLine = getAdvisoryLine(eng);
  return (
    <div className={`border rounded p-3 bg-white ${eng.status === 'open' ? 'border-green-200' : 'border-slate-100'}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-wrap">
          <span className="text-sm font-medium text-slate-900 truncate">{eng.name}</span>
          {eng.status === 'open' && (
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-green-100 text-green-800 shrink-0">OPEN</span>
          )}
          {eng.status === 'closed' && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500 shrink-0">CLOSED</span>
          )}
          {advisoryLine && (
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${advisoryLine.className}`}>
              {advisoryLine.label}
            </span>
          )}
        </div>
        <span className="text-xs text-slate-400 shrink-0">{eng.staff_count} staff</span>
      </div>
      {(dates || eng.service_line) && (
        <div className="flex items-center gap-2 mt-1 text-xs text-slate-500 flex-wrap">
          {dates && <span>{dates}</span>}
          {eng.service_line && (
            <span className="px-1.5 py-0.5 rounded bg-slate-50 text-slate-500 border border-slate-200">
              {eng.service_line}
            </span>
          )}
        </div>
      )}
      {eng.description && (
        <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">{eng.description}</p>
      )}
      {eng.key_staff.length > 0 && (
        <div className="mt-1.5 space-y-0.5">
          {eng.key_staff.map((staff, i) => {
            if (typeof staff === 'string') {
              return <p key={i} className="text-xs text-slate-500">{staff}</p>;
            }
            return (
              <div key={i} className="flex items-center gap-1.5 text-xs">
                <span className="font-medium text-slate-700">{staff.name}</span>
                {staff.role && <span className="text-slate-400">· {staff.role}</span>}
                {staff.email && (
                  <a href={`mailto:${staff.email}`} className="text-blue-500 hover:underline">{staff.email}</a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CollapsibleSection({ title, count, children, defaultOpen = false }: {
  title: string;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left py-2"
      >
        <span className="text-xs text-slate-400">{open ? '▼' : '▶'}</span>
        <span className="text-sm font-semibold text-slate-700">{title}</span>
        <span className="text-xs text-slate-400">({count})</span>
      </button>
      {open && <div className="pl-4 space-y-2">{children}</div>}
    </div>
  );
}

export default function CompanyRelationships({ companyId }: Props) {
  const [data, setData] = useState<RelationshipData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    client
      .get<RelationshipData>(`/companies/${companyId}/relationships`)
      .then((res) => setData(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [companyId]);

  if (loading) return <p className="text-sm text-slate-500">Loading relationships...</p>;
  if (error) return <p className="text-sm text-red-500">Failed to load relationship data.</p>;
  if (!data) return null;

  const { pwc_structured: structured, pwc_grouped_engagements: grouped, pwc_engagement_history,
    pwc_engagement_fetched_at, manual_contacts, manual_engagements, has_pwc_data } = data;

  const hasStructured = structured !== null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-900">PwC Relationships</h2>
          {has_pwc_data && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200">
              People Connector
            </span>
          )}
        </div>
        {pwc_engagement_fetched_at && (
          <span className="text-xs text-slate-400">Updated {formatDate(pwc_engagement_fetched_at)}</span>
        )}
      </div>

      {!has_pwc_data && (
        <div className="text-center py-6 border border-dashed border-slate-200 rounded-lg">
          <p className="text-sm text-slate-500">No PwC engagement data available yet.</p>
          <p className="text-xs text-slate-400 mt-1">
            Run enrichment with <code className="bg-slate-100 px-1 rounded">--mcp people_engagements</code> to populate.
          </p>
        </div>
      )}

      {/* Structured view */}
      {hasStructured && (
        <>
          {/* GRP + Account Team */}
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Key Relationships</h3>
            <p className="text-[11px] text-slate-400 mb-3">Senior PwC people responsible for this client relationship</p>

            {structured.grp && (
              <div className="mb-3">
                <span className="text-[10px] font-bold text-violet-600 uppercase tracking-wider">GRP</span>
                <p className="text-[10px] text-slate-400 mb-0.5">Global Relationship Partner — owns this client relationship at PwC</p>
                <PersonBadge person={structured.grp} highlight />
              </div>
            )}

            {structured.account_team.length > 0 && (
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Account Team</span>
                <p className="text-[10px] text-slate-400 mb-0.5">Designated CRM team managing this client across service lines</p>
                {structured.account_team.map((p, i) => (
                  <PersonBadge key={i} person={p} />
                ))}
              </div>
            )}
          </div>

          {/* Strategy& Engagements — prominent */}
          {grouped && grouped.strategy.length > 0 && (
            <div>
              <div className="mb-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">Strategy& Engagements</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                    {grouped.strategy.length}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">Strategy, Consulting Solutions, and related advisory sub-practices</p>
              </div>
              <div className="space-y-2">
                {grouped.strategy.map((eng, i) => (
                  <EngagementCard key={i} eng={eng} />
                ))}
              </div>
            </div>
          )}

          {grouped && grouped.strategy.length === 0 && (
            <div className="border border-dashed border-slate-200 rounded-lg p-4 text-center">
              <p className="text-sm text-slate-500">No Strategy& engagements found for this company.</p>
              <p className="text-xs text-slate-400 mt-1">Other advisory work is shown below.</p>
            </div>
          )}

          {/* Other Advisory — collapsible by service line */}
          {grouped && grouped.other.length > 0 && (
            <div className="space-y-1">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-0.5">Other Advisory</h3>
              <p className="text-[11px] text-slate-400 mb-2">Deals, Tax, CMAAS, Valuations, and other non-strategy advisory work</p>
              {grouped.other.map((group, i) => (
                <CollapsibleSection
                  key={i}
                  title={group.service_line}
                  count={group.engagements.length}
                >
                  {group.engagements.map((eng, j) => (
                    <EngagementCard key={j} eng={eng} />
                  ))}
                </CollapsibleSection>
              ))}
            </div>
          )}

          {/* Engagement Staff */}
          {structured.engagement_staff.length > 0 && (
            <CollapsibleSection
              title="Advisory Staff"
              count={structured.engagement_staff.length}
            >
              <div className="bg-white border border-slate-200 rounded-lg p-3">
                {structured.engagement_staff.map((p, i) => (
                  <PersonBadge key={i} person={p} />
                ))}
              </div>
            </CollapsibleSection>
          )}
        </>
      )}

      {/* Markdown fallback for old data without structured parsing */}
      {has_pwc_data && !hasStructured && pwc_engagement_history && (
        <div
          className="prose prose-sm max-w-none text-slate-700 border border-slate-200 rounded-lg p-4 bg-slate-50"
          dangerouslySetInnerHTML={{ __html: markdownToHtml(pwc_engagement_history) }}
        />
      )}

      {/* Client-Side Contacts (Manual) */}
      <div>
        <h2 className="text-sm font-semibold text-slate-900 mb-0.5">
          Client-Side Contacts ({manual_contacts.length})
        </h2>
        <p className="text-[11px] text-slate-400 mb-3">Contacts at the company, manually entered. Not from PwC systems.</p>
        {manual_contacts.length === 0 ? (
          <p className="text-sm text-slate-500">No client contacts entered yet.</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-500">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Title</th>
                    <th className="pb-2 font-medium">Relationship</th>
                    <th className="pb-2 font-medium">Last Interaction</th>
                  </tr>
                </thead>
                <tbody>
                  {manual_contacts.map((c, i) => (
                    <tr key={i} className="border-b border-slate-100">
                      <td className="py-2 font-medium text-slate-900">{c.name}</td>
                      <td className="py-2 text-slate-600">{c.title || '—'}</td>
                      <td className={`py-2 font-medium ${c.relationship_strength ? STRENGTH_COLORS[c.relationship_strength] : 'text-slate-400'}`}>
                        {c.relationship_strength ? STRENGTH_LABELS[c.relationship_strength] : '—'}
                      </td>
                      <td className="py-2 text-slate-600">{c.last_interaction_date || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {manual_contacts.every(c => !c.email) && (
              <p className="text-[11px] text-slate-400 mt-2 italic">
                These are placeholder contacts. Add real contacts or link Salesforce to populate with verified data.
              </p>
            )}
          </>
        )}
      </div>

      {/* Manual Engagements */}
      {manual_engagements.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-900 mb-3">
            Past Engagements ({manual_engagements.length})
          </h2>
          <div className="space-y-2">
            {manual_engagements.map((eng, i) => (
              <div key={i} className="border border-slate-100 rounded p-3">
                <div className="flex items-center gap-3 text-sm">
                  {eng.project_type && <span className="font-medium text-slate-900">{eng.project_type}</span>}
                  {eng.outcome && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      eng.outcome === 'won' ? 'bg-green-100 text-green-800' :
                      eng.outcome === 'lost' ? 'bg-red-100 text-red-800' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {eng.outcome}
                    </span>
                  )}
                  {eng.date && <span className="text-slate-400">{eng.date}</span>}
                </div>
                {eng.capabilities_pitched && (
                  <p className="text-xs text-slate-500 mt-1">{eng.capabilities_pitched}</p>
                )}
                {eng.team && (
                  <p className="text-xs text-slate-400 mt-1">Team: {eng.team}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
