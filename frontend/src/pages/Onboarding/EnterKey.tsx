import { useContext, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../../auth/AuthContext";
import { useToast } from "../../components/ui/useToast";

import { useTranslation } from "react-i18next";

export default function EnterKey() {
  const { t } = useTranslation();
  const auth = useContext(AuthContext);
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [value, setValue] = useState(auth?.apiKey ?? "");

  const from = (location.state as { from?: string } | null)?.from;

  const handleSave = () => {
    const trimmed = value.trim();
    if (!trimmed) {
      toast.error(t("onboarding.enterKey.errorEmpty"));
      return;
    }
    auth?.setApiKey(trimmed);
    toast.success(t("onboarding.enterKey.successSaved"));
    if (from && from !== "/enter-key") {
      navigate(from, { replace: true });
    }
  };

  const handleClear = () => {
    auth?.clearApiKey();
    setValue("");
    toast.success(t("onboarding.enterKey.keyCleared"));
  };

  return (
    <div className="max-w-md mx-auto p-6 space-y-4">
      <header>
        <h1 className="text-2xl font-semibold mb-2">{t("onboarding.enterKey.title")}</h1>
        <p className="text-sm text-gray-400">
          {t("onboarding.enterKey.description")}
        </p>
      </header>

      <div className="space-y-3">
        <input
          className="w-full border border-white/10 rounded-xl bg-white/5 p-3 text-white placeholder:text-gray-400"
          placeholder={t("onboarding.enterKey.placeholder")}
          value={value}
          autoComplete="off"
          onChange={(event) => setValue(event.target.value)}
        />
        <div className="flex gap-2">
          <button
            className="flex-1 rounded-xl bg-[#339FFF] text-white py-3"
            type="button"
            onClick={handleSave}
          >
            {t("onboarding.enterKey.save")}
          </button>
          <button
            className="rounded-xl border border-white/15 text-white py-3 px-4"
            type="button"
            onClick={handleClear}
          >
            {t("onboarding.enterKey.clear")}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          {t("onboarding.enterKey.changesNote")}
        </p>
      </div>
    </div>
  );
}
