import { Link, useParams } from 'react-router-dom';
import { useCompany } from '../hooks/useCompany';
import SignalCard from '../components/signals/SignalCard';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  past: 'bg-slate-100 text-slate-600',
  target: 'bg-orange-100 text-orange-800',
};

const INDUSTRY_LABELS: Record<string, string> = {
  automotive: 'Automotive',
  aerospace_defense: 'Aerospace & Defense',
  energy: 'Energy',
};

const STRENGTH_LABELS = ['', 'Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong'];

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { company, loading, error } = useCompany(id);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>;
  if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
  if (!company) return <div className="p-8 text-center text-slate-500">Company not found</div>;

  const statusColor = STATUS_COLORS[company.client_status] || 'bg-slate-100 text-slate-600';

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
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
                  {company.sub_sector.replace('_', ' ')}
                </span>
              )}
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColor}`}>
                {company.client_status}
              </span>
            </div>
          </div>
          {company.website && (
            <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
              Website
            </a>
          )}
        </div>
        <div className="flex gap-6 mt-4 text-sm text-slate-500">
          {company.geography && <span>{company.geography}</span>}
          {company.size && <span>Size: {company.size}</span>}
        </div>
        {company.notes && <p className="mt-3 text-sm text-slate-600">{company.notes}</p>}
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">
          Contacts ({company.contacts.length})
        </h2>
        {company.contacts.length === 0 ? (
          <p className="text-sm text-slate-500">No contacts yet.</p>
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
                {company.contacts.map((contact) => (
                  <tr key={contact.id} className="border-b border-slate-100">
                    <td className="py-2 font-medium text-slate-900">{contact.name}</td>
                    <td className="py-2 text-slate-600">{contact.title || '—'}</td>
                    <td className="py-2 text-slate-600">
                      {contact.relationship_strength
                        ? STRENGTH_LABELS[contact.relationship_strength] || contact.relationship_strength
                        : '—'}
                    </td>
                    <td className="py-2 text-slate-600">{contact.last_interaction_date || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {company.engagements.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">
            Engagements ({company.engagements.length})
          </h2>
          <div className="space-y-3">
            {company.engagements.map((eng) => (
              <div key={eng.id} className="border border-slate-100 rounded p-3">
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
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">
          Matched Signals ({company.matched_signals.length})
        </h2>
        {company.matched_signals.length === 0 ? (
          <p className="text-sm text-slate-500">No signals matched to this company yet.</p>
        ) : (
          <div className="space-y-3">
            {company.matched_signals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
