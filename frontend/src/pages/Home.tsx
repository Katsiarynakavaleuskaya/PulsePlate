import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCbtInsight, type CbtInsightResponse } from '../api/premium';
import { UnauthorizedError } from '../api/client';
import AiInsightPanel from '../components/insight/AiInsightPanel';
import { Card, CardContent, buttonClasses } from '../components/ui';
import { canonicalBrand } from '../styles/tokens';
import { useAuth } from '../lib/auth';
import { usePremium } from '../lib/usePremium';

const MAX_AI_QUERY_LENGTH = 500;
const insightSuggestions = ['More protein', 'Less sugar', 'Weekly plan'] as const;

function clampAiQuery(value: string): string {
  return value.slice(0, MAX_AI_QUERY_LENGTH);
}

function basenameFromPath(path: string): string {
  const segments = path.split(/[\\/]/).filter(Boolean);
  return segments.length > 0 ? segments[segments.length - 1] : path;
}

function mapCbtInsightErrorToMessage(error: unknown): string {
  const defaultMessage = 'Unable to load AI insight right now.';

  if (error instanceof UnauthorizedError) {
    return 'Your secure session expired. Reconnect and try again.';
  }

  const status =
    error instanceof Error
      ? Number.parseInt(error.message.match(/HTTP (\d{3})/)?.[1] ?? '', 10)
      : NaN;

  if (status === 401 || status === 403) {
    return 'Your secure session is no longer valid. Reconnect and try again.';
  }

  if (status === 422) {
    return 'We could not validate that question. Please rephrase it and try again.';
  }

  if (status === 429) {
    return 'You’ve reached the limit for AI insights. Please try again in a few minutes.';
  }

  if (status === 503 || status === 504) {
    return 'AI insight is temporarily unavailable. Please try again later.';
  }

  return defaultMessage;
}

function SurfaceCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}): JSX.Element {
  return (
    <Card className="rounded-2xl border-white/12 bg-white/[0.08] text-white shadow-none">
      <CardContent className="space-y-1 p-4">
        <p className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-white/48">{label}</p>
        <p className="text-2xl font-semibold tracking-[-0.04em] text-white">{value}</p>
        <p className="text-xs text-white/56">{detail}</p>
      </CardContent>
    </Card>
  );
}

function ActionTile({
  title,
  detail,
  to,
}: {
  title: string;
  detail: string;
  to: string;
}): JSX.Element {
  return (
    <Link
      to={to}
      className="rounded-2xl border border-white/12 bg-white/[0.08] p-4 transition hover:border-white/20 hover:bg-white/[0.11]"
    >
      <p className="text-sm font-semibold text-white">{title}</p>
      <p className="mt-1 text-xs text-white/62">{detail}</p>
    </Link>
  );
}

