import { FormEvent } from 'react';
import { Button, Input, buttonClasses } from '../ui';
import { canonicalBrand } from '../../styles/tokens';

export interface AiInsightResultCard {
  title: string;
  body: string;
  confidenceLabel: string;
  tags: string[];
  primaryActionLabel?: string;
  secondaryActionLabel?: string;
  onPrimaryAction?: () => void;
  onSecondaryAction?: () => void;
  metadata?: string[];
  warnings?: string[];
  sources?: string[];
}

interface AiInsightPanelProps {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  suggestions: string[];
  onSuggestionClick?: (value: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  subtitle?: string;
  error?: string | null;
  result?: AiInsightResultCard | null;
}

function SuggestionChip({
  label,
  onClick,
}: {
  label: string;
  onClick?: () => void;
}): JSX.Element {
  const interactive = typeof onClick === 'function';

  if (!interactive) {
    return (
      <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-[0.65rem] text-white/70">
        {label}
      </span>
    );
  }

  return (
    <button
      type="button"
      className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-[0.65rem] text-white/70 transition hover:border-white/20 hover:bg-white/[0.08]"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

export default function AiInsightPanel({
  query,
  onQueryChange,
  onSubmit,
  suggestions,
  onSuggestionClick,
  isLoading = false,
  placeholder = 'Ask one focused question',
  subtitle = 'Use a quick suggestion or write a short prompt',
  error,
  result,
}: AiInsightPanelProps): JSX.Element {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-[var(--pp-navy)] p-5 text-white shadow-[0_28px_56px_rgba(15,23,42,0.28)]">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-white/95">AI Insight</h2>
        <p className="text-xs text-white/60">{subtitle}</p>
      </div>

      <form
        className="mt-5 rounded-[1.125rem] border border-white/10 bg-white/[0.06] p-3"
        onSubmit={onSubmit}
      >
        <div className="flex items-start gap-2">
          <Input
            aria-label="Ask one question"
            className="min-h-[44px] border-white/10 bg-white/[0.04] text-sm text-white placeholder:text-white/45 focus:ring-[var(--color-primary)]"
            placeholder={placeholder}
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
          <Button
            aria-label="Generate insight"
            className="min-h-[44px] min-w-[44px] rounded-2xl px-4 text-base text-[var(--pp-navy)]"
            disabled={isLoading || !query.trim()}
            style={{ backgroundColor: canonicalBrand.blue }}
            type="submit"
          >
            {isLoading ? '…' : '➜'}
          </Button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <SuggestionChip
              key={suggestion}
              label={suggestion}
              onClick={onSuggestionClick ? () => onSuggestionClick(suggestion) : undefined}
            />
          ))}
        </div>
      </form>

      {error ? (
        <div
          role="alert"
          className="mt-4 rounded-[1.125rem] border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 p-4 text-sm text-white"
        >
          {error}
        </div>
      ) : null}

      {isLoading ? (
        <div className="mt-4 rounded-[1.125rem] border border-white/10 bg-white/[0.06] p-4">
          <div className="h-2.5 w-44 rounded-full bg-white/10" />
          <div className="mt-3 h-2.5 w-full rounded-full bg-white/10" />
          <div className="mt-3 h-2.5 w-5/6 rounded-full bg-white/10" />
        </div>
      ) : null}

      {!isLoading && result ? (
        <article className="mt-4 rounded-[1.125rem] border border-white/10 bg-white/[0.06] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-semibold text-white/95">{result.title}</p>
            <span className="rounded-full bg-[color:rgba(32,201,151,0.18)] px-3 py-1 text-[0.65rem] font-semibold text-[var(--pp-green)]">
              {result.confidenceLabel}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-white/72">{result.body}</p>
          {result.metadata && result.metadata.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {result.metadata.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[0.65rem] text-white/72"
                >
                  {item}
                </span>
              ))}
            </div>
          ) : null}
          {result.warnings && result.warnings.length > 0 ? (
            <div className="mt-4 space-y-2">
              {result.warnings.map((warning, index) => (
                <p
                  key={`${warning}-${index}`}
                  className="rounded-2xl border border-[var(--color-warning)]/25 bg-[var(--color-warning)]/10 px-3 py-2 text-xs text-white/88"
                >
                  {warning}
                </p>
              ))}
            </div>
          ) : null}
          {result.sources && result.sources.length > 0 ? (
            <div className="mt-4 space-y-2">
              {result.sources.map((source) => (
                <p
                  key={source}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white/68"
                >
                  {source}
                </p>
              ))}
            </div>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {result.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[0.65rem] text-white/55"
              >
                {tag}
              </span>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            {result.primaryActionLabel ? (
              result.onPrimaryAction ? (
                <button
                  type="button"
                  className={buttonClasses({
                    className: 'rounded-2xl px-5 text-[var(--pp-navy)]',
                  })}
                  style={{ backgroundColor: canonicalBrand.blue }}
                  onClick={result.onPrimaryAction}
                >
                  {result.primaryActionLabel}
                </button>
              ) : (
                <span
                  className="rounded-2xl border border-white/10 bg-white/[0.05] px-5 py-2 text-sm font-medium text-white/72"
                >
                  {result.primaryActionLabel}
                </span>
              )
            ) : null}
            {result.secondaryActionLabel ? (
              result.onSecondaryAction ? (
                <button
                  type="button"
                  className={buttonClasses({
                    variant: 'secondary',
                    className: 'rounded-2xl border-white/10 bg-white/[0.03] px-5 text-white hover:bg-white/[0.08]',
                  })}
                  onClick={result.onSecondaryAction}
                >
                  {result.secondaryActionLabel}
                </button>
              ) : (
                <span
                  className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-2 text-sm font-medium text-white/72"
                >
                  {result.secondaryActionLabel}
                </span>
              )
            ) : null}
          </div>
        </article>
      ) : null}
    </section>
  );
}
