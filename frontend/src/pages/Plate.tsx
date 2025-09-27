import React from "react";
import PremiumGate from "../components/PremiumGate";

export default function Plate() {
  // Temporarily render content unguarded until premium status is wired from app state
  return (
    <main className="p-4">
      <h1>Plate</h1>
      <section className="mt-4">
        <p>Premium-only section preview…</p>
      </section>
    </main>
  );
}
