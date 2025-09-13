# 📊 План интеграции DLT (Data Load Tool) в BMI-App проект

## 🎯 Цель
Автоматизировать ETL pipeline для nutrition данных используя **DLT** - современный Python фреймворк для data loading.

## 📋 Текущее состояние данных

### Существующие источники:
- **`data/food_db.csv`** - 19 локальных продуктов (RU/EN)
- **`external/usda_fdc_sample.csv`** - 12 USDA продуктов
- **`external/off_products_sample.csv`** - OpenFoodFacts продукты
- **Перспектива**: Миллионы записей из USDA FDC + OFF

### Структура данных:
```csv
name,group,per_g,kcal,protein_g,fat_g,carbs_g,fiber_g,Fe_mg,Ca_mg,VitD_IU,B12_ug,Folate_ug,Iodine_ug,K_mg,Mg_mg,flags,price,source,version_date
```

## 🚀 DLT Integration План

### 1. Установка и настройка DLT

```bash
# Добавить в requirements.txt
dlt[postgres,parquet]>=0.5.0
duckdb>=0.9.0
```

### 2. Создание DLT pipeline структуры

```
dlt_pipelines/
├── __init__.py
├── nutrition_sources/
│   ├── __init__.py
│   ├── usda_fdc_source.py      # USDA FDC API connector
│   ├── openfoodfacts_source.py # OpenFoodFacts API connector
│   └── local_csv_source.py     # Локальные CSV источники
├── transforms/
│   ├── __init__.py
│   ├── nutrition_normalizer.py # Нормализация nutrition данных
│   └── quality_checks.py       # Валидация качества данных
└── pipelines/
    ├── __init__.py
    ├── nutrition_etl.py        # Главный ETL pipeline
    └── incremental_updates.py  # Инкрементальные обновления
```

### 3. USDA FDC Source с DLT

```python
# dlt_pipelines/nutrition_sources/usda_fdc_source.py
import dlt
from dlt.sources.helpers import requests

@dlt.source
def usda_fdc_source(api_key: str = dlt.secrets.value):
    """DLT source для USDA FDC API"""

    @dlt.resource(
        table_name="usda_foods",
        write_disposition="merge",
        primary_key="fdc_id"
    )
    def foods():
        # Загрузка продуктов из USDA FDC
        base_url = "https://api.nal.usda.gov/fdc/v1"

        # Пагинация через DLT
        page = 1
        page_size = 1000

        while True:
            response = requests.get(
                f"{base_url}/foods/search",
                params={
                    "api_key": api_key,
                    "query": "*",
                    "pageSize": page_size,
                    "pageNumber": page,
                    "dataType": ["SR Legacy", "Foundation"]
                }
            )

            data = response.json()
            foods_data = data.get("foods", [])

            if not foods_data:
                break

            for food in foods_data:
                yield {
                    "fdc_id": food["fdcId"],
                    "description": food["description"],
                    "food_category": food.get("foodCategory"),
                    "nutrients": food.get("foodNutrients", []),
                    "publication_date": food.get("publicationDate"),
                    "data_type": food.get("dataType"),
                    "brand_owner": food.get("brandOwner"),
                    "ingredients": food.get("ingredients"),
                    "modified_date": food.get("modifiedDate"),
                }

            page += 1

    @dlt.resource(
        table_name="usda_nutrients",
        write_disposition="merge",
        primary_key=["fdc_id", "nutrient_id"]
    )
    def nutrients():
        # Детальная информация о нутриентах
        # Будет заполняться из foods() через transform
        pass

    return foods, nutrients
```

### 4. OpenFoodFacts Source с DLT

```python
# dlt_pipelines/nutrition_sources/openfoodfacts_source.py
import dlt
from dlt.sources.helpers import requests

@dlt.source
def openfoodfacts_source():
    """DLT source для OpenFoodFacts API"""

    @dlt.resource(
        table_name="off_products",
        write_disposition="merge",
        primary_key="code"
    )
    def products():
        base_url = "https://world.openfoodfacts.org/api/v2"

        # Категории продуктов для загрузки
        categories = [
            "en:meats", "en:fish", "en:dairy-products",
            "en:cereals-and-potatoes", "en:fruits-and-vegetables",
            "en:nuts", "en:plant-based-foods"
        ]

        for category in categories:
            page = 1
            while True:
                response = requests.get(
                    f"{base_url}/search",
                    params={
                        "categories_tags": category,
                        "page": page,
                        "page_size": 100,
                        "json": True,
                        "fields": "code,product_name,nutriments,categories,ingredients_text,brands,countries,last_modified_t"
                    }
                )

                data = response.json()
                products_data = data.get("products", [])

                if not products_data:
                    break

                for product in products_data:
                    nutrients = product.get("nutriments", {})

                    yield {
                        "code": product.get("code"),
                        "product_name": product.get("product_name"),
                        "brands": product.get("brands"),
                        "categories": product.get("categories"),
                        "ingredients_text": product.get("ingredients_text"),
                        "countries": product.get("countries"),
                        "energy_kcal_100g": nutrients.get("energy-kcal_100g"),
                        "proteins_100g": nutrients.get("proteins_100g"),
                        "fat_100g": nutrients.get("fat_100g"),
                        "carbohydrates_100g": nutrients.get("carbohydrates_100g"),
                        "fiber_100g": nutrients.get("fiber_100g"),
                        "salt_100g": nutrients.get("salt_100g"),
                        "sodium_100g": nutrients.get("sodium_100g"),
                        "last_modified_t": product.get("last_modified_t"),
                        "extraction_date": dlt.common.pendulum.now().isoformat()
                    }

                page += 1

    return products
```

