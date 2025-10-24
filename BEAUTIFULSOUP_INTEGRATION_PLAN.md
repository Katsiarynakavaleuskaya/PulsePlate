# 🍲 BeautifulSoup Integration Plan для PulsePlate

## 🎯 Цель

Использовать BeautifulSoup для парсинга HTML страниц магазинов, ресторанов и кулинарных сайтов для автоматического извлечения данных о продуктах и рецептах.

## 📊 Текущее состояние

- ❌ BeautifulSoup не установлен
- ❌ Нет парсеров для веб-скрапинга
- ✅ requests уже используется для API интеграции

## 🛠️ Установка и настройка

### 1. Добавить в requirements.txt

```bash
# Веб-скрапинг и парсинг
beautifulsoup4>=4.12.0
lxml>=4.9.0  # Быстрый XML/HTML парсер
html5lib>=1.1  # Альтернативный парсер
requests-html>=0.10.0  # Для JavaScript-рендеринга
```

### 2. Установить зависимости

```bash
pip install beautifulsoup4 lxml html5lib requests-html
```

## 🌐 Применение для PulsePlate

### 1. **Парсинг магазинов продуктов**

```python
# core/web_scrapers/store_parsers.py
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
import logging

class StoreParser:
    """Базовый класс для парсинга магазинов"""

    def __init__(
        self,
        store_name: str,
        base_url: str,
        user_agent: str = 'Mozilla/5.0 (compatible; PulsePlate/1.0)'
    ) -> None:
        self.store_name = store_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml',
        })

    def parse_product_page(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Парсинг страницы продукта"""
        try:
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            return {
                'name': self._extract_name(soup),
                'price': self._extract_price(soup),
                'nutrition': self._extract_nutrition(soup),
                'ingredients': self._extract_ingredients(soup),
                'image_url': self._extract_image(soup),
                'store': self.store_name,
                'source_url': product_url
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error parsing {product_url}: {e}")
            return None
        except Exception as e:
            logging.exception(f"Parsing error for {product_url}: {e}")
            return None

    def _extract_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение названия продукта"""
        # Разные селекторы для разных магазинов
        selectors = [
            'h1.product-title',
            'h1[data-testid="product-title"]',
            '.product-name h1',
            'h1.title'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

        return "Unknown Product"

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Извлечение цены"""
        price_selectors = [
            '.price-current',
            '[data-testid="price"]',
            '.product-price .current-price',
            '.price .value'
        ]

        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Извлекаем число из строки типа "$12.99" или "12,99 €"
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', '.'))
                if price_match:
                    return float(price_match.group())

        return None

    def _extract_nutrition(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение nutritional информации"""
        nutrition = {}

        # Ищем таблицу nutrition facts
        nutrition_table = soup.find('table', class_='nutrition-facts')
        if not nutrition_table:
            nutrition_table = soup.find('div', class_='nutrition-info')

        if nutrition_table:
            rows = nutrition_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    nutrient = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    # Маппинг nutrient names
                    if 'calories' in nutrient or 'kcal' in nutrient:
                        nutrition['calories'] = self._parse_nutrition_value(value)
                    elif 'protein' in nutrient:
                        nutrition['protein_g'] = self._parse_nutrition_value(value)
                    elif 'fat' in nutrient and 'total' in nutrient:
                        nutrition['fat_g'] = self._parse_nutrition_value(value)
                    elif 'carbohydrate' in nutrient or 'carbs' in nutrient:
                        nutrition['carbs_g'] = self._parse_nutrition_value(value)
                    elif 'fiber' in nutrient:
                        nutrition['fiber_g'] = self._parse_nutrition_value(value)

        return nutrition

    def _parse_nutrition_value(self, value_str: str) -> Optional[float]:
        """Парсинг nutritional values"""
        # Извлекаем число из строки типа "12g", "12.5g", "12,5g"
        match = re.search(r'[\d,]+\.?\d*', value_str.replace(',', '.'))
        return float(match.group()) if match else None

    def _extract_ingredients(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """Извлечение списка ингредиентов"""
        # Разные селекторы для ингредиентов
        selectors = [
            '.ingredients-list li',
            '.product-ingredients',
            '[data-testid="ingredients"]',
            '.ingredients p'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                ingredients = []
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and text.lower() not in ['ingredients:', 'состав:']:
                        # Разделяем по запятым и очищаем
                        parts = [part.strip() for part in text.split(',')]
                        ingredients.extend(parts)
                return ingredients if ingredients else None

        return None

    def _extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение URL изображения продукта"""
        # Разные селекторы для изображений
        selectors = [
            '.product-image img',
            '[data-testid="product-image"]',
            '.product-photo img',
            '.main-image img'
        ]

        for selector in selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    # Преобразуем относительные URL в абсолютные
                    if src.startswith('//'):
                        return f"https:{src}"
                    elif src.startswith('/'):
                        return f"{self.base_url.rstrip('/')}{src}"
                    elif src.startswith('http'):
                        return src

        return None

    def close(self):
        """Закрытие сессии"""
        if hasattr(self, 'session'):
            self.session.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __del__(self):
        """Destructor"""
        self.close()
```

