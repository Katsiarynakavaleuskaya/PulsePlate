# 🎯 План реализации Computer Vision, Machine Learning и Gamification

**Дата:** 2026-01-28
**Статус:** Комплексный план с open-source интеграциями
**Приоритет:** P0-P2 (Critical to Medium)

---

## 📊 Executive Summary

**Текущее состояние:**
- ❌ **Computer Vision:** Нет реализации (только упоминания в документации)
- ❌ **Food Recognition:** Нет функциональности
- ⚠️ **Recipe Generation:** Базовая реализация (`core/recipe_synth.py`), но нет AI-powered генерации
- ❌ **Shopping List Optimization:** Нет AI-ассистента
- ❌ **Gamification:** Нет игровых элементов
- ❌ **AI Motivation/Coaching:** Нет мотивационного ассистента

**Целевое состояние:**
- ✅ Food recognition по фотографии (CV)
- ✅ Calorie estimation по фотографии
- ✅ AI-powered recipe generation (кухни мира)
- ✅ Shopping list optimization AI
- ✅ Gamification system (achievements, streaks, rewards)
- ✅ AI health coach (мотивация, персональные советы)

---

## 🔍 Часть 1: Computer Vision для Food Recognition

### Текущее состояние

**Что есть:**
- ✅ Документация в `.cursor/agents/ai-innovation-specialist.md` (упоминания CV техник)
- ✅ Food database (`core/food_db.py`, `core/food_apis/`)
- ✅ Nutrition database (USDA, Open Food Facts)

**Чего нет:**
- ❌ Image upload endpoint
- ❌ Food recognition model
- ❌ Calorie estimation по фотографии
- ❌ Portion size estimation

---

### Open-Source проекты для интеграции

#### 1. **Food-Vision-101** (проверенная модель)

**Hugging Face:** `mhamza-007/Food-Vision-101` (EfficientNetB4 на Food-101)
**Лицензия:** проверьте карточку модели
**Особенности:**
- ✅ 101 категория (Food-101 dataset)
- ✅ ~79% test accuracy (документировано на HF)
- ✅ Готовый AutoImageProcessor + AutoModelForImageClassification

**Интеграция:**
```python
# core/cv/food_vision.py
from transformers import AutoImageProcessor, AutoModelForImageClassification
import torch

MODEL_ID = "mhamza-007/Food-Vision-101"  # Verified public model

class FoodVisionAI:
    """Food recognition using Food-Vision-101 (EfficientNetB4 on Food-101)."""

    def __init__(self):
        self.processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        self.model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def recognize(self, image: bytes) -> FoodRecognitionResult:
        """Recognize food from image."""
        inputs = self.processor(image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            top_probs, top_indices = torch.topk(probs, k=5)
        foods = []
        id2label = self.model.config.id2label
        for idx, prob in zip(top_indices[0], top_probs[0]):
            food_name = id2label.get(str(idx.item()), "unknown")
            foods.append({"name": food_name, "confidence": prob.item()})
        return FoodRecognitionResult(foods=foods)
```

**Оценка:** проверенная публичная модель; точность и лицензия — см. карточку на Hugging Face.

---

#### 2. **FoodVision** (Альтернатива)

**GitHub:** `faroukbrachemi/FoodVision`
**Лицензия:** MIT
**Особенности:**
- ✅ 101 категория (Food101 dataset)
- ✅ 85% accuracy
- ✅ CNN-based (быстрее, чем ViT)
- ✅ Обучен за 90 минут

**Интеграция:**
```python
# core/cv/foodvision.py
import torch
import torchvision.transforms as transforms
from PIL import Image

class FoodVision:
    """Food recognition using FoodVision CNN model."""

    def __init__(self):
        self.model = torch.load("models/foodvision.pth")
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def recognize(self, image: Image.Image) -> FoodRecognitionResult:
        """Recognize food from PIL Image."""
        # Preprocess
        img_tensor = self.transform(image).unsqueeze(0)

        # Predict
        with torch.no_grad():
            outputs = self.model(img_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)
            top_probs, top_indices = torch.topk(probs, k=5)

        # Map to food database
        foods = []
        for idx, prob in zip(top_indices[0], top_probs[0]):
            food_name = self._idx_to_food_name(idx.item())
            foods.append({
                "name": food_name,
                "confidence": prob.item(),
            })

        return FoodRecognitionResult(foods=foods)
```

