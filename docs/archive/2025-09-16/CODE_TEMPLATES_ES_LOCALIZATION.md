# 🧩 Готовые заготовки кода для ES-локализации

## 1️⃣ Snapshot-тесты ES

### Файл: `tests/test_premium_targets_i18n_es.py`

```python
# -*- coding: utf-8 -*-
"""
RU: Снапшот-тест локализации ES для /api/v1/premium/targets.
EN: Snapshot test for ES localization of /api/v1/premium/targets.
"""
import json
import pytest

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

from fastapi.testclient import TestClient
client = TestClient(app_mod.app)  # type: ignore

@pytest.mark.parametrize("sex", ["female", "male"])
def test_premium_targets_es_snapshot(sex, snapshot):
    payload = {
        "sex": sex,
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "lang": "es",
    }
    resp = client.post("/api/v1/premium/targets", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Мини-контракт: ключевые поля и локализация предупреждений.
    assert "micros" in data and "macros" in data
    assert "warnings" in data and isinstance(data["warnings"], list)

    # Отфильтруем динамические поля, чтобы снапшот был стабильным.
    stable = {
        "lang": data.get("lang"),
        "required_micros": sorted([k for k in data["micros"].keys()
                                   if k in {"iron_mg","calcium_mg","vitamin_d_iu","folate_µg","iodine_µg","magnesium_mg","potassium_mg","vitamin_b12_µg"}]),
        "warnings": sorted([w.get("code", "") for w in data["warnings"]]),
        "ui_labels": data.get("ui_labels", {}),  # если есть словарь UI-строк
    }
    snapshot.assert_match(json.dumps(stable, ensure_ascii=False, indent=2))
```

## 2️⃣ Warnings по life_stage (+локализация)

### Бэкенд: `core/targets.py` (или соответствующий слой)

```python
# RU: Пример добавления варнингов по жизненным этапам (с локализацией).
# EN: Example of adding life-stage warnings with localization.

from typing import List, Dict

def _life_stage_warnings(age: int, pregnant: bool, lang: str) -> List[Dict[str, str]]:
    # Примеры локализованных сообщений.
    M = {
        "teen": {
            "ru": "Подростковая группа: используйте специализированные нормы.",
            "en": "Teen life stage: use age-appropriate references.",
            "es": "Etapa adolescente: use referencias apropiadas para la edad.",
        },
        "pregnant": {
            "ru": "Беременность: нормы отличаются; обратитесь к специализированным рекомендациям.",
            "en": "Pregnancy: requirements differ; consult specialized guidelines.",
            "es": "Embarazo: los requisitos difieren; consulte guías especializadas.",
        },
        "51plus": {
            "ru": "51+: возможна иная потребность в микронутриентах.",
            "en": "Age 51+: micronutrient needs may differ.",
            "es": "51+: las necesidades de micronutrientes pueden diferir.",
        },
    }
    codes = []
    if 12 <= age <= 18: codes.append("teen")
    if pregnant: codes.append("pregnant")
    if age >= 51: codes.append("51plus")

    res = []
    for c in codes:
        res.append({"code": c, "message": M[c].get(lang, M[c]["en"])})
    return res
```

### Тест: `tests/test_premium_targets_lifestage.py`

```python
# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient
import app as app_mod  # type: ignore

client = TestClient(app_mod.app)  # type: ignore

@pytest.mark.parametrize("case", [
    {"age": 16, "pregnant": False, "code": "teen"},
    {"age": 30, "pregnant": True,  "code": "pregnant"},
    {"age": 55, "pregnant": False, "code": "51plus"},
])
@pytest.mark.parametrize("lang", ["ru", "en", "es"])
def test_life_stage_warnings(case, lang):
    payload = {
        "sex": "female",
        "age": case["age"],
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "light",
        "goal": "maintain",
        "lang": lang,
        "pregnant": case["pregnant"],
    }
    resp = client.post("/api/v1/premium/targets", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    codes = [w.get("code") for w in data.get("warnings", [])]
    assert case["code"] in codes
```

## 3️⃣ Негативные кейсы (422)

### Файл: `tests/test_premium_targets_422.py`

