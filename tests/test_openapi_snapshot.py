# RU: Снапшот OpenAPI — защищаем контракт для фронтенда.
# EN: OpenAPI snapshot to guard the frontend contract.

from pathlib import Path
import json

try:
    # Пытаемся импортировать приложение (поддержим два варианта именования)
    from app import app  # type: ignore
except Exception:  # pragma: no cover - fallback only for alternate entrypoint
    from main import app  # type: ignore

from fastapi.testclient import TestClient


def test_openapi_schema_snapshot():
    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    snap_path = Path("app/static/openapi.json")
    snap_path.parent.mkdir(parents=True, exist_ok=True)

    if not snap_path.exists():
        # Первый прогон — зафиксировали эталон (сознательный шаг).
        snap_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
        # Подсказываем обновить снапшот намеренно, если так и должно быть.
        assert True
    else:
        baseline = json.loads(snap_path.read_text(encoding="utf-8"))
        assert schema == baseline, (
            "OpenAPI changed. If это намеренно — обнови снапшот:\n"
            "  1) пересоздай app/static/openapi.json\n"
            "  2) прокоммить как conscious API change."
        )