export default function Home(): JSX.Element {
  const isPremium = usePremium();
  const { isAuthenticated, isLoading } = useAuth();
  const [aiQuery, setAiQuery] = useState('');
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<CbtInsightResponse | null>(null);

  const apiStatusLabel = isLoading ? 'Checking…' : isAuthenticated ? 'Connected' : 'Offline';
  const premiumLabel = isPremium === undefined ? 'Checking…' : isPremium ? 'Active' : 'Locked';
  const aiHasPremiumAccess = isAuthenticated && isPremium === true;
  const aiQueryLength = aiQuery.trim().length;

  const insightResultCard = useMemo(() => {
    if (!aiResult) {
      return null;
    }

    const mappedTags = aiResult.sources
      .slice(0, 3)
      .map((source) => basenameFromPath(source.file));

    return {
      title: 'Tonight’s guidance',
      body: aiResult.insight,
      confidenceLabel: `Confidence ${aiResult.confidence.toFixed(2)}`,
      tags: mappedTags.length > 0 ? mappedTags : ['Meals', 'Goals'],
      metadata: [
        `Mode: ${aiResult.mode}`,
        `Quota: ${aiResult.quota_state}`,
        `RAG: ${aiResult.rag_used ? 'Used' : 'Not used'}`,
        `Confidence: ${aiResult.confidence.toFixed(2)}`,
        `Uncertainty: ${aiResult.uncertainty.toFixed(2)}`,
      ],
      warnings: aiResult.warnings,
      sources: aiResult.sources.map(
        (source) => `${basenameFromPath(source.file)}: ${source.preview}`
      ),
      primaryActionLabel: 'Apply',
      secondaryActionLabel: 'Review',
    };
  }, [aiResult]);

  async function handleAiSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (aiLoading) {
      return;
    }
    const nextQuery = aiQuery.trim();
    if (!nextQuery) {
      setAiError('Enter a short question to generate an AI insight.');
      return;
    }
    if (nextQuery.length > MAX_AI_QUERY_LENGTH) {
      setAiError(`Keep your question within ${MAX_AI_QUERY_LENGTH} characters.`);
      return;
    }

    setAiLoading(true);
    setAiError(null);

    try {
      const result = await getCbtInsight({ query: nextQuery });
      setAiResult(result);
    } catch (error) {
      setAiResult(null);
      setAiError(mapCbtInsightErrorToMessage(error));
    } finally {
      setAiLoading(false);
    }
  }

  function handleSuggestionClick(value: string): void {
    setAiQuery(clampAiQuery(value));
    setAiError(null);
  }

  return (
    <main className="min-h-screen bg-[var(--pp-navy)] px-4 py-6 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="rounded-[1.75rem] border border-white/12 bg-white/[0.08] p-6 shadow-[0_30px_60px_rgba(15,23,42,0.28)] sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/52">Calm control panel</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.06em] text-white sm:text-5xl">PulsePlate Home</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-white/62 sm:text-base">
            Quick actions, premium guidance, and one AI surface that stays grounded in your current session.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
              Session {apiStatusLabel}
            </span>
            <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
              Premium {premiumLabel}
            </span>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SurfaceCard label="Connection" value={apiStatusLabel} detail="Secure session status" />
          <SurfaceCard label="Premium" value={premiumLabel} detail="Access to guided features" />
          <SurfaceCard
            label="AI quota"
            value={aiResult?.quota_state === 'consumed' ? 'In use' : 'Ready'}
            detail="Server-side reliability lane"
          />
          <SurfaceCard
            label="Focus"
            value={aiResult?.rag_used ? 'Grounded' : 'Simple'}
            detail="RAG-backed when supporting context is available"
          />
        </section>

        <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(22rem,24rem)]">
          <div className="space-y-8">
            <div>
              <p className="text-sm font-semibold text-white">Quick actions</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <ActionTile title="Meal Log" detail="Log today’s meals" to="/plate" />
                <ActionTile title="BMI" detail="Check your baseline metrics" to="/bmi" />
                <ActionTile title="Setup" detail="Tune your nutrition inputs" to="/setup" />
                <ActionTile title="Progress" detail="Review weekly charts" to="/progress" />
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-white">Pro tools</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <ActionTile title="AI Coach" detail="Premium guidance and summaries" to="/pro" />
                <ActionTile title="Weekly Charts" detail="Longer-term signals" to="/progress" />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {!isAuthenticated ? (
              <section className="rounded-[2rem] border border-white/12 bg-white/[0.08] p-6">
                <h2 className="text-xl font-semibold text-white">AI Insight</h2>
                <p className="mt-2 text-sm leading-6 text-white/62">
                  Connect your secure session before using the AI insight workflow.
                </p>
                <Link
                  to="/enter-key"
                  className={buttonClasses({ className: 'mt-5 inline-flex rounded-2xl text-[var(--pp-navy)]' })}
                  style={{ backgroundColor: canonicalBrand.blue }}
                >
                  Connect secure session
                </Link>
              </section>
            ) : isPremium === undefined ? (
              <section className="rounded-[2rem] border border-white/12 bg-white/[0.08] p-6">
                <h2 className="text-xl font-semibold text-white">AI Insight</h2>
                <p className="mt-2 text-sm text-white/62">Checking premium access for AI insights…</p>
              </section>
            ) : !aiHasPremiumAccess ? (
              <section className="rounded-[2rem] border border-white/12 bg-white/[0.08] p-6">
                <h2 className="text-xl font-semibold text-white">AI Insight</h2>
                <p className="mt-2 text-sm leading-6 text-white/62">
                  Upgrade to Pro to unlock AI reliability signals and guided insight summaries.
                </p>
                <Link
                  to="/pro"
                  className={buttonClasses({ className: 'mt-5 inline-flex rounded-2xl text-[var(--pp-navy)]' })}
                  style={{ backgroundColor: canonicalBrand.blue }}
                >
                  Upgrade to Pro
                </Link>
              </section>
            ) : (
              <AiInsightPanel
                error={aiError}
                isLoading={aiLoading}
                query={aiQuery}
                result={insightResultCard}
                placeholder="For example: what should I focus on this week?"
                subtitle={
                  aiLoading
                    ? 'Generating a recommendation…'
                    : aiResult
                      ? 'Personalized recommendation for today'
                      : 'Formulate one question or use a quick suggestion'
                }
                suggestions={[...insightSuggestions]}
                onQueryChange={(value) => setAiQuery(clampAiQuery(value))}
                onSubmit={handleAiSubmit}
                onSuggestionClick={handleSuggestionClick}
              />
            )}

            <Card className="rounded-[2rem] border-white/12 bg-white/[0.05] text-white shadow-none">
              <CardContent className="space-y-3 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/48">Preview note</p>
                <p className="text-sm leading-6 text-white/68">
                  This home surface now follows the Figma review family: calm hero, compact status tiles, quick
                  actions, and a dedicated AI insight block.
                </p>
                <p className="text-xs text-white/48">{aiQueryLength}/{MAX_AI_QUERY_LENGTH} characters</p>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}
