import React from "react";
import { useTranslation } from "react-i18next";
import PremiumGate from "../components/PremiumGate";
import { usePremium } from "../lib/usePremium";

export default function Plate() {
  const isPremium = usePremium();
  const { t } = useTranslation();

  if (isPremium === undefined) {
    return (
      <main className="p-4">
        <h1>{t("plate.title")}</h1>
        <p>{t("common.loading")}</p>
      </main>
    );
  }

  return (
    <main className="p-4">
      <h1>{t("plate.title")}</h1>
      <PremiumGate isPremium={isPremium} source="plate_page">
        <section className="mt-4">
          <p>{t("plate.preview")}</p>
        </section>
      </PremiumGate>
    </main>
  );
}
