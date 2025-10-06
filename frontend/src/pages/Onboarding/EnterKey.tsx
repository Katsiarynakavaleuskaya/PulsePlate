import { useContext, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { useToast } from "../../components/ui/useToast";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function EnterKey() {
  const { apiKey, setApiKey, clearApiKey } = useContext(AuthContext);
  const [value, setValue] = useState(apiKey?.trim() ?? "");
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  const { t } = useTranslation();

  const onSave = () => {
    const v = value.trim();
    if (!v) {
      useToast.error(t("auth.invalidApiKey"));
      return;
    }
    try {
      setApiKey(v);
      useToast.success(t("enterKey.saved"));
      // Автоматический возврат туда, откуда пришли (если был soft-гейт)
      if (from && from !== "/enter-key") {
        nav(from, { replace: true });
      }
    } catch (error) {
      useToast.error(t("enterKey.saveFailed") + ". " + t("shoplist.tryAgain").toLowerCase());
    }
  };

  const onClear = () => {
    clearApiKey();
    setValue("");
    useToast.success(t("enterKey.cleared"));
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
      <input
        type="password"
        id="x-api-key"
        className="w-full border rounded-xl p-3 mb-3"
        placeholder={t("enterKey.placeholder")}
        value={value}
        onChange={(e)=>setValue(e.target.value)}
        autoComplete="new-password"
      />
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
