# Project TODO List

This document tracks the progress of the BMI App project, showing what has been completed and what still needs to be done.

## Completed Tasks

### ✅ Spanish Language Implementation
- [x] Enhanced core i18n system to include Spanish language support
- [x] Added comprehensive Spanish translation dictionary with all necessary keys
- [x] Extended Language type alias to include "es"
- [x] Added new translation keys for previously missing items:
  - Risk assessment notes for elderly, children, and teens
  - Level descriptions (advanced, intermediate, novice, beginner)
- [x] Verified validation function works across all three languages
- [x] Updated bodyfat.py with Spanish language support
- [x] Added Spanish labels for body fat calculation results:
  - "métodos" for methods
  - "mediana" for median
  - "%" for units
- [x] Fully refactored bmi_core.py to support Spanish:
  - bmi_category() now uses i18n for all BMI categories
  - interpret_group() uses i18n for group notes
  - group_display_name() now supports Spanish group names
  - estimate_level() uses i18n for fitness levels
  - build_premium_plan() now has Spanish action and activity tips
  - Updated normalize_lang() to accept Spanish as a valid language
  - Enhanced auto_group() to recognize Spanish terms for gender and pregnancy
- [x] Enhanced web interface with dynamic language switching
- [x] Added Spanish translations for all form labels and UI elements
- [x] Implemented client-side language switching with cookie persistence
- [x] Added language selector with ES/RU/EN options
- [x] Created comprehensive test suite for Spanish language support:
  - Unit tests for i18n parity
  - API endpoint tests for Spanish language
  - End-to-end API tests for Spanish language
  - Web interface tests for Spanish language
  - Complete end-to-end workflow tests
- [x] Updated README with Spanish language information and examples
- [x] Created SPANISH_EXAMPLES.md with detailed curl examples
- [x] Created SPANISH_IMPLEMENTATION_SUMMARY.md documentation

### ✅ Premium Targets API Implementation
- [x] Implemented compact RDA/AI table for key micronutrients (19-50 age group):
  - Fe, Ca, VitD, B12, I, Folate, K, Mg
- [x] Added water guidelines and activity recommendations (150/75 мин/нед)
- [x] Enhanced core/targets.py with BMR/TDEE calculations
- [x] Added macronutrient distribution:
  - Protein (1.6–1.8 г/кг)
  - Fat (0.8–1.0 г/кг)
  - Carbs — from remainder
  - Fiber 25–30 г
  - Water ≈30 мл/кг
- [x] Implemented /api/v1/premium/targets endpoint with Pydantic schemas
- [x] Added comprehensive tests for Premium Targets API:
  - Required micronutrients validation
  - Values in reasonable ranges
  - Loss goal calorie calculations
- [x] Created PREMIUM_TARGETS_EXAMPLE.md with curl examples
- [x] Created PREMIUM_TARGETS_API.md documentation

## In Progress

### ⏳ Additional Language Support
- [ ] Consider adding French language support
- [ ] Consider adding German language support

### ⏳ Enhanced Documentation
- [ ] Create comprehensive API documentation
- [ ] Add user guides for all features
- [ ] Create developer documentation for contributing

