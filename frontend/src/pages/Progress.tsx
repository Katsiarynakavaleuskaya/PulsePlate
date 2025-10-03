import { useTranslation } from "react-i18next";

export default function Progress() {
  const { t } = useTranslation();

  return (
    <main className="p-4">
      <h1>{t("progress.title")}</h1>
      <p>{t("common.skeleton")}</p>
    </main>
  );
}
