# iOS API Integration Guide

**Last Updated**: 2025-12-13
**Target**: iOS 15.0+, Swift 5.9+
**Architecture**: SwiftUI + async/await

---

## 🎯 Overview

Complete guide for integrating PulsePlate API into iOS applications with proper subscription tier handling, error management, and offline support.

---

## 📦 Project Setup

### 1. Add Network Layer

Create `Services/APIClient.swift`:

```swift
import Foundation

enum SubscriptionTier: String, Codable {
    case free = "FREE"
    case pro = "PRO"
    case vip = "VIP"
}

enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case invalidAPIKey
    case insufficientTier(required: SubscriptionTier, current: SubscriptionTier)
    case rateLimitExceeded(retryAfter: TimeInterval)
    case serverError(statusCode: Int, message: String?)
    case networkError(Error)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL"
        case .invalidResponse:
            return "Invalid server response"
        case .invalidAPIKey:
            return "Invalid or missing API key. Please check your subscription."
        case .insufficientTier(let required, let current):
            return "This feature requires \(required.rawValue) tier. You currently have \(current.rawValue) tier."
        case .rateLimitExceeded(let retryAfter):
            return "Too many requests. Please try again in \(Int(retryAfter)) seconds."
        case .serverError(let code, let message):
            return message ?? "Server error (code: \(code))"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError:
            return "Failed to decode server response"
        }
    }
}

struct APIErrorResponse: Codable {
    let detail: String
    let errorCode: String?
    let tierRequired: String?
    let tierCurrent: String?

    enum CodingKeys: String, CodingKey {
        case detail
        case errorCode = "error_code"
        case tierRequired = "tier_required"
        case tierCurrent = "tier_current"
    }
}

class APIClient {
    static let shared = APIClient()

    private let baseURL: String
    private let session: URLSession

    private init() {
        #if DEBUG
        // IMPORTANT: localhost won't work on physical devices
        // You need to either:
        // 1. Use your Mac's IP (e.g., "http://192.168.1.100:8000")
        // 2. Add ATS exception to Info.plist for localhost:8000:
        //    <key>NSAppTransportSecurity</key>
        //    <dict>
        //        <key>NSExceptionDomains</key>
        //        <dict>
        //            <key>localhost</key>
        //            <dict>
        //                <key>NSExceptionAllowsInsecureHTTPLoads</key>
        //                <true/>
        //            </dict>
        //        </dict>
        //    </dict>
        // 3. Use port forwarding (device USB to Mac)
        // For simulator, localhost works fine
        self.baseURL = "http://localhost:8000"
        #else
        self.baseURL = "https://api.pulseplate.com"
        #endif

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config)
    }

    // MARK: - Generic Request Methods

    /// Convenience helper for GET requests without body
    func requestGET<T: Decodable>(
        endpoint: String,
        tier: SubscriptionTier? = nil
    ) async throws -> T {
        return try await request(endpoint: endpoint, method: "GET", body: Optional<EmptyBody>.none, tier: tier)
    }

    /// Request without body (for GET/DELETE requests)
    func request<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        tier: SubscriptionTier? = nil
    ) async throws -> T {
        return try await request(endpoint: endpoint, method: method, body: Optional<EmptyBody>.none, tier: tier)
    }

    /// Request with body (for POST/PUT requests)
    func request<T: Decodable, Body: Encodable>(
        endpoint: String,
        method: String = "GET",
        body: Body? = nil,
        tier: SubscriptionTier? = nil
    ) async throws -> T {
        // Build URL using URLComponents for safer query handling
        var urlString = "\(baseURL)\(endpoint)"

        // Parse endpoint to check if it has query params
        if let components = URLComponents(string: urlString) {
            urlString = components.url?.absoluteString ?? urlString
        }

        guard let url = URL(string: urlString) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add API key if tier requires authentication
        if let tier = tier {
            let apiKey = try await getAPIKey(for: tier)
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }

        // Encode body if present
        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        // Execute request
        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }

            // Handle errors
            if httpResponse.statusCode >= 400 {
                try handleErrorResponse(httpResponse, data: data)
            }

            // Decode success response
            do {
                return try JSONDecoder().decode(T.self, from: data)
            } catch {
                throw APIError.decodingError(error)
            }
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.networkError(error)
        }
    }

    // MARK: - Error Handling

    private func handleErrorResponse(_ response: HTTPURLResponse, data: Data) throws {
        let decoder = JSONDecoder()

        // Try to decode error response
        if let errorResponse = try? decoder.decode(APIErrorResponse.self, from: data) {
            switch response.statusCode {
            case 401:
                // 401 = authentication failure (invalid/missing API key)
                throw APIError.invalidAPIKey

            case 403:
                // 403 = authorization failure (valid key but insufficient tier/permissions)
                let required = SubscriptionTier(rawValue: errorResponse.tierRequired ?? "FREE") ?? .free
                let current = SubscriptionTier(rawValue: errorResponse.tierCurrent ?? "FREE") ?? .free
                throw APIError.insufficientTier(required: required, current: current)

            case 429:
                let retryAfter = Double(response.value(forHTTPHeaderField: "Retry-After") ?? "60") ?? 60
                throw APIError.rateLimitExceeded(retryAfter: retryAfter)

            default:
                throw APIError.serverError(statusCode: response.statusCode, message: errorResponse.detail)
            }
        }

        // Fallback for non-JSON errors
        throw APIError.serverError(statusCode: response.statusCode, message: nil)
    }

    // MARK: - API Key Management

    /// Load API key from Config.plist (for development) or environment variable
    private static func loadTestKey(for tier: String) -> String? {
        // 1. Try loading from Config.plist (recommended for dev)
        // Add Config.plist to .gitignore to keep keys private
        if let configPath = Bundle.main.path(forResource: "Config", ofType: "plist"),
           let config = NSDictionary(contentsOfFile: configPath) as? [String: Any],
           let key = config["TEST_\(tier.uppercased())_KEY"] as? String, !key.isEmpty {
            return key
        }

        // 2. Fallback to environment variable (less recommended, but supported)
        if let envKey = ProcessInfo.processInfo.environment["TEST_\(tier.uppercased())_KEY"], !envKey.isEmpty {
            #if DEBUG
            print("⚠️ Using environment variable for \(tier) key. Consider using Config.plist instead.")
            #endif
            return envKey
        }

        // 3. If no key found, log error and return nil
        #if DEBUG
        print("❌ No test \(tier) key found. Create Config.plist with TEST_\(tier.uppercased())_KEY.")
        #endif
        return nil
    }

    private func getAPIKey(for tier: SubscriptionTier) async throws -> String {
        #if DEBUG
        // Development: load from Config.plist (never hardcode keys)
        // Create Config.plist in your project with structure:
        // {
        //   "TEST_PRO_KEY": "your_test_pro_key_here",
        //   "TEST_VIP_KEY": "your_test_vip_key_here"
        // }
        // Add Config.plist to .gitignore!
        switch tier {
        case .free:
            return "" // FREE tier doesn't need API key
        case .pro:
            guard let key = Self.loadTestKey(for: "PRO") else {
                throw APIError.invalidAPIKey
            }
            return key
        case .vip:
            guard let key = Self.loadTestKey(for: "VIP") else {
                throw APIError.invalidAPIKey
            }
            return key
        }
        #else
        // Production: retrieve from Keychain
        guard let key = APIKeyManager.shared.retrieveAPIKey(for: tier) else {
            throw APIError.invalidAPIKey
        }
        return key
        #endif
    }
}

// MARK: - Empty Body Type

private struct EmptyBody: Encodable {}
```

