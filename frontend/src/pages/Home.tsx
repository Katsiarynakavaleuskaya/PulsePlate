import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getCbtInsight, type CbtInsightResponse } from '../api/premium';
import { UnauthorizedError } from '../api/client';
import { HomeOpenSetupCta } from '../components/cta';
import { Card, CardContent, Input, buttonClasses } from '../components/ui';
import LiveProgressIndicator from '../features/progress/LiveProgressIndicator';
import { useAuth } from '../lib/auth';
import { usePremium } from '../lib/usePremium';

const MAX_AI_QUERY_LENGTH = 500;

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

export default function Home() {
  const isPremium = usePremium();
  const { isAuthenticated, isLoading } = useAuth();
  const [aiQuery, setAiQuery] = useState('');
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<CbtInsightResponse | null>(null);
  const hasSession = isAuthenticated;
  const premiumLabel = isPremium === undefined ? 'Checking…' : isPremium ? 'Active' : 'Inactive';
  const statusTone = isPremium === true ? 'text-[var(--color-success)]' : 'text-text';
  const apiStatusLabel = isLoading ? 'Checking…' : hasSession ? 'Connected' : 'Not Set';
  const apiStatusDescription = isLoading
    ? 'Verifying your secure session state with the server.'
      : hasSession
      ? 'Your secure session is active. Personalized guidance is enabled.'
      : 'Configure your API key once to establish a secure session and unlock personalized insights.';
  const aiQueryLength = aiQuery.trim().length;
  const aiHasPremiumAccess = isAuthenticated && isPremium === true;
  const aiSources = aiResult?.sources.slice(0, 2) ?? [];

  async function handleAiSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
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

  return (
    <main className="flex min-h-screen flex-col bg-[var(--color-bg)]">
      {/* Hero Section */}
      <section className="px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
            Wellness Control Panel
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-[var(--color-text)] sm:text-5xl">
            Home
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-[var(--color-text-muted)]">
            Quick access to your wellness setup, nutrition tracking, and progress insights. Everything you need for
            optimal health in one place.
          </p>
        </div>
      </section>

      {/* Status Cards */}
      <section className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* API Status Card */}
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex h-full flex-col justify-between p-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                API Connection
              </p>
              <p className="mt-3 text-2xl font-semibold text-[var(--color-text)]">
                {apiStatusLabel}
              </p>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-muted)]">
              {apiStatusDescription}
            </p>
            </CardContent>
          </Card>

          {/* Premium Status Card */}
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex h-full flex-col justify-between p-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                Premium Status
              </p>
              <p className={`mt-3 text-2xl font-semibold ${statusTone}`}>
                {premiumLabel}
              </p>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-muted)]">
              {isPremium
                ? 'You have access to advanced analytics and premium nutrition optimization.'
                : 'Upgrade to Pro to unlock advanced insights, meal planning, and premium features.'}
            </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Progress Indicator */}
      <section className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <LiveProgressIndicator source="home" ctaTo="/progress" ctaLabel="View detailed progress" />
        </div>
      </section>

      <section className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="space-y-4 p-6">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                  AI Reliability
                </p>
                <h2 className="text-xl font-semibold text-[var(--color-text)]">AI Insight</h2>
                <p className="text-sm leading-relaxed text-[var(--color-text-muted)]">
                  Ask one question and review the server-validated insight, reliability signals, and source coverage.
                </p>
              </div>

              {!isAuthenticated ? (
                <div className="space-y-3">
                  <p className="text-sm text-[var(--color-text-muted)]">
                    Connect your secure session before using the AI insight workflow.
                  </p>
                  <Link
                    to="/enter-key"
                    className={buttonClasses({ variant: 'secondary', size: 'md', className: 'inline-flex' })}
                  >
                    Connect secure session
                  </Link>
                </div>
              ) : isPremium === undefined ? (
                <p className="text-sm text-[var(--color-text-muted)]">Checking premium access for AI insights…</p>
              ) : !aiHasPremiumAccess ? (
                <div className="space-y-3">
                  <p className="text-sm text-[var(--color-text-muted)]">
                    Upgrade to Pro to unlock AI reliability signals and guided insight summaries.
                  </p>
                  <Link
                    to="/pro"
                    className={buttonClasses({ variant: 'secondary', size: 'md', className: 'inline-flex' })}
                  >
                    Upgrade to Pro
                  </Link>
                </div>
              ) : (
                <>
                  <form className="space-y-3" onSubmit={handleAiSubmit}>
                    <label className="block text-sm font-medium text-[var(--color-text)]" htmlFor="home-ai-query">
                      Ask one question
                    </label>
                    <Input
                      id="home-ai-query"
                      maxLength={MAX_AI_QUERY_LENGTH}
                      placeholder="Example: What should I focus on this week for steadier nutrition?"
                      value={aiQuery}
                      onChange={(event) => setAiQuery(event.target.value)}
                    />
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs text-[var(--color-text-muted)]">
                        {aiQueryLength}/{MAX_AI_QUERY_LENGTH}
                      </span>
                      <button
                        className={buttonClasses({ variant: 'primary', size: 'md' })}
                        disabled={aiLoading}
                        type="submit"
                      >
                        {aiLoading ? 'Loading…' : 'Generate insight'}
                      </button>
                    </div>
                  </form>

                  {aiError ? (
                    <div
                      className="rounded-xl border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 p-3 text-sm text-[var(--color-text)]"
                      role="alert"
                    >
                      {aiError}
                    </div>
                  ) : null}

                  {aiResult ? (
                    <div className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="space-y-2">
                        <p className="text-sm leading-relaxed text-[var(--color-text)]">{aiResult.insight}</p>
                        <div className="flex flex-wrap gap-2 text-xs text-[var(--color-text-muted)]">
                          <span>Mode: {aiResult.mode}</span>
                          <span>Quota: {aiResult.quota_state}</span>
                          <span>RAG: {aiResult.rag_used ? 'Used' : 'Not used'}</span>
                          <span>Confidence: {aiResult.confidence.toFixed(2)}</span>
                          <span>Uncertainty: {aiResult.uncertainty.toFixed(2)}</span>
                        </div>
                      </div>

                      {aiResult.warnings.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                            Warnings
                          </p>
                          <ul className="space-y-1 text-sm text-[var(--color-text-muted)]">
                            {aiResult.warnings.map((warning, index) => (
                              <li key={index}>{warning}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {aiSources.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                            Sources
                          </p>
                          <ul className="space-y-1 text-sm text-[var(--color-text-muted)]">
                            {aiSources.map((source) => (
                              <li key={source.chunk_id}>
                                {basenameFromPath(source.file)}: {source.preview}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Quick Actions Section */}
      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-[var(--color-text)]">
              Quick Navigation
            </h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Jump to any section of your wellness journey
            </p>
          </div>

          {/* Primary Action */}
          <div className="mb-4">
            <HomeOpenSetupCta />
          </div>

          {/* Secondary Actions Grid */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Link
              to="/plate"
              className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
            >
              Nutrition Plate
            </Link>
            <Link
              to="/progress"
              className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
            >
              Progress View
            </Link>
            <Link
              to="/pro"
              className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
            >
              Premium Features
            </Link>
          </div>
        </div>
      </section>

      {/* Footer Spacing for Tab Bar */}
      <div className="h-24" />
    </main>
  );
}