**Оценка:** ⭐⭐⭐⭐ (4/5) — хорошая альтернатива, быстрее

---

#### 3. **Nutrify** (Streamlit-based, для прототипирования)

**GitHub:** `shivan-s/nutrify`
**Лицензия:** MIT
**Особенности:**
- ✅ Streamlit interface
- ✅ Nutrition information
- ✅ Data exploration tools
- ✅ Trained models available

**Оценка:** ⭐⭐⭐ (3/5) — хорош для прототипирования, но требует адаптации для production

---

### План реализации Food Recognition

#### Phase 1: Базовая интеграция (Week 1-2)

**Задачи:**

1. **Создать CV модуль**
   ```python
   # core/cv/__init__.py
   # core/cv/food_vision.py
   # core/cv/portion_estimation.py
   # core/cv/calorie_estimation.py
   ```

2. **Интегрировать Food-Vision-AI**
   - Fork/import модель
   - Создать wrapper (`FoodVisionAI`)
   - Добавить mapping к food database

3. **Создать API endpoint (с проверками безопасности и rate limiting)**
   ```python
   # app/routers/cv.py
   from fastapi import HTTPException
   from PIL import Image
   import io

   MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
   ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

   @router.post("/api/v1/pro/cv/food-recognition", dependencies=[Depends(require_pro_tier), Depends(rate_limit_llm)])
   async def recognize_food(image: UploadFile) -> FoodRecognitionResponse:
       """Recognize food from image. Validates type, size, integrity."""
       if image.content_type not in ALLOWED_TYPES:
           raise HTTPException(400, f"Invalid content type: {image.content_type}")
       contents = await image.read()
       if len(contents) > MAX_IMAGE_SIZE:
           raise HTTPException(413, "Image too large")
       try:
           img = Image.open(io.BytesIO(contents))
           img.verify()
       except Exception as e:
           raise HTTPException(400, f"Invalid image: {e}")
       # Call FoodVisionAI, map to food database, return nutrition info
   ```

   **Security (endpoint):** File type (ALLOWED_TYPES), size limit (MAX_IMAGE_SIZE), and image integrity (PIL verify) are enforced above; authentication and rate limiting via `Depends(require_pro_tier)`, `Depends(rate_limit_llm)`.

4. **Добавить calorie estimation**
   - Portion size estimation (reference object)
   - Calorie calculation (food_db lookup)

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

#### Phase 2: Улучшения (Week 3-4)

**Задачи:**

1. **Portion size estimation**
   - Reference object detection (coin, hand, plate)
   - Depth estimation (MiDaS)
   - Volume regression

2. **Multi-food detection**
   - Object detection (YOLO v8/v9)
   - Segmentation (SAM)
   - Composite meal recognition

3. **Nutrition label OCR**
   - Tesseract/EasyOCR для текста
   - LLM parsing для структурированных данных
   - Database lookup

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

## 🔍 Часть 2: AI-Powered Recipe Generation

### Текущее состояние

**Что есть:**
- ✅ `core/recipe_synth.py` (базовая генерация рецептов)
- ✅ Recipe database (`core/recipe_db_new.py`)
- ✅ Meal planning engine (`core/menu_engine.py`)

**Чего нет:**
- ❌ AI-powered recipe generation
- ❌ Кухни мира (cuisine types)
- ❌ Ингредиент-based генерация
- ❌ Dietary constraint-aware генерация

---

### Open-Source проекты для интеграции

#### 1. **Recipe_AI** (Рекомендуется)

**GitHub:** `Dyno-man/Recipe_AI`
**Лицензия:** MIT
**Особенности:**
- ✅ Генерация рецептов на основе pantry ingredients
- ✅ JSON datasets
- ✅ AI iterations

