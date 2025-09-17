# RU: Простой заглушечный провайдер — без внешних зависимостей
# EN: Simple stub provider — no external deps
from datetime import UTC, datetime

from core.time_utils import isoformat_utc


class StubProvider:
    name = "stub"

    def generate(self, text: str) -> str:
        # RU: Возвращаем детерминированную "инсайт"-строку
        # EN: Return deterministic "insight" string
        ts = isoformat_utc(datetime.now(UTC).replace(microsecond=0))
        return f"[{self.name} @ {ts}] Insight: {text[:120]}"