### 2. Create Models

Create `Models/Nutrition.swift`:

```swift
import Foundation

// MARK: - User Profile

struct UserProfile: Codable {
    let sex: Sex
    let age: Int
    let heightCm: Int
    let weightKg: Int
    let activity: ActivityLevel
    let goal: Goal
    let dietFlags: [DietFlag]
    let language: Language

    enum Sex: String, Codable {
        case male, female
    }

    enum ActivityLevel: String, Codable {
        case sedentary, light, moderate, active, veryActive = "very_active"
    }

    enum Goal: String, Codable {
        case loss, maintain, gain
    }

    enum DietFlag: String, Codable {
        case vegetarian, vegan, glutenFree = "gluten_free", dairyFree = "dairy_free", keto, paleo
    }

    enum Language: String, Codable {
        // Supported languages (backend supports en/ru/es only)
        case en, ru, es

        // Future/unsupported languages - will fallback to English
        // case de, fr  // TODO: Enable when backend adds support
    }

    enum CodingKeys: String, CodingKey {
        case sex, age
        case heightCm = "height_cm"
        case weightKg = "weight_kg"
        case activity, goal
        case dietFlags = "diet_flags"
        case language = "lang"
    }
}

// MARK: - Weekly Plan

struct WeeklyPlanRequest: Codable {
    let sex: UserProfile.Sex
    let age: Int
    let heightCm: Int
    let weightKg: Int
    let activity: UserProfile.ActivityLevel
    let goal: UserProfile.Goal
    let dietFlags: [UserProfile.DietFlag]
    let lang: UserProfile.Language

    enum CodingKeys: String, CodingKey {
        case sex, age
        case heightCm = "height_cm"
        case weightKg = "weight_kg"
        case activity, goal
        case dietFlags = "diet_flags"
        case lang
    }
}

struct WeeklyPlanResponse: Codable {
    let dailyMenus: [DailyMenu]
    let weeklyCoverage: [String: Double]
    let shoppingList: [String: Double]
    let totalCost: Double
    let adherenceScore: Double

    enum CodingKeys: String, CodingKey {
        case dailyMenus = "daily_menus"
        case weeklyCoverage = "weekly_coverage"
        case shoppingList = "shopping_list"
        case totalCost = "total_cost"
        case adherenceScore = "adherence_score"
    }
}

struct DailyMenu: Codable, Identifiable {
    var id: String { day }
    let day: String
    let meals: [Meal]
}

struct Meal: Codable, Identifiable {
    var id: String { name }
    let mealType: String
    let name: String
    let kcal: Int
    let proteinG: Double
    let fatG: Double
    let carbsG: Double

    enum CodingKeys: String, CodingKey {
        case mealType = "meal_type"
        case name, kcal
        case proteinG = "protein_g"
        case fatG = "fat_g"
        case carbsG = "carbs_g"
    }
}

// MARK: - VIP Recipe Synthesis

struct RecipeSynthesisRequest: Codable {
    let ingredients: [Ingredient]
    let cuisinePreference: String?
    let difficultyPreference: String?
    let servings: Int

    enum CodingKeys: String, CodingKey {
        case ingredients
        case cuisinePreference = "cuisine_preference"
        case difficultyPreference = "difficulty_preference"
        case servings
    }
}

struct Ingredient: Codable, Identifiable {
    var id: String { name }
    let name: String
    let amount: Double
    let unit: String
}

struct RecipeSynthesisResponse: Codable {
    let recipe: SynthesizedRecipe
}

struct SynthesizedRecipe: Codable, Identifiable {
    var id: String { name }
    let name: String
    let instructions: [String]
    let nutrition: RecipeNutrition
    let cookTimeMin: Int
    let difficulty: String

    enum CodingKeys: String, CodingKey {
        case name, instructions, nutrition, difficulty
        case cookTimeMin = "cook_time_min"
    }
}

struct RecipeNutrition: Codable {
    let kcal: Int
    let proteinG: Double
    let fatG: Double
    let carbsG: Double
    let vitamins: [String: Double]?

    enum CodingKeys: String, CodingKey {
        case kcal
        case proteinG = "protein_g"
        case fatG = "fat_g"
        case carbsG = "carbs_g"
        case vitamins
    }
}
```

