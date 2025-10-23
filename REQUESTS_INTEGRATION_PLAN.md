# 🌐 План интеграции requests для магазинов, ресторанов и кухонь мира

## 🎯 Цель

Использовать библиотеку `requests` для интеграции с внешними API магазинов, ресторанов и кухонь мира для автоматического наполнения базы данных продуктами.

## 📊 Текущее использование requests

### ✅ Уже используется:
- **`example_nutrition_api.py`** - тестирование Premium BMR/TDEE API
- **`DLT_INTEGRATION_PLAN.md`** - план интеграции с USDA FDC и OpenFoodFacts

## 🏪 Планируемые интеграции

### 1. **Магазины продуктов**
```python
# Примеры API для интеграции
STORE_APIS = {
    "walmart": "https://developer.walmartlabs.com/",
    "target": "https://developer.target.com/",
    "kroger": "https://developer.kroger.com/",
    "sainsburys": "https://developer.sainsburys.co.uk/",
    "tesco": "https://developer.tesco.com/",
    "carrefour": "https://developer.carrefour.com/",
    "auchan": "https://developer.auchan.com/",
}
```

### 2. **Рестораны и доставка еды**
```python
RESTAURANT_APIS = {
    "ubereats": "https://developer.ubereats.com/",
    "doordash": "https://developer.doordash.com/",
    "grubhub": "https://developer.grubhub.com/",
    "deliveroo": "https://developer.deliveroo.com/",
    "just_eat": "https://developer.just-eat.com/",
    "yandex_eda": "https://developer.yandex.ru/eda/",
}
```

### 3. **Кухни мира - специализированные API**
```python
CUISINE_APIS = {
    "spoonacular": "https://spoonacular.com/food-api",
    "edamam": "https://developer.edamam.com/",
    "recipe_puppy": "http://www.recipepuppy.com/about/api/",
    "food2fork": "https://www.food2fork.com/about/api",
    "themealdb": "https://www.themealdb.com/api.php",
    "chinese_cuisine": "https://api.chinese-cuisine.com/",
    "indian_cuisine": "https://api.indian-cuisine.com/",
    "mexican_cuisine": "https://api.mexican-cuisine.com/",
}
```

## 🔧 Архитектура интеграции

### 1. **Создание универсального API клиента**
```python
# core/api_client.py
import requests
from typing import Dict, Any, Optional
import logging

class UniversalAPIClient:
    """Универсальный клиент для интеграции с внешними API"""

    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PulsePlate/1.0',
            'Accept': 'application/json',
        })
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

    def get_products(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """Получить продукты по запросу"""
        pass

    def get_restaurant_menu(self, restaurant_id: str) -> Dict[str, Any]:
        """Получить меню ресторана"""
        pass

    def get_recipe_details(self, recipe_id: str) -> Dict[str, Any]:
        """Получить детали рецепта"""
        pass
```

### 2. **Интеграция с DLT для ETL**
```python
# dlt_pipelines/sources/store_apis_source.py
import dlt
import requests
from typing import Iterator, Dict, Any

@dlt.source
def store_apis_source(api_configs: Dict[str, Dict[str, str]]):
    """DLT source для магазинов"""

    @dlt.resource(name="products", write_disposition="merge")
    def get_products() -> Iterator[Dict[str, Any]]:
        for store_name, config in api_configs.items():
            client = UniversalAPIClient(
                base_url=config['base_url'],
                api_key=config['api_key']
            )

            # Получаем продукты
            products = client.get_products(query="nutrition", limit=1000)

            for product in products:
                yield {
                    'store': store_name,
                    'product_id': product['id'],
                    'name': product['name'],
                    'nutrition': product['nutrition'],
                    'price': product['price'],
                    'source': 'store_api',
                    'updated_at': dlt.current_timestamp()
                }

    return get_products()
```

## 🌍 Региональные особенности

### 1. **Россия и СНГ**
```python
RUSSIAN_APIS = {
    "yandex_eda": "https://developer.yandex.ru/eda/",
    "delivery_club": "https://developer.delivery-club.ru/",
    "sbermarket": "https://developer.sbermarket.ru/",
    "ozon": "https://developer.ozon.ru/",
    "wildberries": "https://developer.wildberries.ru/",
}
```

### 2. **Европа**
```python
EUROPEAN_APIS = {
    "deliveroo": "https://developer.deliveroo.com/",
    "just_eat": "https://developer.just-eat.com/",
    "ubereats_eu": "https://developer.ubereats.com/eu/",
    "carrefour": "https://developer.carrefour.com/",
    "auchan": "https://developer.auchan.com/",
}
```

### 3. **Азия**
```python
ASIAN_APIS = {
    "grab": "https://developer.grab.com/",
    "foodpanda": "https://developer.foodpanda.com/",
    "meituan": "https://developer.meituan.com/",
    "eleme": "https://developer.ele.me/",
}
```

## 🔄 Workflow интеграции

### 1. **Ежедневное обновление**
```python
# scripts/daily_sync.py
import requests
from core.api_client import UniversalAPIClient

def daily_sync():
    """Ежедневная синхронизация с внешними API"""

    # 1. Получаем новые продукты из магазинов
    store_products = sync_store_products()

    # 2. Получаем меню ресторанов
    restaurant_menus = sync_restaurant_menus()

    # 3. Получаем рецепты кухонь мира
    world_recipes = sync_world_recipes()

    # 4. Обрабатываем через DLT pipeline
    process_with_dlt(store_products, restaurant_menus, world_recipes)
```

### 2. **Обработка ошибок и retry**
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_robust_session():
    """Создание сессии с retry логикой"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
```

## 📈 Преимущества requests для проекта

### 1. **Автоматическое наполнение БД**
- ✅ Миллионы продуктов из магазинов
- ✅ Меню ресторанов в реальном времени
- ✅ Рецепты кухонь мира
- ✅ Актуальные цены и наличие

### 2. **Масштабируемость**
- ✅ Асинхронные запросы с `requests-futures`
- ✅ Кэширование с `requests-cache`
- ✅ Rate limiting и retry логика
- ✅ Мониторинг API лимитов

### 3. **Качество данных**
- ✅ Валидация nutrition данных
- ✅ Нормализация единиц измерения
- ✅ Дедупликация продуктов
- ✅ Контроль качества

## 🚀 Следующие шаги

1. **Создать универсальный API клиент** (`core/api_client.py`)
2. **Интегрировать с DLT pipeline** для ETL
3. **Добавить региональные API** (Россия, Европа, Азия)
4. **Настроить мониторинг** и алерты
5. **Создать dashboard** для отслеживания интеграций

## 💰 Экономический эффект

- **Экономия времени**: Автоматизация vs ручное наполнение
- **Качество данных**: Актуальные цены и наличие
- **Масштаб**: Миллионы продуктов vs тысячи
- **Локализация**: Поддержка разных регионов и валют

---

**Вывод**: `requests` критически важен для масштабирования проекта и интеграции с внешними источниками данных!