**Интеграция:**
```python
# core/recipes/ai_generator.py
from langchain import LLMChain, PromptTemplate
from langchain.llms import OpenAI  # или наш провайдер

class AIRecipeGenerator:
    """AI-powered recipe generation."""

    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.prompt_template = PromptTemplate(
            input_variables=["ingredients", "cuisine", "dietary_constraints"],
            template="""
            Generate a recipe using these ingredients: {ingredients}
            Cuisine type: {cuisine}
            Dietary constraints: {dietary_constraints}

            Return JSON format:
            {{
                "title": "...",
                "description": "...",
                "ingredients": [...],
                "steps": [...],
                "nutrition": {{"kcal": ..., "protein_g": ..., ...}}
            }}
            """
        )

    def generate(self, ingredients: list[str], cuisine: str = "international",
                 dietary_constraints: set[str] = None) -> Recipe:
        """Generate recipe from ingredients."""
        prompt = self.prompt_template.format(
            ingredients=", ".join(ingredients),
            cuisine=cuisine,
            dietary_constraints=", ".join(dietary_constraints or [])
        )

        response = await self.llm.generate(prompt)
        recipe_data = json.loads(response)

        return Recipe(**recipe_data)
```

**Оценка:** ⭐⭐⭐⭐ (4/5) — хорошая база, требует адаптации

---

#### 2. **Sauteq** (Next.js + OpenAI)

**GitHub:** `rqres/sauteq`
**Лицензия:** MIT
**Особенности:**
- ✅ Next.js frontend
- ✅ OpenAI API integration
- ✅ Ingredient-based generation

**Оценка:** ⭐⭐⭐ (3/5) — хорош для frontend, но backend требует переписывания

---

#### 3. **RecipeMe.ai** (Flask-based)

**GitHub:** `petersapountzis/RecipeMe.ai`
**Лицензия:** MIT
**Особенности:**
- ✅ Flask backend
- ✅ Database integration
- ✅ Web interface

**Оценка:** ⭐⭐⭐ (3/5) — требует адаптации к FastAPI

---

### План реализации Recipe Generation

#### Phase 1: AI Integration (Week 1-2)

**Задачи:**

1. **Интегрировать LLM в recipe generation**
   ```python
   # core/recipes/ai_generator.py
   class AIRecipeGenerator:
       def generate_from_ingredients(self, ingredients, cuisine, constraints) -> Recipe
       def generate_from_cuisine(self, cuisine, kcal_target, constraints) -> Recipe
       def generate_from_preferences(self, preferences, constraints) -> Recipe
   ```

2. **Добавить cuisine types**
   - Italian, French, Japanese, Indian, Mexican, Thai, etc.
   - Cuisine-specific templates
   - Cuisine-specific ingredient lists

3. **Создать API endpoint**
   ```python
   # app/routers/vip.py
   @router.post("/api/v1/vip/recipes/generate", dependencies=[Depends(require_vip_tier)])
   async def generate_recipe(req: RecipeGenerationRequest) -> RecipeResponse:
       """Generate AI-powered recipe."""
   ```

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

#### Phase 2: Улучшения (Week 3-4)

**Задачи:**

1. **Dietary constraint-aware generation**
   - VEG, GF, KETO, PALEO, etc.
   - Ingredient substitution
   - Nutrition optimization

2. **Multi-cuisine meal planning**
   - Weekly plan с разными кухнями
   - Cuisine rotation
   - Cultural preferences

3. **Recipe personalization**
   - User preferences
   - Past recipe ratings
   - Nutritional goals

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

## 🔍 Часть 3: Shopping List Optimization AI

### Текущее состояние

**Что есть:**
- ✅ Shopping list generation (`core/shoplist_engine/`)
- ✅ Product finder (`core/product_finder.py`)
- ✅ Catalog adapter (`app/services/catalog_adapter.py`)

**Чего нет:**
- ❌ AI-оптимизация списка покупок
- ❌ Price optimization
- ❌ Store selection AI
- ❌ Meal plan → shopping list AI

---