### 2. **Парсинг ресторанов и доставки**

```python
# core/web_scrapers/restaurant_parsers.py
import re
import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

class RestaurantParser:
    """Парсер для ресторанов и доставки еды"""

    def __init__(self, session: Optional[requests.Session] = None):
        """Инициализация парсера"""
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; PulsePlate/1.0)'
        })

    def parse_menu_page(self, restaurant_url: str) -> List[Dict]:
        """Парсинг меню ресторана"""
        try:
            response = self.session.get(restaurant_url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')

            menu_items = []

            # Ищем элементы меню
            menu_items_elements = soup.find_all(['div', 'li'], class_=re.compile(r'menu-item|dish|food-item'))

            for item in menu_items_elements:
                menu_item = {
                    'name': self._extract_dish_name(item),
                    'description': self._extract_dish_description(item),
                    'price': self._extract_dish_price(item),
                    'category': self._extract_dish_category(item),
                    'allergens': self._extract_allergens(item),
                    'image_url': self._extract_dish_image(item),
                    'restaurant': self._extract_restaurant_name(soup)
                }

                if menu_item['name']:
                    menu_items.append(menu_item)

            return menu_items

        except Exception as e:
            logging.error(f"Error parsing restaurant menu: {e}")
            return []

    def _extract_dish_name(self, item) -> str:
        """Извлечение названия блюда"""
        name_elem = item.find(['h3', 'h4', 'span'], class_=re.compile(r'name|title|dish-name'))
        return name_elem.get_text(strip=True) if name_elem else ""

    def _extract_dish_description(self, item) -> str:
        """Извлечение описания блюда"""
        desc_elem = item.find(['p', 'div'], class_=re.compile(r'description|desc|details'))
        return desc_elem.get_text(strip=True) if desc_elem else ""

    def _extract_dish_price(self, item) -> Optional[float]:
        """Извлечение цены блюда"""
        price_elem = item.find(['span', 'div'], class_=re.compile(r'price|cost'))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Извлекаем число из строки цены
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', '.'))
            if price_match:
                try:
                    return float(price_match.group())
                except ValueError:
                    pass
        return None

    def _extract_dish_category(self, item) -> str:
        """Извлечение категории блюда"""
        category_elem = item.find(['span', 'div'], class_=re.compile(r'category|type|section'))
        return category_elem.get_text(strip=True) if category_elem else ""

    def _extract_allergens(self, item) -> List[str]:
        """Извлечение аллергенов"""
        allergen_elem = item.find(['span', 'div'], class_=re.compile(r'allergen|allergy'))
        if allergen_elem:
            allergen_text = allergen_elem.get_text(strip=True)
            return [a.strip() for a in allergen_text.split(',') if a.strip()]
        return []

    def _extract_dish_image(self, item) -> str:
        """Извлечение URL изображения блюда"""
        img_elem = item.find('img')
        if img_elem and img_elem.get('src'):
            return img_elem['src']
        return ""

    def _extract_restaurant_name(self, soup) -> str:
        """Извлечение названия ресторана"""
        name_elem = soup.find(['h1', 'h2'], class_=re.compile(r'restaurant|name|title'))
        return name_elem.get_text(strip=True) if name_elem else ""
```

