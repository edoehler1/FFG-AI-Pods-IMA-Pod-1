import { useEffect, useState } from 'react';
import {
  fetchCompanyProfile,
  triggerProfileGeneration,
  fetchFinancialAnalysis,
  triggerFinancialAnalysis,
  fetchAnnualBaseline,
  triggerBaselineGeneration,
} from '../../api/companies';
import { markdownToHtml, formatDate } from '../../utils/formatters';

interface CompanyProfileProps {
  companyId: string;
}

interface ProfileSections {
  theStory: string;
  keyDevelopments: string;
  financialPosition: string;
  opportunity: string;
  whoShouldAct: string;
}

function parseProfileSections(narrative: string): ProfileSections {
  const sections: ProfileSections = {
    theStory: '',
    keyDevelopments: '',
    financialPosition: '',
    opportunity: '',
    whoShouldAct: '',
  };

  const sectionMap: [RegExp, keyof ProfileSections][] = [
    [/## The Story/i, 'theStory'],
    [/## Key Developments/i, 'keyDevelopments'],
    [/## Financial Position/i, 'financialPosition'],
    [/## S&? Opportunity/i, 'opportunity'],
    [/## Who Should Act/i, 'whoShouldAct'],
  ];

  const lines = narrative.split('\n');
  let currentKey: keyof ProfileSections | null = null;
  let currentLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('# ') && !line.startsWith('## ')) continue;

    let matched = false;
    for (const [pattern, key] of sectionMap) {
      if (pattern.test(line)) {
        if (currentKey) {
          sections[currentKey] = currentLines.join('\n').trim();
        }
        currentKey = key;
        currentLines = [];
        matched = true;
        break;
      }
    }
    if (!matched && currentKey) {
      currentLines.push(line);
    }
  }
  if (currentKey) {
    sections[currentKey] = currentLines.join('\n').trim();
  }

  return sections;
}

function extractTaxonomyTag(text: string): string | null {
  const match = text.match(/Taxonomy tag:\s*\[?([^\]\n]+)\]?/i);
  return match ? match[1].trim() : null;
}

function SectionCard({ title, children, className = '' }: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`border border-slate-200 rounded-lg p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-slate-900 mb-3">{title}</h3>
      {children}
    </div>
  );
}

export default function CompanyProfile({ companyId }: CompanyProfileProps) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [financialContent, setFinancialContent] = useState<string | null>(null);
  const [financialGeneratedAt, setFinancialGeneratedAt] = useState<string | null>(null);
  const [financialLoading, setFinancialLoading] = useState(true);
  const [financialGenerating, setFinancialGenerating] = useState(false);
  const [showFinancialAnalysis, setShowFinancialAnalysis] = useState(false);

  const [baselineContent, setBaselineContent] = useState<string | null>(null);
  const [baselineGeneratedAt, setBaselineGeneratedAt] = useState<string | null>(null);
  const [baselineSignalCount, setBaselineSignalCount] = useState<number | null>(null);
  const [baselineLoading, setBaselineLoading] = useState(true);
  const [baselineGenerating, setBaselineGenerating] = useState(false);
  const [showBaseline, setShowBaseline] = useState(false);

  useEffect(() => {
    fetchCompanyProfile(companyId)
      .then((data) => {
        setNarrative(data.profile_narrative);
        setGeneratedAt(data.generated_at);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    fetchFinancialAnalysis(companyId)
      .then((data) => {
        setFinancialContent(data.content);
        setFinancialGeneratedAt(data.generated_at);
      })
      .catch(() => {})
      .finally(() => setFinancialLoading(false));

    fetchAnnualBaseline(companyId)
      .then((data) => {
        setBaselineContent(data.timeline_content);
        setBaselineGeneratedAt(data.generated_at);
        setBaselineSignalCount(data.signal_count);
      })
      .catch(() => {})
      .finally(() => setBaselineLoading(false));
  }, [companyId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await triggerProfileGeneration(companyId);
      setNarrative(data.profile_narrative);
      setGeneratedAt(data.generated_at);
    } catch (err: any) {
      setError(err.message || 'Failed to generate profile');
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateBaseline = async () => {
    setBaselineGenerating(true);
    try {
      const data = await triggerBaselineGeneration(companyId);
      setBaselineContent(data.timeline_content);
      setBaselineGeneratedAt(data.generated_at);
      setBaselineSignalCount(data.signal_count);
      setShowBaseline(true);
    } catch {
    } finally {
      setBaselineGenerating(false);
    }
  };

  const handleGenerateFinancial = async () => {
    setFinancialGenerating(true);
    try {
      const data = await triggerFinancialAnalysis(companyId);
      setFinancialContent(data.content);
      setFinancialGeneratedAt(data.generated_at);
      setShowFinancialAnalysis(true);
    } catch {
    } finally {
      setFinancialGenerating(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-500 py-4">Loading profile...</p>;
  }

  if (!narrative) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-500 mb-4">No profile has been generated for this company yet.</p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-slate-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate Profile'}
        </button>
        {error && <p className="text-red-600 text-sm mt-3">{error}</p>}
      </div>
    );
  }

  const sections = parseProfileSections(narrative);
  const taxonomyTag = extractTaxonomyTag(sections.opportunity);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="text-xs text-slate-400">
          {generatedAt && <span>Generated {formatDate(generatedAt, true)}</span>}
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
        >
          {generating ? 'Refreshing...' : 'Refresh Profile'}
        </button>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}

      {sections.theStory && (
        <div className="border-l-4 border-slate-900 pl-5 py-3">
          <h3 className="text-sm font-semibold text-slate-900 mb-2">The Story</h3>
          <div
            className="text-sm text-slate-700 leading-relaxed [&_p]:my-2 [&_strong]:text-slate-900"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(sections.theStory) }}
          />
        </div>
      )}

      {sections.keyDevelopments && (
        <SectionCard title="Key Developments (Past 12 Months)">
          <div
            className="text-sm text-slate-600 space-y-1 [&_ul]:space-y-2 [&_li]:border-b [&_li]:border-slate-50 [&_li]:pb-2 [&_li:last-child]:border-0 [&_strong]:text-slate-700"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(sections.keyDevelopments) }}
          />
        </SectionCard>
      )}

      {sections.financialPosition && (
        <SectionCard title="Financial Position">
          <div
            className="text-sm text-slate-600 [&_p]:my-2 [&_strong]:text-slate-700"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(sections.financialPosition) }}
          />
          <div className="mt-3 pt-3 border-t border-slate-100">
            {financialLoading ? (
              <span className="text-xs text-slate-400">Loading financial analysis...</span>
            ) : financialContent ? (
              <button
                onClick={() => setShowFinancialAnalysis(!showFinancialAnalysis)}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                {showFinancialAnalysis ? 'Hide' : 'View'} Full Financial Analysis
              </button>
            ) : (
              <button
                onClick={handleGenerateFinancial}
                disabled={financialGenerating}
                className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
              >
                {financialGenerating ? 'Generating...' : 'Generate Financial Analysis'}
              </button>
            )}
          </div>
        </SectionCard>
      )}

      {showFinancialAnalysis && financialContent && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-900">Financial Analysis</h3>
            <div className="flex items-center gap-3">
              {financialGeneratedAt && (
                <span className="text-xs text-slate-400">
                  {formatDate(financialGeneratedAt, true)}
                </span>
              )}
              <button
                onClick={handleGenerateFinancial}
                disabled={financialGenerating}
                className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-2 py-0.5 hover:bg-white disabled:opacity-50"
              >
                {financialGenerating ? 'Refreshing...' : 'Refresh'}
              </button>
              <button
                onClick={() => setShowFinancialAnalysis(false)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                Close
              </button>
            </div>
          </div>
          <div
            className="prose prose-slate prose-sm max-w-none
              prose-headings:text-slate-900 prose-headings:font-semibold
              prose-h2:text-sm prose-h2:mt-4 prose-h2:mb-2
              prose-li:my-0.5 prose-p:my-2
              prose-strong:text-slate-700"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(financialContent) }}
          />
        </div>
      )}

      {sections.opportunity && (
        <SectionCard title="S& Opportunity" className="bg-amber-50 border-amber-200">
          {taxonomyTag && (
            <span className="inline-block text-xs font-medium px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 mb-3">
              {taxonomyTag}
            </span>
          )}
          <div
            className="text-sm text-slate-700 [&_p]:my-2 [&_strong]:text-slate-900 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-0.5"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(
              sections.opportunity
                .replace(/Taxonomy tag:.*$/im, '')
                .replace(/Key Contacts[\s\S]*/i, '')
                .trim()
            ) }}
          />
        </SectionCard>
      )}

      {sections.whoShouldAct && (
        <SectionCard title="Who Should Act">
          <div
            className="text-sm text-slate-600 [&_ul]:space-y-2 [&_li]:bg-slate-50 [&_li]:rounded [&_li]:px-3 [&_li]:py-2 [&_strong]:text-slate-800 [&_a]:text-blue-600 [&_a]:hover:underline"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(sections.whoShouldAct) }}
          />
        </SectionCard>
      )}

      <div className="border-t border-slate-200 pt-4 mt-2">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-900">Annual Baseline</h3>
          <div className="flex items-center gap-3">
            {baselineLoading ? (
              <span className="text-xs text-slate-400">Loading...</span>
            ) : baselineContent ? (
              <>
                {baselineGeneratedAt && (
                  <span className="text-xs text-slate-400">
                    {formatDate(baselineGeneratedAt, true)} · {baselineSignalCount} signals
                  </span>
                )}
                <button
                  onClick={() => setShowBaseline(!showBaseline)}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  {showBaseline ? 'Hide' : 'View'} Baseline
                </button>
                <button
                  onClick={handleGenerateBaseline}
                  disabled={baselineGenerating}
                  className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded px-2 py-0.5 hover:bg-slate-50 disabled:opacity-50"
                >
                  {baselineGenerating ? 'Refreshing...' : 'Refresh'}
                </button>
              </>
            ) : (
              <button
                onClick={handleGenerateBaseline}
                disabled={baselineGenerating}
                className="bg-slate-900 text-white px-3 py-1 rounded text-xs font-medium hover:bg-slate-800 disabled:opacity-50"
              >
                {baselineGenerating ? 'Generating...' : 'Generate Baseline'}
              </button>
            )}
          </div>
        </div>

        {showBaseline && baselineContent && (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-5">
            <div
              className="prose prose-slate prose-sm max-w-none
                prose-headings:text-slate-900 prose-headings:font-semibold
                prose-h1:text-lg prose-h1:mb-3
                prose-h2:text-sm prose-h2:mt-5 prose-h2:mb-2
                prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1
                prose-li:my-0.5 prose-p:my-2
                prose-strong:text-slate-700"
              dangerouslySetInnerHTML={{ __html: markdownToHtml(baselineContent) }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
