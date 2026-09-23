import { useEffect, useState } from 'react';
import { fetchCompanyAnalysis, triggerCompanyAnalysis } from '../../api/companies';

function markdownToHtml(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*\[(.+?)\]\*\*/g, '<strong>[$1]</strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul\/>])/gm, '<p>')
    .replace(/<p><\/p>/g, '')
    .replace(/<p>(<[hul])/g, '$1')
    .replace(/(<\/[hul].*?>)<\/p>/g, '$1');
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

interface CompanyAnalysisProps {
  companyId: string;
}

export default function CompanyAnalysis({ companyId }: CompanyAnalysisProps) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [signalCount, setSignalCount] = useState(0);
  const [filingCount, setFilingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCompanyAnalysis(companyId)
      .then((data) => {
        setNarrative(data.narrative);
        setGeneratedAt(data.generated_at);
        setSignalCount(data.signal_count || 0);
        setFilingCount(data.filing_count || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [companyId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await triggerCompanyAnalysis(companyId);
      setNarrative(data.narrative);
      setGeneratedAt(data.generated_at);
      setSignalCount(data.signal_count || 0);
      setFilingCount(data.filing_count || 0);
    } catch (err: any) {
      setError(err.message || 'Failed to generate analysis');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-500 py-4">Loading analysis...</p>;
  }

  if (!narrative) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-500 mb-4">No analysis has been generated for this company yet.</p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-slate-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate Analysis'}
        </button>
        {error && <p className="text-red-600 text-sm mt-3">{error}</p>}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-4 text-xs text-slate-400">
          {generatedAt && <span>Generated {formatDate(generatedAt)}</span>}
          <span>{filingCount} filings</span>
          <span>{signalCount} news signals</span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
        >
          {generating ? 'Refreshing...' : 'Refresh Analysis'}
        </button>
      </div>
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
      <div
        className="prose prose-slate prose-sm max-w-none
          prose-headings:text-slate-900 prose-headings:font-semibold
          prose-h1:text-xl prose-h1:mb-3
          prose-h2:text-base prose-h2:mt-6 prose-h2:mb-2
          prose-h3:text-sm prose-h3:mt-4 prose-h3:mb-1
          prose-li:my-0.5 prose-p:my-2
          prose-strong:text-slate-700
          prose-em:text-slate-500"
        dangerouslySetInnerHTML={{ __html: markdownToHtml(narrative) }}
      />
    </div>
  );
}
