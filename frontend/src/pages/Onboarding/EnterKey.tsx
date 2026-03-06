import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth, AuthError } from "../../lib/auth";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

interface LocationState {
  from?: {
    pathname: string;
  };
}

export default function EnterKey() {
  const { t } = useTranslation();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [value, setValue] = useState("");

  // Get the page user was trying to access
  const from = (location.state as LocationState)?.from?.pathname || "/";

  const handleSave = async () => {
    const trimmed = value.trim();
    if (!trimmed) {
      toast.error(t("onboarding.enterKey.errorEmpty"));
      return;
    }
    try {
      await auth.setApiKey(trimmed, true);
      toast.success(t("onboarding.enterKey.successSaved"));
      if (from && from !== "/enter-key" && from !== "/") {
        navigate(from, { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    } catch (error) {
      let errorMessage = t("onboarding.enterKey.errorGeneric");
      if (error instanceof AuthError) {
        if (error.code === 'API_KEY_TOO_SHORT') {
          errorMessage = t("auth.apiKey.tooShort");
        } else if (error.code === 'API_KEY_INVALID_FORMAT') {
          errorMessage = t("auth.apiKey.invalidFormat");
        }
      }
      toast.error(errorMessage);
    }
  };

  const handleClear = async () => {
    const hadKey = auth.isAuthenticated || !!value.trim();
    await auth.clearApiKey();
    setValue("");
    if (hadKey) {
      toast.success(t("onboarding.enterKey.keyCleared"));
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 space-y-4">
      <header>
        <h1 className="text-2xl font-semibold mb-2">{t("onboarding.enterKey.title")}</h1>
        <p className="text-sm text-gray-400">
          {t("onboarding.enterKey.description")}
        </p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void handleSave();
        }}
      >
        <div className="space-y-3">
          <label htmlFor="api-key-input" className="sr-only">
            {t("onboarding.enterKey.label")}
          </label>
          <input
            id="api-key-input"
            className="w-full border border-white/10 rounded-xl bg-white/5 p-3 text-white placeholder:text-gray-400"
            placeholder={t("onboarding.enterKey.placeholder")}
            value={value}
            autoComplete="off"
            onChange={(event) => setValue(event.target.value)}
          />

          <div className="flex gap-3">
            <button
              className="flex-1 rounded-xl bg-blue-600 text-white py-3 px-4 font-medium"
              type="submit"
            >
              {t("onboarding.enterKey.save")}
            </button>
            <button
              className="rounded-xl border border-white/15 text-white py-3 px-4"
              type="button"
              onClick={() => {
                void handleClear();
              }}
            >
              {t("onboarding.enterKey.clear")}
            </button>
          </div>
        </div>
      </form>
      <p className="text-xs text-gray-500">
        {t("onboarding.enterKey.changesNote")}
      </p>
    </div>
  );
}
