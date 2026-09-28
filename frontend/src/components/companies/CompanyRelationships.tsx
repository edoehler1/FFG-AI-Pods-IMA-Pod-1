import { useEffect, useState } from 'react';
import client from '../../api/client';
import { markdownToHtml, formatDate } from '../../utils/formatters';

interface RelationshipData {
  company_id: string;
  company_name: string;
  pwc_engagement_history: string | null;
  pwc_engagement_fetched_at: string | null;
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

export default function CompanyRelationships({ companyId }: Props) {
  const [data, setData] = useState<RelationshipData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showPwcHistory, setShowPwcHistory] = useState(true);

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

  const { pwc_engagement_history, pwc_engagement_fetched_at, manual_contacts, manual_engagements, has_pwc_data } = data;

  return (
    <div className="space-y-8">
      {/* PwC Engagement History */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-900">PwC Engagement History</h2>
            {has_pwc_data && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200">
                People Connector
              </span>
            )}
          </div>
          {has_pwc_data && (
            <button
              onClick={() => setShowPwcHistory(!showPwcHistory)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              {showPwcHistory ? 'Collapse' : 'Expand'}
            </button>
          )}
        </div>

        {has_pwc_data && pwc_engagement_history ? (
          <>
            {pwc_engagement_fetched_at && (
              <p className="text-xs text-slate-400 mb-2">
                Last updated: {formatDate(pwc_engagement_fetched_at)}
              </p>
            )}
            {showPwcHistory && (
              <div
                className="prose prose-sm max-w-none text-slate-700 border border-slate-200 rounded-lg p-4 bg-slate-50"
                dangerouslySetInnerHTML={{ __html: markdownToHtml(pwc_engagement_history) }}
              />
            )}
          </>
        ) : (
          <div className="text-center py-6 border border-dashed border-slate-200 rounded-lg">
            <p className="text-sm text-slate-500">No PwC engagement data available yet.</p>
            <p className="text-xs text-slate-400 mt-1">
              Run enrichment with <code className="bg-slate-100 px-1 rounded">--mcp people_engagements</code> to populate.
            </p>
          </div>
        )}
      </div>

      {/* Manual Contacts */}
      <div>
        <h2 className="text-sm font-semibold text-slate-900 mb-3">
          Contacts ({manual_contacts.length})
        </h2>
        {manual_contacts.length === 0 ? (
          <p className="text-sm text-slate-500">No contacts entered yet.</p>
        ) : (
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
        )}
      </div>

      {/* Manual Engagements */}
      <div>
        <h2 className="text-sm font-semibold text-slate-900 mb-3">
          Past Engagements ({manual_engagements.length})
        </h2>
        {manual_engagements.length === 0 ? (
          <p className="text-sm text-slate-500">No engagements recorded yet.</p>
        ) : (
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
        )}
      </div>
    </div>
  );
}