### 3. **Парсинг кулинарных сайтов и рецептов**

```python
# core/web_scrapers/recipe_parsers.py
import json
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any, TypedDict

class RecipeParser:
    """Парсер для кулинарных сайтов"""

    def __init__(self, session: Optional[requests.Session] = None):
        """Инициализация парсера"""
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; PulsePlate/1.0)'
        })

    def parse_recipe_page(self, recipe_url: str) -> Optional[Dict]:
        """Парсинг рецепта"""
        try:
            response = self.session.get(recipe_url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')

            # Ищем structured data (JSON-LD)
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    recipe_data = json.loads(json_ld.string)
                    if isinstance(recipe_data, list):
                        recipe_data = recipe_data[0]

                    if recipe_data.get('@type') == 'Recipe':
                        return self._parse_structured_recipe(recipe_data)
                except json.JSONDecodeError:
                    pass

            # Fallback: парсинг HTML
            return self._parse_html_recipe(soup)

        except Exception as e:
            logging.error(f"Error parsing recipe: {e}")
            return None

    def _has_class_containing(self, class_list, substring: str) -> bool:
        """Check if any class contains substring"""
        return class_list and substring in str(class_list).lower()

    def _parse_html_recipe(self, soup) -> Dict:
        """Fallback HTML парсинг рецепта"""
        return {
            'name': soup.find('h1').get_text(strip=True) if soup.find('h1') else '',
            'description': soup.find('meta', {'name': 'description'}).get('content', '') if soup.find('meta', {'name': 'description'}) else '',
            'ingredients': [li.get_text(strip=True) for li in soup.find_all('li', class_=lambda x: self._has_class_containing(x, 'ingredient'))],
            'instructions': [li.get_text(strip=True) for li in soup.find_all('li', class_=lambda x: self._has_class_containing(x, 'instruction'))],
            'prep_time': '',
            'cook_time': '',
            'servings': '',
            'nutrition': {},
            'image_url': soup.find('img').get('src', '') if soup.find('img') else '',
            'source_url': '',
            'cuisine': '',
            'difficulty': ''
        }

    def _parse_structured_recipe(self, data: Dict) -> Dict:
        """Парсинг structured data рецепта"""
        return {
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'ingredients': data.get('recipeIngredient', []),
            'instructions': data.get('recipeInstructions', []),
            'prep_time': data.get('prepTime', ''),
            'cook_time': data.get('cookTime', ''),
            'total_time': data.get('totalTime', ''),
            'servings': data.get('recipeYield', ''),
            'nutrition': data.get('nutrition', {}),
            'image_url': data.get('image', ''),
            'cuisine_type': data.get('recipeCuisine', ''),
            'difficulty': data.get('recipeDifficulty', ''),
            'source_url': data.get('url', '')
        }
```

## 🌍 Региональные парсеры

### 1. **Российские магазины**

```python
# core/web_scrapers/russian_stores.py
class RussianStoreParser(StoreParser):
    """Парсер для российских магазинов"""

    def __init__(self):
        super().__init__("Russian Store", "https://example.ru")

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Парсинг цен в рублях"""
        price_element = soup.find('span', class_='price')
        if price_element:
            price_text = price_element.get_text(strip=True)
            # Убираем "₽" и пробелы, заменяем запятую на точку
            price_clean = price_text.replace('₽', '').replace(' ', '').replace(',', '.')
            try:
                return float(price_clean)
            except ValueError:
                pass
        return None
```

### 2. **Европейские магазины**

```python
# core/web_scrapers/european_stores.py
import re
from typing import Optional
from bs4 import BeautifulSoup

class EuropeanStoreParser(StoreParser):
    """Парсер для европейских магазинов"""

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Парсинг цен в евро"""
        # Поддержка разных форматов: "12,99 €", "€12.99", "12.99EUR"
        price_patterns = [
            r'(\d+[,.]?\d*)\s*€',
            r'€\s*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*EUR'
        ]

        price_text = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, price_text)
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None
```