### 3. Create Service Layer

Create `Services/NutritionService.swift`:

```swift
import Foundation

class NutritionService {
    private let client = APIClient.shared

    // MARK: - FREE Tier (No API Key)

    func searchFoods(query: String) async throws -> [Food] {
        // Use URLComponents for safer query parameter handling
        var components = URLComponents(string: "/api/v1/foods/search")
        components?.queryItems = [URLQueryItem(name: "q", value: query)]

        guard let query = components?.percentEncodedQuery else {
            throw APIError.invalidURL
        }

        let fullEndpoint = "/api/v1/foods/search?" + query
        // Use convenience helper for GET requests
        return try await client.requestGET(endpoint: fullEndpoint)
    }

    func searchRecipes(query: String) async throws -> [Recipe] {
        // Use URLComponents for safer query parameter handling
        var components = URLComponents(string: "/api/v1/recipes/search")
        components?.queryItems = [URLQueryItem(name: "q", value: query)]

        guard let query = components?.percentEncodedQuery else {
            throw APIError.invalidURL
        }

        let fullEndpoint = "/api/v1/recipes/search?" + query
        // Use convenience helper for GET requests
        return try await client.requestGET(endpoint: fullEndpoint)
    }

    // MARK: - PRO Tier (Requires PRO API Key)

    func generateWeeklyPlan(profile: UserProfile) async throws -> WeeklyPlanResponse {
        let request = WeeklyPlanRequest(
            sex: profile.sex,
            age: profile.age,
            heightCm: profile.heightCm,
            weightKg: profile.weightKg,
            activity: profile.activity,
            goal: profile.goal,
            dietFlags: profile.dietFlags,
            lang: profile.language
        )

        return try await client.request(
            endpoint: "/api/v1/pro/meal/weekly",
            method: "POST",
            body: request,
            tier: .pro
        )
    }

    // MARK: - VIP Tier (Requires VIP API Key)

    func synthesizeRecipe(ingredients: [Ingredient], cuisine: String? = nil, difficulty: String? = nil, servings: Int = 2) async throws -> SynthesizedRecipe {
        let request = RecipeSynthesisRequest(
            ingredients: ingredients,
            cuisinePreference: cuisine,
            difficultyPreference: difficulty,
            servings: servings
        )

        let response: RecipeSynthesisResponse = try await client.request(
            endpoint: "/api/v1/vip/recipes/synthesize",
            method: "POST",
            body: request,
            tier: .vip
        )

        return response.recipe
    }

    func generateShoppingList(weekPlan: WeeklyPlanResponse) async throws -> ShoppingListResponse {
        return try await client.request(
            endpoint: "/api/v1/vip/shoplist/weekly",
            method: "POST",
            body: weekPlan,
            tier: .vip
        )
    }
}

// Stub types for completeness
struct Food: Codable, Identifiable {
    let id: Int
    let name: String
}

struct Recipe: Codable, Identifiable {
    let id: Int
    let name: String
}

struct ShoppingListResponse: Codable {
    let items: [String: Double]
}
```

