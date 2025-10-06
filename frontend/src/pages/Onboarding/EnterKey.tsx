import { useContext, useState, useRef } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { useToast } from "../../components/ui/useToast";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function EnterKey() {
  const { apiKey, setApiKey, clearApiKey } = useContext(AuthContext);
  const [value, setValue] = useState(apiKey?.trim() ?? "");
  const [showKey, setShowKey] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  const { t } = useTranslation();
  const toast = useToast();

  const onSave = () => {
    const v = value.trim();
    if (!v) {
      toast.error(t("auth.invalidApiKey"));
      return;
    }
    try {
      setApiKey(v);
      toast.success(t("enterKey.saved"));
      // Автоматический возврат туда, откуда пришли (если был soft-гейт)
      if (from && from !== "/enter-key") {
        nav(from, { replace: true });
      }
    } catch (error) {
      toast.error(t("enterKey.saveFailed") + ". " + t("shoplist.tryAgain").toLowerCase());
    }
  };

  const onClear = () => {
    clearApiKey();
    setValue("");
    toast.success(t("enterKey.cleared"));
  };

  const toggleShowKey = () => {
    setShowKey(!showKey);
    // Focus back to input after state change
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  return (
    <div className="max-w-md mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-2">{t("enterKey.title")}</h1>
      <p className="text-sm text-gray-500 mb-4">
        {t("enterKey.description")}{" "}
        <a href="https://github.com/Katsiarynakavaleuskaya/PulsePlate/blob/main/README.md#feature-flags-and-auth" target="_blank" rel="noreferrer" className="text-blue-600 underline">
          README
        </a>.
      </p>
      <label htmlFor="x-api-key" className="sr-only">{t("enterKey.label")}</label>
      <div className="relative mb-3">
        <input
          type={showKey ? "text" : "password"}
          id="x-api-key"
          ref={inputRef}
          className="w-full border rounded-xl p-3 pr-12"
          placeholder={t("enterKey.placeholder")}
          value={value}
          onChange={(e)=>setValue(e.target.value)}
          autoComplete="off"
          aria-describedby="api-key-toggle"
        />
        <button
          type="button"
          onClick={toggleShowKey}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          aria-label={showKey ? t("enterKey.hideKey", "Hide API key") : t("enterKey.showKey", "Show API key")}
          aria-pressed={showKey}
          id="api-key-toggle"
        >
          {showKey ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
      <div className="flex gap-2">
        <button className="flex-1 rounded-xl py-3 bg-[#339FFF] text-white" onClick={onSave}>{t("enterKey.save")}</button>
        <button className="rounded-xl px-4 py-3 border" onClick={onClear}>{t("enterKey.clear")}</button>
      </div>
      <p className="text-xs text-gray-500 mt-3">
        {t("enterKey.footer")}
      </p>
    </div>
  );
}
