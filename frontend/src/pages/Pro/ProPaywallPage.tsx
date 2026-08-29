import { AppleProductInfoCard } from '../../components/AppleProductInfoDialog';

/**
 * Compatibility owner for the public `/pro` URL.
 *
 * The route is information-only. Legacy location state is intentionally ignored
 * so an old teaser or bookmark cannot recreate a Web purchase path.
 */
export default function ProPaywallPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[var(--color-surface)] px-4 py-10 sm:px-6 sm:py-16">
      <div className="mx-auto flex max-w-4xl justify-center">
        <AppleProductInfoCard />
      </div>
    </main>
  );
}