---

## 🔐 Secure API Key Storage

Create `Services/APIKeyManager.swift`:

**IMPORTANT**: For development, create a `Config.plist` file in your Xcode project with test API keys and add it to `.gitignore` to prevent committing sensitive keys:

```xml
<!-- Config.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>TEST_PRO_KEY</key>
    <string>your_test_pro_key_here</string>
    <key>TEST_VIP_KEY</key>
    <string>your_test_vip_key_here</string>
</dict>
</plist>
```

**Add to `.gitignore`**:

```gitignore
# Never commit Config.plist with test keys
**/Config.plist
```

**Production Keychain Storage**:

```swift
import Foundation
import Security

class APIKeyManager {
    static let shared = APIKeyManager()

    private let service = "com.pulseplate.apikeys"

    private init() {}

    // MARK: - Store API Key

    func storeAPIKey(_ key: String, for tier: SubscriptionTier) throws {
        let account = "api_key_\(tier.rawValue.lowercased())"

        guard let data = key.data(using: .utf8) else {
            throw KeychainError.encodingError
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data,
            // RECOMMENDED: Use WhenUnlockedThisDeviceOnly for maximum security
            // - API keys are only accessible when device is unlocked
            // - Keys will NOT sync via iCloud Keychain (device-only)
            // - Keys will NOT be included in device backups
            // - Most secure option for sensitive credentials
            // Alternative: kSecAttrAccessibleAfterFirstUnlock (syncs via iCloud, included in backups)
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        // Delete existing item
        SecItemDelete(query as CFDictionary)

        // Add new item
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.unhandledError(status: status)
        }
    }

    // MARK: - Retrieve API Key

    func retrieveAPIKey(for tier: SubscriptionTier) -> String? {
        let account = "api_key_\(tier.rawValue.lowercased())"

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let key = String(data: data, encoding: .utf8) else {
            return nil
        }

        return key
    }

    // MARK: - Delete API Key

    func deleteAPIKey(for tier: SubscriptionTier) throws {
        let account = "api_key_\(tier.rawValue.lowercased())"

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.unhandledError(status: status)
        }
    }

    // MARK: - Clear All Keys

    func clearAllAPIKeys() throws {
        for tier in [SubscriptionTier.pro, .vip] {
            try? deleteAPIKey(for: tier)
        }
    }
}

enum KeychainError: Error {
    case encodingError
    case unhandledError(status: OSStatus)
}
```