### 5. Главный ETL Pipeline

```python
# dlt_pipelines/pipelines/nutrition_etl.py
import dlt
from ..nutrition_sources.usda_fdc_source import usda_fdc_source
from ..nutrition_sources.openfoodfacts_source import openfoodfacts_source
from ..transforms.nutrition_normalizer import normalize_nutrition_data

@dlt.pipeline(
    pipeline_name="nutrition_etl",
    destination="duckdb",
    dataset_name="nutrition_db"
)
def nutrition_pipeline():
    """Главный nutrition ETL pipeline"""

    # 1. Загружаем данные из источников
    usda_data = usda_fdc_source()
    off_data = openfoodfacts_source()

    # 2. Нормализуем и трансформируем
    normalized_usda = usda_data | normalize_nutrition_data("usda")
    normalized_off = off_data | normalize_nutrition_data("off")

    # 3. Загружаем в destination
    load_info = dlt.run([normalized_usda, normalized_off])

    return load_info

if __name__ == "__main__":
    load_info = nutrition_pipeline()
    print(f"Pipeline completed: {load_info}")
```

### 6. Трансформации данных

```python
# dlt_pipelines/transforms/nutrition_normalizer.py
import dlt
from typing import Iterator, Dict, Any

@dlt.transformer(
    table_name="normalized_foods",
    write_disposition="merge"
)
def normalize_nutrition_data(source_type: str):
    """Нормализует nutrition данные из разных источников"""

    def transform(item: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        if source_type == "usda":
            yield {
                "food_id": f"usda_{item['fdc_id']}",
                "name": item["description"],
                "source": "USDA_FDC",
                "energy_kcal_100g": extract_nutrient(item["nutrients"], "Energy"),
                "protein_g_100g": extract_nutrient(item["nutrients"], "Protein"),
                "fat_g_100g": extract_nutrient(item["nutrients"], "Total lipid (fat)"),
                "carbs_g_100g": extract_nutrient(item["nutrients"], "Carbohydrate, by difference"),
                "fiber_g_100g": extract_nutrient(item["nutrients"], "Fiber, total dietary"),
                "iron_mg_100g": extract_nutrient(item["nutrients"], "Iron, Fe"),
                "calcium_mg_100g": extract_nutrient(item["nutrients"], "Calcium, Ca"),
                "last_updated": item.get("modified_date"),
                "data_quality_score": calculate_quality_score(item)
            }

        elif source_type == "off":
            yield {
                "food_id": f"off_{item['code']}",
                "name": item["product_name"],
                "source": "OpenFoodFacts",
                "energy_kcal_100g": item.get("energy_kcal_100g"),
                "protein_g_100g": item.get("proteins_100g"),
                "fat_g_100g": item.get("fat_100g"),
                "carbs_g_100g": item.get("carbohydrates_100g"),
                "fiber_g_100g": item.get("fiber_100g"),
                "last_updated": item.get("last_modified_t"),
                "brands": item.get("brands"),
                "categories": item.get("categories"),
                "data_quality_score": calculate_quality_score(item)
            }

    return transform

def extract_nutrient(nutrients: list, nutrient_name: str) -> float:
    """Извлекает значение нутриента из USDA структуры"""
    for nutrient in nutrients:
        if nutrient.get("nutrientName") == nutrient_name:
            return nutrient.get("value", 0.0)
    return 0.0

def calculate_quality_score(item: Dict[str, Any]) -> float:
    """Рассчитывает score качества данных"""
    score = 0.0

    # Проверяем наличие ключевых нутриентов
    required_fields = ["energy_kcal_100g", "protein_g_100g", "fat_g_100g", "carbs_g_100g"]

    for field in required_fields:
        if item.get(field) is not None and item.get(field) > 0:
            score += 0.25

    return score
```

### 7. Инкрементальные обновления