### План реализации Shopping List AI

#### Phase 1: AI Assistant для Shopping List (Week 1-2)

**Задачи:**

1. **Создать AI shopping assistant**
   ```python
   # core/shoplist/ai_assistant.py
   class ShoppingListAI:
       def optimize_list(self, meal_plan: WeeklyPlan, budget: float) -> OptimizedShoppingList
       def suggest_substitutions(self, unavailable_items: list[str]) -> list[Substitution]
       def recommend_stores(self, shopping_list: ShoppingList, location: str) -> list[Store]
   ```

2. **Интеграция с meal planning**
   - Автоматическая генерация списка из meal plan
   - Ингредиент aggregation
   - Portion scaling

3. **Price optimization**
   - Сравнение цен между stores
   - Budget constraints
   - Bulk buying recommendations

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

#### Phase 2: Advanced Features (Week 3-4)

**Задачи:**

1. **Store selection AI**
   - Location-based recommendations
   - Price comparison
   - Availability checking

2. **Ingredient substitution**
   - Dietary constraint-aware
   - Price optimization
   - Nutrition equivalence

3. **Shopping route optimization**
   - Multi-store optimization
   - Route planning
   - Time estimation

**Время:** 2 недели
**Приоритет:** P2 (MEDIUM)

---

## 🔍 Часть 4: Gamification System

### Текущее состояние

**Что есть:**
- ⚠️ Telemetry system (`frontend/src/lib/telemetry.ts`)
- ❌ Нет gamification элементов

**Чего нет:**
- ❌ Achievements/badges
- ❌ Streaks
- ❌ Rewards
- ❌ Leaderboards
- ❌ Challenges

---

### Open-Source проекты для интеграции

#### 1. **Sukuwatto** (Рекомендуется)

**GitHub:** `t-recx/sukuwatto`
**Лицензия:** MIT
**Особенности:**
- ✅ Workout tracker с gamification
- ✅ Social components
- ✅ Full backend/frontend architecture

**Оценка:** ⭐⭐⭐⭐ (4/5) — хорошая архитектура, требует адаптации

---

#### 2. **DuckDuckJump** (Gamified Fitness)

**GitHub:** `JumpFit/DuckDuckJump`
**Лицензия:** MIT
**Особенности:**
- ✅ Platformer game + fitness
- ✅ TensorFlow.js для movement detection
- ✅ Phaser 3.js для gaming

**Оценка:** ⭐⭐⭐ (3/5) — интересно, но требует значительной адаптации

---

#### 3. **wger** (Self-hosted Fitness Tracker)

**GitHub:** `wger-project/wger`
**Лицензия:** AGPL-3.0
**Особенности:**
- ✅ 5.5k stars, 810 forks
- ✅ Self-hosted
- ✅ Nutrition + workout tracking

**Оценка:** ⭐⭐⭐⭐ (4/5) — отличная база, но AGPL лицензия требует внимания

---

### План реализации Gamification

#### Phase 1: Базовая Gamification (Week 1-2)

**Задачи:**

1. **Создать gamification модуль**
   ```python
   # core/gamification/__init__.py
   # core/gamification/achievements.py
   # core/gamification/streaks.py
   # core/gamification/rewards.py
   ```

2. **Achievements System**
   ```python
   # core/gamification/achievements.py
   class Achievement:
       id: str
       name: str
       description: str
       icon: str
       condition: Callable  # функция проверки условия

   ACHIEVEMENTS = [
       Achievement("first_bmi", "First BMI Calculation", "Calculate your first BMI", "🎯"),
       Achievement("week_streak", "Week Streak", "Log meals for 7 days", "🔥"),
       Achievement("nutrition_goal", "Nutrition Goal", "Meet nutrition targets for a week", "⭐"),
   ]
   ```

3. **Streaks System**
   ```python
   # core/gamification/streaks.py
   class StreakTracker:
       def get_current_streak(self, user_id: str, activity: str) -> int
       def update_streak(self, user_id: str, activity: str) -> StreakResult
       def get_longest_streak(self, user_id: str, activity: str) -> int
   ```