---

## 💰 In-App Purchase Integration

Create `Services/SubscriptionManager.swift`:

```swift
import StoreKit
import OSLog  // For Logger

@MainActor
class SubscriptionManager: ObservableObject {
    static let shared = SubscriptionManager()

    @Published var currentTier: SubscriptionTier = .free
    @Published var products: [Product] = []
    @Published var purchasedProductIDs: Set<String> = []

    private let productIDs: Set<String> = [
        "com.pulseplate.subscription.pro.monthly",
        "com.pulseplate.subscription.vip.monthly"
    ]

    private var updateListenerTask: Task<Void, Never>?

    private init() {
        updateListenerTask = listenForTransactions()
        Task {
            await loadProducts()
            await updateSubscriptionStatus()
        }
    }

    deinit {
        updateListenerTask?.cancel()
    }

    // MARK: - Load Products

    func loadProducts() async {
        do {
            products = try await Product.products(for: productIDs)
                .sorted { $0.price < $1.price }
        } catch {
            // Production-ready logging (iOS 15.0+ deployment target)
            Logger(subsystem: "com.pulseplate", category: "IAP").error("Failed to load products: \(error.localizedDescription)")
        }
    }

    // MARK: - Purchase

    func purchase(_ product: Product) async throws {
        let result = try await product.purchase()

        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            await updateSubscriptionStatus()
            await transaction.finish()

            // Send receipt to backend for API key
            try await validateReceipt(transaction)

        case .userCancelled:
            break

        case .pending:
            break

        @unknown default:
            break
        }
    }

    // MARK: - Restore Purchases

    func restorePurchases() async {
        for await result in Transaction.currentEntitlements {
            guard case .verified(let transaction) = result else {
                continue
            }

            if transaction.revocationDate == nil {
                purchasedProductIDs.insert(transaction.productID)
            }
        }

        await updateSubscriptionStatus()
    }

    // MARK: - Update Status

    private func updateSubscriptionStatus() async {
        var highestTier: SubscriptionTier = .free

        for await result in Transaction.currentEntitlements {
            guard case .verified(let transaction) = result else {
                continue
            }

            if transaction.revocationDate == nil {
                if transaction.productID.contains("vip") {
                    highestTier = .vip
                } else if transaction.productID.contains("pro") && highestTier != .vip {
                    highestTier = .pro
                }
            }
        }

        currentTier = highestTier
    }

    // MARK: - Transaction Listener

    private func listenForTransactions() -> Task<Void, Never> {
        // Use regular Task instead of detached to inherit MainActor context
        // and respect parent task cancellation
        return Task { [weak self] in
            for await result in Transaction.updates {
                guard let self = self else { return }

                // Check for cancellation
                if Task.isCancelled { return }

                guard case .verified(let transaction) = result else {
                    continue
                }

                await self.updateSubscriptionStatus()
                await transaction.finish()
            }
        }
    }

    // MARK: - Receipt Validation

    private func validateReceipt(_ transaction: Transaction) async throws {
        // Get receipt data
        guard let receiptURL = Bundle.main.appStoreReceiptURL,
              let receiptData = try? Data(contentsOf: receiptURL) else {
            throw SubscriptionError.noReceipt
        }

        let base64Receipt = receiptData.base64EncodedString()

        // Send to backend (future endpoint)
        struct ReceiptValidationRequest: Codable {
            let receiptData: String
            let platform: String
            let bundleId: String

            enum CodingKeys: String, CodingKey {
                case receiptData = "receipt_data"
                case platform
                case bundleId = "bundle_id"
            }
        }

        struct ReceiptValidationResponse: Codable {
            let apiKey: String
            let tier: String
            let expiresAt: String

            enum CodingKeys: String, CodingKey {
                case apiKey = "api_key"
                case tier
                case expiresAt = "expires_at"
            }
        }

        let request = ReceiptValidationRequest(
            receiptData: base64Receipt,
            platform: "ios",
            bundleId: Bundle.main.bundleIdentifier ?? ""
        )

        // TODO: Uncomment when backend endpoint is ready
        /*
        let response: ReceiptValidationResponse = try await APIClient.shared.request(
            endpoint: "/api/v1/subscriptions/validate",
            method: "POST",
            body: request
        )

        // Store API key
        if let tier = SubscriptionTier(rawValue: response.tier) {
            try APIKeyManager.shared.storeAPIKey(response.apiKey, for: tier)
        }
        */
    }

    // MARK: - Verification

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw SubscriptionError.failedVerification
        case .verified(let safe):
            return safe
        }
    }
}

enum SubscriptionError: Error {
    case noReceipt
    case failedVerification
}
```