```python
# dlt_pipelines/pipelines/incremental_updates.py
import dlt
from dlt.common.time import ensure_pendulum_datetime
from datetime import datetime, timedelta

@dlt.source
def incremental_nutrition_updates():
    """Инкрементальные обновления nutrition данных"""

    # Только новые/обновленные записи за последние 24 часа
    @dlt.resource(
        table_name="usda_foods",
        write_disposition="merge",
        primary_key="fdc_id"
    )
    def recent_usda_updates():
        # Используем dlt.sources.incremental для отслеживания последнего обновления
        last_updated = dlt.sources.incremental(
            "modified_date",
            initial_value=datetime.now() - timedelta(days=1)
        )

        # Загружаем только обновленные записи
        for food_item in fetch_usda_updates_since(last_updated.start_value):
            yield food_item

    return recent_usda_updates
```

### 8. Интеграция с FastAPI

```python
# core/data_pipeline.py
import dlt
from dlt_pipelines.pipelines.nutrition_etl import nutrition_pipeline
from dlt_pipelines.pipelines.incremental_updates import incremental_nutrition_updates

class DLTNutritionManager:
    """Менеджер для работы с DLT nutrition pipeline"""

    def __init__(self):
        self.pipeline = dlt.pipeline(
            pipeline_name="nutrition_etl",
            destination="duckdb",
            dataset_name="nutrition_db"
        )

    async def run_full_sync(self) -> dict:
        """Полная синхронизация всех данных"""
        load_info = nutrition_pipeline()
        return {
            "status": "completed",
            "loaded_packages": len(load_info.loads_ids),
            "tables_updated": list(load_info.dataset_name)
        }

    async def run_incremental_sync(self) -> dict:
        """Инкрементальная синхронизация"""
        incremental_source = incremental_nutrition_updates()
        load_info = self.pipeline.run(incremental_source)

        return {
            "status": "completed",
            "new_records": len(load_info.loads_ids),
            "sync_time": load_info.started_at
        }

    def get_data_stats(self) -> dict:
        """Статистика по загруженным данным"""
        with self.pipeline.sql_client() as client:
            # DuckDB queries для статистики
            usda_count = client.execute_sql("SELECT COUNT(*) FROM usda_foods")[0][0]
            off_count = client.execute_sql("SELECT COUNT(*) FROM off_products")[0][0]

            return {
                "usda_foods_count": usda_count,
                "off_products_count": off_count,
                "total_foods": usda_count + off_count,
                "last_sync": self.get_last_sync_time()
            }
```

### 9. API endpoints для DLT управления

```python
# В app.py добавить:

from core.data_pipeline import DLTNutritionManager

dlt_manager = DLTNutritionManager()

@app.post("/api/v1/admin/sync-nutrition-data")
async def sync_nutrition_data(
    sync_type: str = "incremental",  # "full" or "incremental"
    api_key: str = Depends(get_api_key)
):
    """Синхронизация nutrition данных через DLT"""
    try:
        if sync_type == "full":
            result = await dlt_manager.run_full_sync()
        else:
            result = await dlt_manager.run_incremental_sync()

        return {
            "status": "success",
            "sync_type": sync_type,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.get("/api/v1/admin/nutrition-stats")
async def get_nutrition_stats(api_key: str = Depends(get_api_key)):
    """Статистика nutrition данных"""
    stats = dlt_manager.get_data_stats()
    return stats
```

## 🎯 Преимущества DLT интеграции

### 1. **Автоматизация ETL**
- ✅ Автоматическая схема inference
- ✅ Incremental loading
- ✅ Data versioning
- ✅ Pipeline monitoring

### 2. **Scalability**
- ✅ Поддержка больших объёмов (миллионы записей)
- ✅ Efficient pagination
- ✅ Parallel processing
- ✅ Memory optimization

### 3. **Data Quality**
- ✅ Schema validation
- ✅ Type checking
- ✅ Data lineage tracking
- ✅ Quality scoring

### 4. **Flexibility**
- ✅ Multiple destinations (DuckDB, PostgreSQL, BigQuery)
- ✅ Custom transformations
- ✅ API integration
- ✅ Scheduling support

## 📈 Roadmap

### Phase 1: Базовая интеграция
1. ✅ Установка DLT
2. ⏳ USDA FDC source
3. ⏳ OpenFoodFacts source
4. ⏳ DuckDB destination

### Phase 2: Продвинутые функции
1. ⏳ Incremental updates
2. ⏳ Data quality checks
3. ⏳ API интеграция
4. ⏳ Monitoring dashboard

### Phase 3: Оптимизация
1. ⏳ Performance tuning
2. ⏳ Caching layer
3. ⏳ Real-time updates
4. ⏳ Multi-region support

## 🚀 Следующие шаги

1. **Установить DLT**: `pip install dlt[postgres,parquet]`
2. **Создать pipeline структуру**
3. **Настроить USDA API credentials**
4. **Протестировать на sample данных**
5. **Интегрировать с FastAPI admin endpoints**

---

**DLT поможет превратить наш nutrition pipeline из статических CSV файлов в современную, автоматизированную систему загрузки данных! 🚀**