4. **API endpoints**
   ```python
   # app/routers/gamification.py
   @router.get("/api/v1/gamification/achievements")
   @router.get("/api/v1/gamification/streaks")
   @router.post("/api/v1/gamification/rewards/claim")
   ```

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

#### Phase 2: Advanced Features (Week 3-4)

**Задачи:**

1. **Rewards System**
   - Points system
   - Badge collection
   - Unlockable features

2. **Challenges**
   - Daily challenges
   - Weekly challenges
   - Community challenges

3. **Leaderboards**
   - Global leaderboard
   - Friend leaderboard
   - Category leaderboards (BMI improvement, nutrition goals, etc.)

**Время:** 2 недели
**Приоритет:** P2 (MEDIUM)

---

## 🔍 Часть 5: AI Health Coach (Motivation)

### Текущее состояние

**Что есть:**
- ✅ Insight endpoint (`/api/v1/insight`)
- ✅ LLM providers (grok, ollama)
- ❌ Нет специализированного health coach

**Чего нет:**
- ❌ Personal health coach
- ❌ Motivation system
- ❌ Progress tracking AI
- ❌ Personalized advice

---

### Open-Source проекты для интеграции

#### 1. **AI Habit Coach** (Рекомендуется)

**GitHub:** `mohdarshil09/AI_habit_coach`
**Лицензия:** MIT
**Особенности:**
- ✅ React + FastAPI (совместимо с нашим стеком)
- ✅ OpenAI GPT integration
- ✅ Goal tracking
- ✅ Motivational quotes
- ✅ Progress indicators

**Интеграция:**
```python
# core/coach/ai_coach.py
class AIHealthCoach:
    """AI-powered health coach for motivation and advice."""

    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.system_prompt = """
        You are a friendly, supportive health and nutrition coach for PulsePlate.
        Your role:
        - Provide personalized nutrition advice
        - Motivate users to achieve their health goals
        - Celebrate their progress
        - Offer practical, actionable tips
        - Be empathetic and understanding
        """

    async def get_motivation(self, user_profile: UserProfile, progress: ProgressData) -> str:
        """Get personalized motivation message."""
        prompt = f"""
        User profile: {user_profile}
        Recent progress: {progress}

        Provide a motivational message (2-3 sentences) that:
        1. Acknowledges their progress
        2. Encourages continued effort
        3. Offers a specific tip for improvement
        """

        return await self.llm.generate(prompt)

    async def get_advice(self, user_query: str, context: UserContext) -> str:
        """Get personalized health advice."""
        prompt = f"""
        User query: {user_query}
        User context: {context}

        Provide personalized, evidence-based advice.
        """

        return await self.llm.generate(prompt)
```

**Оценка:** ⭐⭐⭐⭐⭐ (5/5) — идеально подходит для нашего стека

---

#### 2. **GPTCoach (CHI '25)**

**GitHub:** `StanfordHCI/GPTCoach-CHI2025`
**Лицензия:** Research (требует проверки)
**Особенности:**
- ✅ Full-stack (backend, frontend, iOS)
- ✅ Research-backed
- ✅ Prompt configurations

**Оценка:** ⭐⭐⭐⭐ (4/5) — отличная база, но research license требует внимания

---

#### 3. **Goggins AI Fitness Coach**

**GitHub:** `extrawest/goggins-ai-fitness-coach`
**Лицензия:** MIT
**Особенности:**
- ✅ Intense motivational style
- ✅ Workout recommendations
- ✅ Fitness advice

**Оценка:** ⭐⭐⭐ (3/5) — интересно, но стиль может быть слишком интенсивным

---

### План реализации AI Health Coach

#### Phase 1: Базовая реализация (Week 1-2)

**Задачи:**

1. **Создать AI Coach модуль**
   ```python
   # core/coach/__init__.py
   # core/coach/ai_coach.py
   # core/coach/motivation.py
   # core/coach/progress_tracker.py
   ```

2. **Motivation System**
   - Personalized messages
   - Progress celebration
   - Goal reminders
   - Encouragement

