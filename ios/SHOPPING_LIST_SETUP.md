# Shopping List Integration Setup

## 🎯 Overview

Shopping List Generator экран интегрирован в Debug Tools вкладку (только для DEBUG builds).

## 📱 Access

1. Запустите приложение в DEBUG режиме
2. Откройте вкладку **Debug** (иконка молотка)
3. Выберите **Shopping List Generator**

## ⚙️ Configuration

### Backend URL

**Development:**
- Default: `http://localhost:8000`
- Настраивается через Xcode environment variables:
  - Product → Scheme → Edit Scheme → Run → Environment Variables
  - Добавьте: `BASE_URL` = `http://<your-local-ip>:8000`

**Production:**
- Hardcoded: `https://api.pulseplate.com`
- Автоматически используется в Release builds

### PRO API Key

**Development / Production:**
- Runtime source: **Keychain only**
- Xcode `PRO_API_KEY` environment variable is **not** used for runtime access
- Load the key via the in-app path:
  - **PRO Settings → Debug Tools → Keychain**
- Tests and previews may still use explicitly injected providers, but app runtime does not fall back to env vars

## 📋 Files Structure

```
ios/PulsePlate/
├── Services/
│   ├── AppConfig.swift                     # Base URL configuration
│   ├── ProKeyProvider.swift                # Keychain-only API key provider
│   └── DefaultShoppingListService.swift    # Network service
├── Models/ShoppingList/
│   ├── ShoppingListDTO.swift               # Backend contract DTOs
│   ├── ShoppingListAdapter.swift           # DTO → ViewData adapter
│   └── ShoppingListStubPlan.swift          # Minimal test plan data
├── ViewModels/
│   └── ShoppingListReaderViewModel.swift   # @MainActor state management
├── Views/
│   └── DebugToolsScreen.swift              # Debug menu with config display
└── Screens/
    └── ShoppingListReaderScreen.swift      # Shopping list UI
```

## 🧪 Testing Locally

1. **Start backend:**
   ```bash
   cd backend
   uvicorn app:app --reload --port 8000
   ```

2. **Configure Xcode scheme:**
   - Edit Scheme → Environment Variables
   - `BASE_URL` = `http://localhost:8000` (or your local IP for device testing)

3. **Load a PRO key in app runtime:**
   - Open **PRO Settings → Debug Tools → Keychain**
   - Add your test PRO key there

4. **Run app:**
   - Debug → Debug Tools → Shopping List Generator

5. **Expected response:**
   - Should show 3 items (oats, banana, milk)
   - Categories: grains, fruits, dairy
   - No warnings (valid stub data)

## 🔍 Debugging

**Check configuration:**
- Open Debug Tools screen
- Configuration section shows current BASE_URL and API key status

**Common issues:**
- Missing API key → Shows "Not configured" (orange); load a key via **PRO Settings → Debug Tools → Keychain**
- Invalid URL → App crashes with clear fatalError message (DEBUG only)
- Backend unreachable → Network error displayed in UI

## 🚀 Next Steps

- [ ] Add warnings sheet UI
- [ ] Add empty state handling
- [ ] Add pull-to-refresh
- [ ] Wire into production navigation flow (remove DEBUG-only constraint)

## 📝 Notes

- Debug вкладка **автоматически скрывается** в Release builds (`#if DEBUG`)
- Stub plan data соответствует backend contract (minimal valid daily_menus)
- Все localization keys уже добавлены (EN/RU/ES)
- Runtime PRO access is Keychain-backed; do not rely on Xcode environment variables for secrets