---

## 🎨 SwiftUI Views

Create `Views/SubscriptionView.swift`:

```swift
import SwiftUI
import StoreKit

struct SubscriptionView: View {
    @StateObject private var subscriptionManager = SubscriptionManager.shared
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Current Tier
                    currentTierCard

                    // Product Cards
                    ForEach(subscriptionManager.products, id: \.id) { product in
                        ProductCard(product: product) {
                            await purchaseProduct(product)
                        }
                    }

                    // Restore Button
                    Button("Restore Purchases") {
                        Task {
                            await subscriptionManager.restorePurchases()
                        }
                    }
                    .padding()
                }
                .padding()
            }
            .navigationTitle("Subscriptions")
            .alert("Error", isPresented: Binding(
                get: { errorMessage != nil },
                set: { if !$0 { errorMessage = nil } }
            )) {
                Button("OK") {
                    errorMessage = nil
                }
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }

    private var currentTierCard: some View {
        VStack(spacing: 8) {
            Text("Current Plan")
                .font(.caption)
                .foregroundColor(.secondary)

            Text(subscriptionManager.currentTier.rawValue)
                .font(.title)
                .fontWeight(.bold)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color.blue.opacity(0.1))
        .cornerRadius(12)
    }

    private func purchaseProduct(_ product: Product) async {
        isLoading = true
        defer { isLoading = false }

        do {
            try await subscriptionManager.purchase(product)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct ProductCard: View {
    let product: Product
    let onPurchase: () async -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(product.displayName)
                .font(.headline)

            Text(product.description)
                .font(.subheadline)
                .foregroundColor(.secondary)

            HStack {
                Text(product.displayPrice)
                    .font(.title2)
                    .fontWeight(.bold)

                Spacer()

                Button("Subscribe") {
                    Task {
                        await onPurchase()
                    }
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(radius: 2)
    }
}
```

---

## ✅ Complete Usage Example

Create `ViewModels/WeeklyPlanViewModel.swift`:

```swift
import SwiftUI

@MainActor
class WeeklyPlanViewModel: ObservableObject {
    @Published var weeklyPlan: WeeklyPlanResponse?
    @Published var isLoading = false
    @Published var error: APIError?

    private let nutritionService = NutritionService()

    func generatePlan(for profile: UserProfile) async {
        isLoading = true
        error = nil

        do {
            weeklyPlan = try await nutritionService.generateWeeklyPlan(profile: profile)
        } catch let apiError as APIError {
            error = apiError
        } catch {
            error = .networkError(error)
        }

        isLoading = false
    }
}

struct WeeklyPlanView: View {
    @StateObject private var viewModel = WeeklyPlanViewModel()

    let userProfile: UserProfile

    var body: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Generating your weekly plan...")
            } else if let error = viewModel.error {
                ErrorView(error: error) {
                    Task {
                        await viewModel.generatePlan(for: userProfile)
                    }
                }
            } else if let plan = viewModel.weeklyPlan {
                PlanDetailView(plan: plan)
            } else {
                EmptyStateView {
                    Task {
                        await viewModel.generatePlan(for: userProfile)
                    }
                }
            }
        }
        .navigationTitle("Weekly Plan")
        .task {
            await viewModel.generatePlan(for: userProfile)
        }
    }
}

struct ErrorView: View {
    let error: APIError
    let retry: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundColor(.orange)

            Text(error.errorDescription ?? "Unknown error")
                .multilineTextAlignment(.center)

            if case .insufficientTier = error {
                NavigationLink("Upgrade Subscription") {
                    SubscriptionView()
                }
                .buttonStyle(.borderedProminent)
            } else {
                Button("Retry", action: retry)
                    .buttonStyle(.bordered)
            }
        }
        .padding()
    }
}

struct EmptyStateView: View {
    let generatePlan: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "calendar")
                .font(.largeTitle)
                .foregroundColor(.secondary)

            Text("No weekly plan yet")
                .font(.headline)

            Button("Generate Plan", action: generatePlan)
                .buttonStyle(.borderedProminent)
        }
    }
}

struct PlanDetailView: View {
    let plan: WeeklyPlanResponse

    var body: some View {
        List {
            Section("Weekly Summary") {
                HStack {
                    Text("Total Cost")
                    Spacer()
                    Text("$\(plan.totalCost, specifier: "%.2f")")
                        .fontWeight(.bold)
                }

                HStack {
                    Text("Adherence Score")
                    Spacer()
                    Text("\(Int(plan.adherenceScore * 100))%")
                        .fontWeight(.bold)
                        .foregroundColor(plan.adherenceScore > 0.8 ? .green : .orange)
                }
            }

            Section("Daily Menus") {
                ForEach(plan.dailyMenus) { dailyMenu in
                    NavigationLink(dailyMenu.day.capitalized) {
                        DayDetailView(dailyMenu: dailyMenu)
                    }
                }
            }
        }
    }
}

struct DayDetailView: View {
    let dailyMenu: DailyMenu

    var body: some View {
        List(dailyMenu.meals) { meal in
            VStack(alignment: .leading, spacing: 8) {
                Text(meal.name)
                    .font(.headline)

                Text(meal.mealType.capitalized)
                    .font(.caption)
                    .foregroundColor(.secondary)

                HStack {
                    MacroLabel(name: "Kcal", value: "\(meal.kcal)")
                    MacroLabel(name: "P", value: "\(Int(meal.proteinG))g")
                    MacroLabel(name: "F", value: "\(Int(meal.fatG))g")
                    MacroLabel(name: "C", value: "\(Int(meal.carbsG))g")
                }
            }
            .padding(.vertical, 4)
        }
        .navigationTitle(dailyMenu.day.capitalized)
    }
}

struct MacroLabel: View {
    let name: String
    let value: String

    var body: some View {
        VStack(spacing: 2) {
            Text(name)
                .font(.caption2)
                .foregroundColor(.secondary)
            Text(value)
                .font(.caption)
                .fontWeight(.medium)
        }
    }
}
```