3. **API endpoints**
   ```python
   # app/routers/vip.py
   @router.post("/api/v1/vip/coach/motivation", dependencies=[Depends(require_vip_tier)])
   @router.post("/api/v1/vip/coach/advice", dependencies=[Depends(require_vip_tier)])
   @router.get("/api/v1/vip/coach/progress", dependencies=[Depends(require_vip_tier)])
   ```

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

#### Phase 2: Advanced Features (Week 3-4)

**Задачи:**

1. **Personalized Coaching**
   - User preference learning
   - Coaching style adaptation
   - Goal-based advice

2. **Progress Analysis**
   - Trend analysis
   - Anomaly detection
   - Predictive insights

3. **Proactive Coaching**
   - Push notifications
   - Daily check-ins
   - Weekly summaries

**Время:** 2 недели
**Приоритет:** P1 (HIGH)

---

## 📊 Сводная таблица реализации

| Компонент | Текущее состояние | Целевое состояние | Open-Source проект | Приоритет | Время |
|-----------|-------------------|-------------------|-------------------|-----------|-------|
| **Food Recognition** | ❌ Нет | ✅ CV модель | Food-Vision-AI | P1 | 2-4 недели |
| **Calorie Estimation** | ❌ Нет | ✅ Portion + calories | Food-Vision-AI + portion estimation | P1 | 2-4 недели |
| **Recipe Generation** | ⚠️ Базовая | ✅ AI-powered | Recipe_AI | P1 | 2-4 недели |
| **Cuisine Types** | ❌ Нет | ✅ 10+ кухонь | Recipe_AI + custom | P1 | 2 недели |
| **Shopping List AI** | ⚠️ Базовая | ✅ AI optimization | Custom (LLM-based) | P1 | 2-4 недели |
| **Gamification** | ❌ Нет | ✅ Achievements, streaks | Sukuwatto (архитектура) | P1 | 2-4 недели |
| **AI Health Coach** | ⚠️ Insight only | ✅ Full coach | AI Habit Coach | P1 | 2-4 недели |

**Общее время:** 8-12 недель (2-3 месяца)
**Общий приоритет:** P1 (HIGH)

---

## 🎯 Критические пути развития

### Path 1: Food Recognition (P1 — High Priority)

**Week 1-2:**
1. Интегрировать Food-Vision-AI
2. Создать API endpoint
3. Добавить food database mapping
4. Базовое calorie estimation

**Week 3-4:**
1. Portion size estimation
2. Multi-food detection
3. Nutrition label OCR

**Результат:** Пользователи могут фотографировать еду и получать nutrition info

---

### Path 2: AI Recipe Generation (P1 — High Priority)

**Week 1-2:**
1. Интегрировать LLM в recipe generation
2. Добавить cuisine types
3. Создать API endpoint

**Week 3-4:**
1. Dietary constraint-aware generation
2. Multi-cuisine meal planning
3. Recipe personalization

**Результат:** AI генерирует рецепты для разных кухонь мира

---

### Path 3: Gamification (P1 — High Priority)

**Week 1-2:**
1. Achievements system
2. Streaks system
3. API endpoints

**Week 3-4:**
1. Rewards system
2. Challenges
3. Leaderboards

**Результат:** Пользователи мотивированы через игровые элементы

---

### Path 4: AI Health Coach (P1 — High Priority)

**Week 1-2:**
1. AI Coach модуль
2. Motivation system
3. API endpoints

**Week 3-4:**
1. Personalized coaching
2. Progress analysis
3. Proactive coaching

**Результат:** Персональный AI health coach для мотивации

---

## 💰 Cost Optimization

### Open-Source преимущества

**1. Food Recognition:**
- ✅ Бесплатные модели (Food-Vision-AI, FoodVision)
- ✅ Self-hosted (нет API costs)
- ✅ Одноразовая настройка

**2. Recipe Generation:**
- ✅ Использовать локальные LLM (Ollama) вместо cloud
- ✅ Кэширование популярных рецептов
- ✅ Batch generation для meal plans

