import { useContext, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { useLocation, useNavigate } from "react-router-dom";

export default function EnterKey() {
  const { apiKey, setApiKey, clearApiKey } = useContext(AuthContext);
  const [value, setValue] = useState(apiKey ?? "");
  const toast = useToast();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;

  const onSave = () => {
    const v = value.trim();
    if (!v) {
      toast.error("Введите непустой API-ключ.");
      return;
    }
    setApiKey(v);
    toast.success("Ключ сохранён.");
    // Автоматический возврат туда, откуда пришли (если был soft-гейт)
    if (from && from !== "/enter-key") nav(from, { replace: true });
  };

  const onClear = () => {
    clearApiKey();
    setValue("");
    toast.success("Ключ удалён.");
  };

  return (
    <div className="max-w-md mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-2">API-ключ</h1>
      <p className="text-sm text-gray-500 mb-4">
        Ключ обязателен для работы Premium-функций. Где взять: см.{" "}
        <a href="https://github.com/…/README.md#api-key" target="_blank" rel="noreferrer" className="text-blue-600 underline">
          README
        </a>.
      </p>
      <input
        className="w-full border rounded-xl p-3 mb-3"
        placeholder="Вставьте X-API-Key"
        value={value}
        onChange={(e)=>setValue(e.target.value)}
        autoComplete="off"
      />
      <div className="flex gap-2">
        <button className="flex-1 rounded-xl py-3 bg-[#339FFF] text-white" onClick={onSave}>Сохранить</button>
        <button className="rounded-xl px-4 py-3 border" onClick={onClear}>Очистить</button>
      </div>
      <p className="text-xs text-gray-500 mt-3">
        Изменение ключа применяется сразу. Перезагрузка VIP/админ-страниц не требуется — вернём вас автоматически на предыдущий экран.
      </p>
    </div>
  );
}