## 🔄 Интеграция с DLT Pipeline

```python
# dlt_pipelines/sources/web_scraping_source.py
import dlt
from typing import List, Iterator, Dict
from core.web_scrapers.store_parsers import StoreParser
from core.web_scrapers.recipe_parsers import RecipeParser

@dlt.source
def web_scraping_source(store_urls: List[str], recipe_urls: List[str]):
    """DLT source для веб-скрапинга"""

    @dlt.resource(name="scraped_products", write_disposition="merge")
    def scrape_products() -> Iterator[Dict]:
        """Скрапинг продуктов из магазинов"""
        parser = StoreParser("Generic Store", "")

        for url in store_urls:
            product_data = parser.parse_product_page(url)
            if product_data:
                yield {
                    **product_data,
                    'scraped_at': dlt.current_timestamp(),
                    'source_type': 'web_scraping'
                }

    @dlt.resource(name="scraped_recipes", write_disposition="merge")
    def scrape_recipes() -> Iterator[Dict]:
        """Скрапинг рецептов"""
        parser = RecipeParser()

        for url in recipe_urls:
            recipe_data = parser.parse_recipe_page(url)
            if recipe_data:
                yield {
                    **recipe_data,
                    'scraped_at': dlt.current_timestamp(),
                    'source_type': 'web_scraping'
                }

    return [scrape_products(), scrape_recipes()]
```

## 🛡️ Этические и правовые аспекты

### 1. **Соблюдение robots.txt**

```python
# core/web_scrapers/robots_checker.py
import urllib.robotparser
from urllib.parse import urljoin, urlparse

class RobotsChecker:
    """Проверка robots.txt перед скрапингом"""

    def __init__(self):
        self.robots_cache = {}

    def can_scrape(self, url: str, user_agent: str = '*') -> bool:
        """Проверка разрешения на скрапинг"""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if base_url not in self.robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urljoin(base_url, '/robots.txt'))
            rp.read()
            self.robots_cache[base_url] = rp

        return self.robots_cache[base_url].can_fetch(user_agent, url)
```

### 2. **Rate Limiting и вежливый скрапинг**

```python
# core/web_scrapers/polite_scraper.py
import time
import random
import requests
import logging
from typing import Dict, Optional

class PoliteScraper:
    """Вежливый скрапер с rate limiting"""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0

    def scrape_with_delay(self, url: str) -> Optional[requests.Response]:
        """Скрапинг с задержкой между запросами"""
        # Соблюдаем rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)

        # Случайная задержка для имитации человеческого поведения
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

        try:
            response = requests.get(url, timeout=30)
            self.last_request_time = time.time()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {url}: {e}")
            return None
```

## 📈 Преимущества BeautifulSoup для PulsePlate

### 1. **Автоматическое наполнение БД**

- ✅ Парсинг миллионов продуктов из магазинов
- ✅ Извлечение актуальных цен и наличия
- ✅ Получение nutritional информации
- ✅ Сбор рецептов из кулинарных сайтов

### 2. **Масштабируемость**

- ✅ Поддержка множества сайтов
- ✅ Адаптация под разные структуры HTML
- ✅ Обработка JavaScript-рендеринга
- ✅ Кэширование и оптимизация

### 3. **Качество данных**

- ✅ Валидация и очистка данных
- ✅ Нормализация единиц измерения
- ✅ Дедупликация продуктов
- ✅ Контроль качества

## 🚀 Следующие шаги

1. **Установить BeautifulSoup** и зависимости
2. **Создать базовые парсеры** для популярных магазинов
3. **Интегрировать с DLT pipeline** для ETL
4. **Добавить мониторинг** и алерты
5. **Создать dashboard** для отслеживания скрапинга

## 💰 Экономический эффект

- **Экономия времени**: Автоматизация vs ручной сбор данных
- **Качество данных**: Актуальные цены и наличие
- **Масштаб**: Миллионы продуктов vs тысячи
- **Локализация**: Поддержка разных регионов и валют

---

**Вывод**: BeautifulSoup критически важен для масштабирования проекта и автоматического сбора данных о продуктах и рецептах!
