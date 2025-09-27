import PremiumGate from "../components/PremiumGate";

export default function Plate() {
  const isPremium = false; // TODO: wire with real premium state/store
  return (
    <main className="p-4">
      <h1>Plate</h1>
      <PremiumGate isPremium={isPremium} source="plate">
        <section className="mt-4">
          <p>Premium-only section preview…</p>
        </section>
      </PremiumGate>
    </main>
  );
}
