# RU: Простой заглушечный провайдер — без внешних зависимостей
# EN: Simple stub provider — no external deps
from datetime import datetime


class StubProvider:
    name = "stub"

    def generate(self, text: str) -> str:
        # RU: Возвращаем детерминированную "инсайт"-строку
        # EN: Return deterministic "insight" string
        ts = datetime.utcnow().isoformat(timespec="seconds")
        return f"[{self.name} @ {ts}] Insight: {text[:120]}"