```python
# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient
import app as app_mod  # type: ignore
client = TestClient(app_mod.app)  # type: ignore

@pytest.mark.parametrize("bad", [
    {"sex": "unknown"},          # invalid enum
    {"activity": "hyper-ultra"}, # invalid enum
    {"goal": "explode"},         # invalid enum
    {"lang": "xx"},              # invalid locale
])
def test_invalid_payload_422(bad):
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "lang": "es",
    }
    payload.update(bad)
    resp = client.post("/api/v1/premium/targets", json=payload)
    assert resp.status_code == 422
```

## 4️⃣ Интеграция Plate→Targets (Fe/Ca/Mg/K покрытие)

### Файл: `tests/test_plate_coverage_integration.py`

```python
# -*- coding: utf-8 -*-
"""
RU: Интеграционный тест: строим таргеты, генерим Plate и сверяем проценты покрытия Fe/Ca/Mg/K.
EN: Integration test: build targets, generate Plate, check Fe/Ca/Mg/K coverage.
"""
from fastapi.testclient import TestClient
import pytest
import app as app_mod  # type: ignore

client = TestClient(app_mod.app)  # type: ignore

def _coverage(micros: dict, targets: dict, key: str) -> float:
    # RU: Простая доля покрытия (0..1), защищаемся от деления на ноль.
    # EN: Simple coverage share (0..1), safeguard division by zero.
    t = float(targets.get(key, 0.0)) or 1.0
    v = float(micros.get(key, 0.0))
    return min(v / t, 10.0)

@pytest.mark.skipif(not hasattr(app_mod, "app"), reason="App missing")  # safety
def test_plate_coverage_basic():
    # 1) Таргеты
    req = {
        "sex": "female",
        "age": 30,
        "height_cm": 170,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "lang": "en",
    }
    t_resp = client.post("/api/v1/premium/targets", json=req)
    assert t_resp.status_code == 200
    targets = t_resp.json()["micros"]

    # 2) Генерим Plate на день (минимальный контракт роутера)
    p_resp = client.post("/api/v1/premium/plate", json={**req, "calorie_budget": 2000})
    assert p_resp.status_code == 200
    plate = p_resp.json()
    day_micros = plate.get("day_micros", {})  # ожидается, что бэкенд агрегирует микросы

    for k in ["iron_mg", "calcium_mg", "magnesium_mg", "potassium_mg"]:
        cov = _coverage(day_micros, targets, k)
        assert cov >= 0.3  # базовая разумная нижняя граница для MVP (подкрутим по факту)
```

## 5️⃣ Docs: Sources & Units (+ES пример)

### Файл: `docs/PREMIUM_TARGETS_API.md` (или README.md, секция)

```markdown
### Sources & Units
- WHO/FAO/UNU & EFSA references consolidated in `rules_who.py`
- Vitamin D: 1 µg = 40 IU. Field `vitamin_d_iu` shown for compatibility; convert as needed.
- Life stage notes: teen / pregnancy / 51+ produce `warnings` with localized messages (RU/EN/ES).

**ES Example**
```bash
curl -s http://localhost:8000/api/v1/premium/targets \
  -H "Content-Type: application/json" \
  -d '{
    "sex":"female","age":30,"height_cm":170,"weight_kg":65,
    "activity":"moderate","goal":"maintain","lang":"es"
  }' | jq
```

## 📋 Команды для тестирования

```bash
# Локально:
uv run pytest -q
uv run pytest tests/test_premium_targets_i18n_es.py -q
uv run pytest tests/test_premium_targets_lifestage.py -q
uv run pytest tests/test_premium_targets_422.py -q
uv run pytest tests/test_plate_coverage_integration.py -q

# Проверка покрытия:
pytest --cov=. --cov-report=term-missing
```

## 🔒 Security Notes

- Валидация входных данных (Pydantic) обязательна для всех новых полей (pregnant, lang)
- Не логировать персональные данные; в логах — только коды варнингов/категории
- Rate limiting для /premium/plate (защитить от "перебора" рецептов)
- Фиксировать версию библиотек и гонять safety/bandit