---

## 🧪 Testing

### Unit Tests

Create `Tests/APIClientTests.swift`:

```swift
import XCTest
@testable import PulsePlate

final class APIClientTests: XCTestCase {
    var client: APIClient!

    override func setUp() {
        super.setUp()
        // Create fresh APIClient instance for each test to avoid shared state pollution
        // In production code, consider dependency injection instead of singleton
        client = APIClient.shared
    }

    override func tearDown() {
        super.tearDown()
        // Reset shared state if using singleton pattern
        // For better isolation, consider protocol-based mocking of APIClient
        client = nil
    }

    func testFreeEndpointSucceeds() async throws {
        // Test FREE tier endpoint (no API key)
        // Note: This test relies on external API - consider mocking for determinism
        let foods: [Food] = try await client.requestGET(
            endpoint: "/api/v1/foods/search?q=chicken"
        )

        // Validate response structure instead of assuming non-empty results
        // Empty results are valid if no foods match the query
        for food in foods {
            // Verify required fields are present
            XCTAssertGreaterThan(food.id, 0, "Food ID must be positive")
            XCTAssertFalse(food.name.isEmpty, "Food name must not be empty")
        }
    }

    func testProEndpointWithoutKeyFails() async {
        // TODO: Replace with mock APIClient for deterministic testing
        // Current implementation depends on external API behavior
        do {
            let _: WeeklyPlanResponse = try await client.request(
                endpoint: "/api/v1/pro/meal/weekly",
                method: "POST",
                tier: nil // No API key
            )
            XCTFail("Should have thrown error")
        } catch APIError.invalidAPIKey {
            // Expected: authentication failure (401)
        } catch {
            XCTFail("Wrong error type: \(error)")
        }
    }
}

// MARK: - Mock APIClient (Recommended)

/// Protocol-based approach for better testability
protocol APIClientProtocol {
    func request<T: Decodable, Body: Encodable>(
        endpoint: String,
        method: String,
        body: Body?,
        tier: SubscriptionTier?
    ) async throws -> T
}

/// Mock implementation for deterministic testing
class MockAPIClient: APIClientProtocol {
    var mockResponse: Any?
    var mockError: Error?

    func request<T: Decodable, Body: Encodable>(
        endpoint: String,
        method: String,
        body: Body? = nil,
        tier: SubscriptionTier? = nil
    ) async throws -> T {
        if let error = mockError {
            throw error
        }

        guard let response = mockResponse as? T else {
            throw APIError.invalidResponse
        }

        return response
    }
}

// Example usage in tests:
// let mockClient = MockAPIClient()
// mockClient.mockResponse = [Food(id: 1, name: "Chicken")]
// let foods: [Food] = try await mockClient.request(endpoint: "...", method: "GET")
```

---

## 📚 References

- **Mobile API Migration Guide**: `MOBILE_API_MIGRATION_GUIDE.md`
- **Endpoint Audit**: `ENDPOINT_AUDIT_MOBILE_FOCUS.md`
- **API Documentation**: <http://localhost:8000/docs> (Swagger UI)

---

## 💡 Best Practices

1. **Always handle tier errors gracefully** - Prompt users to upgrade when needed
2. **Cache API responses** - Reduce network calls and improve offline experience
3. **Store API keys securely** - Use Keychain with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`, never UserDefaults
4. **Implement retry logic** - Handle transient network errors
5. **Monitor subscription status** - Listen for transaction updates
6. **Never hardcode API keys** - Use environment variables or Config.plist for development keys
7. **Use URLComponents** - Build URLs safely to avoid encoding issues
8. **Implement offline-first caching for critical endpoints** - Cache responses locally using URLCache or custom persistence, serve cached data when network is unavailable, and sync/update the cache when connectivity is restored to ensure seamless user experience during network interruptions

---

**Questions?** See `MOBILE_API_MIGRATION_GUIDE.md` or open an issue on GitHub.