### 🌟 Brand Identity & App Design (PulsePlate)
- [ ] Finalize app name: PulsePlate with subtitle "Nutrition • Body • Lifestyle"
- [ ] Design app icon in Figma:
  - Background: Navy #0F172A
  - Plate: White circle with soft turquoise glow (Accent Green #20C997)
  - Fork and knife: Thin lines, white/gray
  - Scales with heart (#FF5D5D) and apple (#20C997)
  - Primary Blue #339FFF for scale pointer
  - Flat style, clean, 20px rounded corners, soft shadow
- [ ] Export app icon (1024×1024 PNG) and generate full iOS App Icon Set
- [ ] Implement color system in tokens.css:
  - Primary Blue #339FFF (intelligence, analytics, science)
  - Accent Green #20C997 (life, nutrition, growth)
  - Heart Red #FF5D5D (pulse, health, energy)
  - Background Navy #0F172A (calm, balance)
  - White/gray for plate and utensils
- [ ] Set up fonts: SF Pro (iOS system) + Inter for numbers
- [ ] Configure SF Symbols and custom SVG icons (heart, apple, scales)
- [ ] Create Lottie splash screen animation:
  - Plate glow, pulsing heart (ECG), bouncing apple, scale needle oscillation
  - 2.7s duration, seamless loop
  - Two versions: splash-lite (≤120KB) and splash-full (≤300KB)
  - Color palette from design tokens
  - Export via Bodymovin from After Effects
  - Integrate in React (lottie-web/react) and Capacitor (iOS webview)

### 🌟 Frontend Development (React + Vite + Capacitor, iOS-first)
- [ ] P0 — Foundation (today/tomorrow):
  - [ ] Design system (tokens): frontend/src/styles/tokens.css with PulsePlate color palette
  - [ ] UI stack: Tailwind + clsx/cva (component variants), fonts (SF Pro/Inter)
  - [ ] Routing: react-router (routes: /, /weekly, /progress, /premium)
  - [ ] API client: api.ts with fetch + error interceptors; Vite proxy /api → :8000
  - [ ] State: lightweight store (zustand) for user parameters (height/weight/sex/age/goal/activity)
  - [ ] i18n: i18next (RU/EN), translation placeholders
  - [ ] Accessibility (A11y): focus rings, contrast, 44×44pt touch targets, semantic roles
  - [ ] Screen "My Plate (MVP)": input form (height/weight/sex/age/activity/goal) → BMI/TDEE cards + "plate" (SVG/grid)
  - [ ] /api/v1/health: API status display on home screen (diagnostics)
- [ ] P1 — Product Value (next):
  - [ ] Charts: recharts (or visx) — weight/calorie/step progress; dark/light theme
  - [ ] Screen "Weekly": 7×(breakfasts/lunches/dinners/snacks) grid, "diet-flags" state (VEG/GF/DAIRY_FREE/LOW_COST)
  - [ ] User profiles: local storage (IndexedDB via idb-keyval) + JSON export/import
  - [ ] Error/empty states: beautiful states for 4xx/5xx/timeout, offline-banner
  - [ ] Skeleton/Loading: for all API requests
  - [ ] Form validation: zod + react-hook-form, proper error messages
  - [ ] UI Tests: Vitest + Testing Library (render/validation/routes)
  - [ ] Logo/icons/splash: SVG logo, iOS icon set, adaptive splash
- [ ] P2 — Polish and iOS:
  - [ ] Capacitor: pnpm cap add ios → Xcode → simulator build
  - [ ] Performance: code splitting, lazy routes, prefetch critical data, vite-plugin-compression
  - [ ] Analytics: privacy-safe (e.g., self-hosted Plausible), basic events (onboarding, plate save, weekly open)
  - [ ] E2E: Playwright (main scenarios: input → calculation → save → transitions)
  - [ ] CI: GitHub Actions — lint, typing, unit/UI tests, build; preview (gh-pages or Vercel) for frontend
  - [ ] ASO package: screenshots 6.1″/6.7″ (light/dark), promo texts, 15–20 sec video screencast

### 🌟 Database Expansion and Integration
- [ ] Research FooDB API/data format and create adapter to enhance phytonutrient data
- [ ] Evaluate WHO Food Composition Database for international food data integration
- [ ] Assess EuroFIR datasets for European regional food data
- [ ] Add phytonutrient fields to unified food database schema
- [ ] Implement international food mapping logic for global database integration
- [ ] Research TheMealDB API integration for international recipe expansion
- [ ] Evaluate dpapathanasiou/recipes JSON collection for regional cuisine data
- [ ] Design regional cuisine classification system for recipe database
- [ ] Investigate AtoZ World Foods database access for cultural context
- [ ] Implement culinary characteristics tagging system for recipes
- [ ] Expand USDA FoodData Central integration to utilize full API capabilities
- [ ] Implement Open Food Facts daily export processing for branded foods
- [ ] Enhance TheMealDB integration to leverage area/category filters
- [ ] Evaluate CalorieNinjas API as backup nutrition data source
- [ ] Expand nutrient schema to include missing vitamins and minerals (A, C, E, K, B-complex, Zinc, Selenium)
- [ ] Implement comprehensive food category expansion (add fruits, dairy, nuts/seeds, herbs/spices)

## Pending Tasks

### 🔜 UI/UX Improvements
- [ ] Add dark mode support to web interface
- [ ] Improve mobile responsiveness
- [ ] Add language-specific formatting for numbers (decimal separators)
- [ ] Add language-specific date/time formatting

### 🔜 Additional Features
- [ ] Implement meal planning functionality
- [ ] Add recipe database integration
- [ ] Create personalized meal suggestions
- [ ] Add progress tracking and visualization
- [ ] Implement export functionality for reports

### 🔜 Testing and Quality Assurance
- [ ] Add property-based testing for core calculations
- [ ] Implement integration tests for all API endpoints
- [ ] Add performance testing
- [ ] Implement security testing
- [ ] Add accessibility testing

### 🔜 Deployment and Operations
- [ ] Set up continuous deployment pipeline
- [ ] Implement monitoring and alerting
- [ ] Add backup and recovery procedures
- [ ] Optimize for cloud deployment
- [ ] Implement rate limiting and security measures

### 🔜 Performance Optimization
- [ ] Optimize database queries
- [ ] Implement caching strategies
- [ ] Reduce API response times
- [ ] Optimize memory usage
- [ ] Implement lazy loading where appropriate

## Future Enhancements

### 💡 Advanced Features
- [ ] Add AI-powered nutrition recommendations
- [ ] Implement personalized workout plans
- [ ] Add social features and community support
- [ ] Create mobile app versions
- [ ] Implement offline functionality

### 💡 Integration Opportunities
- [ ] Integrate with fitness trackers
- [ ] Connect to food delivery services
- [ ] Integrate with healthcare systems
- [ ] Add API marketplace for third-party integrations
- [ ] Implement IoT device connectivity

## Notes

This TODO list is organized by priority and status:
- ✅ Completed tasks
- ⏳ In progress tasks
- 🔜 Pending tasks (next to implement)
- 💡 Future enhancements (ideas for later)

The list will be updated regularly as tasks are completed and new ones are identified.