**3. AI Health Coach:**
- ✅ Использовать Ollama для локального coaching
- ✅ Grok для cloud (только VIP tier)
- ✅ Кэширование common advice

**4. Gamification:**
- ✅ Полностью self-hosted (нет external costs)
- ✅ Минимальные compute requirements

**Общая экономия:** $500-1000/month (vs cloud APIs)

---

## 🔗 Интеграция с существующими модулями

### Food Recognition → Food Database

```python
# core/cv/food_vision.py
def map_to_food_db(self, recognized_foods: list[Food]) -> list[FoodItem]:
    """Map recognized foods to food database."""
    from core.food_db import get_food_db

    food_db = get_food_db()
    mapped = []

    for food in recognized_foods:
        # Fuzzy match to canonical name
        canonical = self._fuzzy_match(food.name, food_db.keys())
        if canonical:
            mapped.append(food_db[canonical])

    return mapped
```

### Recipe Generation → Meal Planning

```python
# core/recipes/ai_generator.py
def generate_for_meal_plan(self, meal_plan: WeeklyPlan) -> list[Recipe]:
    """Generate recipes for weekly meal plan."""
    recipes = []

    for day in meal_plan.days:
        for meal in day.meals:
            recipe = self.generate(
                ingredients=meal.ingredients,
                cuisine=day.cuisine,
                constraints=meal_plan.dietary_constraints
            )
            recipes.append(recipe)

    return recipes
```

### Shopping List AI → Meal Planning

```python
# core/shoplist/ai_assistant.py
def generate_from_meal_plan(self, meal_plan: WeeklyPlan) -> ShoppingList:
    """Generate optimized shopping list from meal plan."""
    # Aggregate ingredients
    ingredients = {}
    for day in meal_plan.days:
        for meal in day.meals:
            for ingredient, amount in meal.ingredients.items():
                ingredients[ingredient] = ingredients.get(ingredient, 0) + amount

    # Optimize
    optimized = self.optimize_list(ingredients, meal_plan.budget)

    return optimized
```

### Gamification → User Actions

```python
# core/gamification/achievements.py
def check_achievements(self, user_id: str, action: str, data: dict) -> list[Achievement]:
    """Check if user unlocked any achievements."""
    unlocked = []

    for achievement in ACHIEVEMENTS:
        if achievement.condition(user_id, action, data):
            unlocked.append(achievement)
            self._unlock_achievement(user_id, achievement.id)

    return unlocked
```

### AI Coach → User Progress

```python
# core/coach/ai_coach.py
async def get_daily_motivation(self, user_id: str) -> str:
    """Get daily motivation based on user progress."""
    progress = self._get_user_progress(user_id)

    if progress.streak_days > 0:
        return await self.get_motivation(
            user_profile=self._get_user_profile(user_id),
            progress=progress
        )

    return "Keep going! Every day is a new opportunity to improve your health."
```

---

## 📋 Рекомендации по внедрению

### Immediate Actions (This Week):

1. **P1 HIGH:**
   - Начать интеграцию Food-Vision-AI
   - Создать базовый gamification модуль
   - Интегрировать AI Habit Coach архитектуру

### Short-Term (Next Month):

2. **P1 HIGH:**
   - Завершить Food Recognition
   - Завершить AI Recipe Generation
   - Завершить Gamification
   - Завершить AI Health Coach

### Long-Term (Next Quarter):

3. **P2 MEDIUM:**
   - Advanced CV features (portion estimation, multi-food)
   - Advanced gamification (leaderboards, challenges)
   - Advanced AI coach (proactive coaching, predictive insights)

---

## 🔗 Связанные документы

- `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md` — LLM/RAG анализ
- `docs/analysis/FRONTEND_IOS_VISUAL_ANALYSIS.md` — Frontend/iOS анализ
- `.cursor/agents/ai-innovation-specialist.md` — AI innovation guide
- `core/recipe_synth.py` — текущая recipe generation
- `core/shoplist_engine/` — shopping list engine

---

**Последнее обновление:** 2026-01-28
**Версия:** 1.0
