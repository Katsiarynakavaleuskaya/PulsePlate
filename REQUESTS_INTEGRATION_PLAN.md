# 🌐 План интеграции requests для магазинов, ресторанов и кухонь мира

## 🎯 Цель

Использовать библиотеку `requests` для интеграции с внешними API магазинов, ресторанов и кухонь мира для автоматического наполнения базы данных продуктами.

## 📊 Текущее использование requests

### ✅ Уже используется

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

    def __init__(self, base_url: str, api_key: Optional[str] = None) -> None:
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
        raise NotImplementedError("Not implemented")

    def get_restaurant_menu(self, restaurant_id: str) -> Dict[str, Any]:
        """Получить меню ресторана"""
        raise NotImplementedError("Not implemented")

    def get_recipe_details(self, recipe_id: str) -> Dict[str, Any]:
        """Получить детали рецепта"""
        raise NotImplementedError("Not implemented")

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
from typing import List, Dict
from core.api_client import UniversalAPIClient

def daily_sync() -> None:
    """Ежедневная синхронизация с внешними API"""

    # 1. Получаем новые продукты из магазинов
    store_products: List[Dict] = sync_store_products()

    # 2. Получаем меню ресторанов
    restaurant_menus: List[Dict] = sync_restaurant_menus()

    # 3. Получаем рецепты кухонь мира
    world_recipes: List[Dict] = sync_world_recipes()

    # 4. Обрабатываем через DLT pipeline
    process_with_dlt(store_products, restaurant_menus, world_recipes)
