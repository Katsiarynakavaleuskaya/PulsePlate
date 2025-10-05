import { useContext, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../../auth/AuthContext";
import { useToast } from "../../components/ui/useToast";

export default function EnterKey() {
  const auth = useContext(AuthContext);
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [value, setValue] = useState(auth?.apiKey ?? "");

  const from = (location.state as { from?: string } | null)?.from;

  const handleSave = () => {
    const trimmed = value.trim();
    if (!trimmed) {
      toast.error("Введите непустой API-ключ.");
      return;
    }
    auth?.setApiKey(trimmed);
    toast.success("Ключ сохранён.");
    if (from && from !== "/enter-key") {
      navigate(from, { replace: true });
    }
  };

  const handleClear = () => {
    auth?.clearApiKey();
    setValue("");
    toast.success("Ключ удалён.");
  };

  return (
    <div className="max-w-md mx-auto p-6 space-y-4">
      <header>
        <h1 className="text-2xl font-semibold mb-2">API-ключ</h1>
        <p className="text-sm text-gray-400">
          Ключ обязателен для Premium и админ-разделов. Где взять: проверьте README → раздел API key.
        </p>
      </header>

      <div className="space-y-3">
        <input
          className="w-full border border-white/10 rounded-xl bg-white/5 p-3 text-white placeholder:text-gray-400"
          placeholder="Вставьте X-API-Key"
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
            Сохранить
          </button>
          <button
            className="rounded-xl border border-white/15 text-white py-3 px-4"
            type="button"
            onClick={handleClear}
          >
            Очистить
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Изменения применяются мгновенно. Перезагружать страницу не требуется — мы вернём вас на предыдущий экран автоматически.
        </p>
      </div>
    </div>
  );
}
