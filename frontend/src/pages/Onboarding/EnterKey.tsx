import { useContext, useState, useRef } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { useToast } from "../../components/ui/useToast";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { EyeIcon } from "../../components/icons/EyeIcon";
import { EyeOffIcon } from "../../components/icons/EyeOffIcon";

// Type-guard helper to safely extract 'from' property from location state
function extractFrom(state: unknown): string | undefined {
  if (state && typeof state === 'object' && 'from' in state && typeof (state as any).from === 'string') {
    return (state as any).from;
  }
  return undefined;
}

// Validate API key format: must start with 'sk-', be at least 20 chars, max 256 chars
function validateApiKeyFormat(apiKey: string): boolean {
  if (!apiKey) {
    return false;
  }
  return apiKey.startsWith('sk-') && apiKey.length >= 20 && apiKey.length <= 256;
}

export default function EnterKey() {
  const { apiKey, setApiKey, clearApiKey } = useContext(AuthContext);
  const [value, setValue] = useState(apiKey?.trim() ?? "");
  const [showKey, setShowKey] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const nav = useNavigate();
  const loc = useLocation();
  const from = extractFrom(loc.state);
  const { t } = useTranslation();
  const toast = useToast();

  const onSave = () => {
    const v = value.trim();
    if (!v) {
      toast.error(t("auth.invalidApiKey"));
      return;
    }
    if (!validateApiKeyFormat(v)) {
      toast.error(t("auth.invalidApiKeyFormat"));
      return;
    }
    try {
      setApiKey(v);
      toast.success(t("enterKey.saved"));
      // Automatically return to origin (if came from soft-gate)
      if (from && from !== "/enter-key") {
        nav(from, { replace: true });
      }
    } catch (error) {
      toast.error(`${t("enterKey.saveFailed")}. ${t("shoplist.tryAgain").toLowerCase()}`);
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
    requestAnimationFrame(() => inputRef.current?.focus());
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
          {showKey ? <EyeOffIcon /> : <EyeIcon />}
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