```

### 2. **Обработка ошибок и retry**

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

def create_robust_session() -> requests.Session:
    """Создание сессии с retry логикой"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE"]),
        respect_retry_after_header=True,
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

### Этап 1: Подготовка инфраструктуры (1-2 недели)

1. **Установить зависимости**

   ```bash
   pip install beautifulsoup4 lxml html5lib requests-html selenium
   pip install dlt[postgres,parquet] duckdb
   ```

2. **Создать базовую структуру**

   ```text
   core/
   ├── api_client.py          # Универсальный API клиент
   ├── web_scrapers/
   │   ├── __init__.py
   │   ├── base_parser.py     # Базовый класс парсера
   │   ├── store_parsers.py   # Парсеры магазинов
   │   ├── restaurant_parsers.py  # Парсеры ресторанов
   │   ├── recipe_parsers.py  # Парсеры рецептов
   │   ├── robots_checker.py  # Проверка robots.txt
   │   └── polite_scraper.py  # Вежливый скрапинг
   ```

3. **Настроить DLT pipeline**

   ```text
   dlt_pipelines/
   ├── sources/
   │   ├── api_sources.py     # API источники
   │   └── scraping_sources.py # Веб-скрапинг источники
   ├── transforms/
   │   ├── data_cleaner.py    # Очистка данных
   │   └── data_validator.py  # Валидация
   └── pipelines/
       ├── daily_sync.py      # Ежедневная синхронизация
       └── incremental_update.py # Инкрементальные обновления
   ```

### Этап 2: API интеграция (2-3 недели)

1. **Создать универсальный API клиент** (`core/api_client.py`)
   - Поддержка retry логики
   - Rate limiting
   - Кэширование
   - Обработка ошибок

2. **Интегрировать основные API**
   - **Магазины**: Walmart, Target, Kroger (США)
   - **Рестораны**: UberEats, DoorDash, Grubhub
   - **Кулинария**: Spoonacular, Edamam, ThemealDB

3. **Добавить региональные API**
   - **Россия**: Yandex.Eda, Delivery Club, SberMarket
   - **Европа**: Deliveroo, Just Eat, Carrefour
   - **Азия**: Grab, Foodpanda, Meituan

### Этап 3: Веб-скрапинг (3-4 недели)

1. **Создать базовые парсеры**
   - Парсер продуктов для популярных магазинов
   - Парсер меню ресторанов
   - Парсер рецептов с кулинарных сайтов

2. **Реализовать вежливый скрапинг**
   - Соблюдение robots.txt
   - Rate limiting (1-3 секунды между запросами)
   - Случайные задержки
   - User-Agent ротация

3. **Добавить обработку JavaScript**
   - Selenium для динамических сайтов
   - requests-html для простых случаев
   - Кэширование рендеринга

### Этап 4: ETL Pipeline (2-3 недели)

1. **Настроить DLT pipeline**
   - Источники данных (API + скрапинг)
   - Трансформации (очистка, нормализация)
   - Загрузка в PostgreSQL

2. **Создать систему мониторинга**
   - Логирование всех операций
   - Алерты при ошибках
   - Метрики производительности

3. **Настроить инкрементальные обновления**
   - Отслеживание изменений
   - Обновление только новых/измененных данных
   - Очистка устаревших записей

### Этап 5: Качество данных (2 недели)

1. **Валидация и очистка**
   - Проверка nutritional данных
   - Нормализация единиц измерения
   - Дедупликация продуктов
   - Контроль качества

2. **Создать dashboard**
   - Статистика по источникам
   - Качество данных
   - Производительность скрапинга
   - Ошибки и алерты

### Этап 6: Масштабирование (ongoing)

1. **Оптимизация производительности**
   - Асинхронный скрапинг
   - Параллельная обработка
   - Кэширование результатов

2. **Расширение источников**
   - Новые магазины и рестораны
   - Специализированные кулинарные сайты
   - Региональные источники

## 📋 Детальный план действий

### Неделя 1-2: Инфраструктура

- [ ] Установить все зависимости
- [ ] Создать базовую структуру папок
- [ ] Настроить DLT pipeline
- [ ] Создать базовые классы парсеров

### Неделя 3-4: API интеграция

- [ ] Реализовать UniversalAPIClient
- [ ] Интегрировать 3-5 основных API
- [ ] Добавить обработку ошибок и retry
- [ ] Создать тесты для API клиентов

### Неделя 5-6: Веб-скрапинг

- [ ] Создать парсеры для 5-10 популярных сайтов
- [ ] Реализовать robots.txt проверку
- [ ] Добавить rate limiting и вежливый скрапинг
- [ ] Создать систему мониторинга скрапинга

### Неделя 7-8: ETL Pipeline

- [ ] Настроить DLT sources для всех источников
- [ ] Создать трансформации данных
- [ ] Реализовать инкрементальные обновления
- [ ] Добавить валидацию и очистку данных

### Неделя 9-10: Качество и мониторинг

- [ ] Создать dashboard для мониторинга
- [ ] Добавить алерты и уведомления
- [ ] Реализовать систему контроля качества
- [ ] Создать документацию

## 🛠️ Технические требования

### Зависимости

#### Веб-скрапинг

beautifulsoup4==4.12.3
lxml==5.1.0
html5lib==1.1
requests-html==0.10.0
selenium==4.16.0

#### ETL Pipeline

dlt[postgres,parquet]==0.5.2
duckdb==0.10.0

#### Мониторинг

prometheus-client==0.20.0
grafana-api==1.0.3

#### Кэширование

redis==5.0.1
requests-cache==1.2.0

### Конфигурация

```yaml
# config/scraping.yaml
scraping:
  rate_limit:
    min_delay: 1.0
    max_delay: 3.0
  user_agents:
    - "Mozilla/5.0 (compatible; PulsePlate/1.0)"
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  robots_check: true
  cache_ttl: 3600

sources:
  stores:
    - name: "walmart"
      base_url: "https://www.walmart.com"
      api_key: "${WALMART_API_KEY}"
    - name: "target"
      base_url: "https://www.target.com"
      api_key: "${TARGET_API_KEY}"

  restaurants:
    - name: "ubereats"
      base_url: "https://www.ubereats.com"
      api_key: "${UBEREATS_API_KEY}"
```

## 📊 Ожидаемые результаты

### Количество данных

- **Продукты**: 1M+ записей из магазинов
- **Рецепты**: 100K+ рецептов из кулинарных сайтов
- **Меню**: 50K+ блюд из ресторанов
- **Обновления**: Ежедневно 10K+ новых записей

### Качество данных

- **Актуальность**: Цены обновляются ежедневно
- **Полнота**: 90%+ продуктов с nutritional информацией
- **Точность**: 95%+ валидных данных после очистки

### Производительность

- **Скорость**: 1000+ запросов в час
- **Надежность**: 99%+ успешных запросов
- **Масштабируемость**: Поддержка 100+ источников

## 💰 Экономический эффект

- **Экономия времени**: Автоматизация vs ручное наполнение
- **Качество данных**: Актуальные цены и наличие
- **Масштаб**: Миллионы продуктов vs тысячи
- **Локализация**: Поддержка разных регионов и валют

---

**Вывод**: `requests` критически важен для масштабирования проекта и интеграции с внешними источниками данных!
