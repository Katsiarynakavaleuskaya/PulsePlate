import PremiumGate from "../components/PremiumGate";
import { usePremium } from "../lib/usePremium";
import { PREMIUM_GATE_SOURCES } from "../config/constants";

export default function Plate() {
  const isPremium = usePremium();

  if (isPremium === undefined) {
    return (
      <main className="p-4">
        <h1>Plate</h1>
        <p>Loading…</p>
      </main>
    );
  }

  return (
    <main className="p-4">
      <h1>Plate</h1>
      <PremiumGate isPremium={isPremium} source={PREMIUM_GATE_SOURCES.PLATE_PAGE}>
        <section className="mt-4">
          <p>Premium-only section preview…</p>
        </section>
      </PremiumGate>
    </main>
  );
}
