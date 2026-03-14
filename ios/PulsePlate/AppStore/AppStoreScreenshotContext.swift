import Foundation
import SwiftUI

enum AppStoreScreenshotScenario: String, CaseIterable {
    case welcome
    case home
    case plate
    case paywall
    case profile
    case healthPermission = "health_permission"

    var accessibilityIdentifier: String {
        switch self {
        case .welcome:
            return "appstore.welcome.screen"
        case .home:
            return "appstore.home.screen"
        case .plate:
            return "appstore.plate.screen"
        case .paywall:
            return "appstore.paywall.screen"
        case .profile:
            return "appstore.profile.screen"
        case .healthPermission:
            return "appstore.health_permission.screen"
        }
    }
}

enum AppStoreScreenshotContext {
    private static let enabledArgument = "-appstore-screenshot-mode"
    private static let scenarioArgument = "-appstore-screenshot-scenario"
    private static let enabledEnvironmentKey = "APPSTORE_SCREENSHOT_MODE"

    static var isEnabled: Bool {
        let processInfo = ProcessInfo.processInfo
        return processInfo.arguments.contains(enabledArgument)
            || processInfo.environment[enabledEnvironmentKey] == "1"
    }

    static var currentScenario: AppStoreScreenshotScenario? {
        guard isEnabled else { return nil }

        if ProcessInfo.processInfo.arguments.contains(scenarioArgument) {
            guard let rawScenario = argumentValue(for: scenarioArgument) else {
                preconditionFailure("Missing value for \(scenarioArgument).")
            }
            guard let scenario = AppStoreScreenshotScenario(rawValue: rawScenario) else {
                let supportedScenarios = AppStoreScreenshotScenario.allCases.map(\.rawValue).joined(separator: ", ")
                preconditionFailure("Unsupported \(scenarioArgument) value '\(rawScenario)'. Allowed: \(supportedScenarios)")
            }
            return scenario
        }

        return nil
    }

    static var previewProKey: String? {
        guard isEnabled else { return nil }

        return "appstore-preview-key"
    }

    static func bootstrapIfNeeded() {
        guard isEnabled else { return }

        let userDefaults = UserDefaults.standard
        let scenario = currentScenario ?? .home

        // RU: Для App Store automation фиксируем детерминированное состояние без реальных данных.
        // EN: App Store automation always runs against deterministic seeded state only.
        userDefaults.set(languageCode, forKey: AppStorageKeys.appLanguage)
        userDefaults.set(scenario != .welcome, forKey: "has_seen_welcome_v1")
        userDefaults.set("female", forKey: "pro_profile_sex")
        userDefaults.set("29", forKey: "pro_profile_age")
        userDefaults.set("170", forKey: "pro_profile_height_cm")
        userDefaults.set("65", forKey: "pro_profile_weight_kg")
        userDefaults.set("moderate", forKey: "pro_profile_activity")
        userDefaults.set("maintain", forKey: "pro_profile_goal")

    }

    static func scenarioView() -> AnyView? {
        guard isEnabled else { return nil }
        let scenario = currentScenario ?? .home

        switch scenario {
        case .welcome:
            return AnyView(
                WelcomeFlowView(onCompleted: {})
                    .appStoreScreenshotRoot(scenario.accessibilityIdentifier)
            )
        case .home:
            return AnyView(
                NavigationStack {
                    HomeView()
                }
                .appStoreScreenshotRoot(scenario.accessibilityIdentifier)
            )
        case .plate:
            return AnyView(
                PlateViewPP()
                    .appStoreScreenshotRoot(scenario.accessibilityIdentifier)
            )
        case .paywall:
            return AnyView(
                NavigationStack {
                    AppStorePaywallPreviewView()
                }
                .appStoreScreenshotRoot(scenario.accessibilityIdentifier)
            )
        case .profile:
            return AnyView(
                ProfileView()
                    .appStoreScreenshotRoot(scenario.accessibilityIdentifier)
            )
        case .healthPermission:
            return AnyView(
                NavigationStack {
                    AppStoreHealthPermissionPreviewView()
                }
                .appStoreScreenshotRoot(scenario.accessibilityIdentifier)
            )
        }
    }

    private static var languageCode: String {
        let rawLanguage = Locale.preferredLanguages.first
            ?? "en"
        let normalized = rawLanguage.replacingOccurrences(of: "_", with: "-").lowercased()

        if normalized.hasPrefix("ru") {
            return "ru"
        }
        if normalized.hasPrefix("es") {
            return "es"
        }
        return "en"
    }

    private static func argumentValue(for argument: String) -> String? {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: argument), arguments.indices.contains(index + 1) else {
            return nil
        }
        let value = arguments[index + 1].trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, !value.hasPrefix("-") else {
            return nil
        }
        return value
    }
}

extension View {
    func appStoreScreenshotRoot(_ identifier: String) -> some View {
        accessibilityIdentifier(identifier)
    }
}

private struct AppStorePaywallPreviewView: View {
    @ObservedObject private var localization = LocalizationManager.shared

    private struct PreviewPlan: Identifiable {
        let id: String
        let title: String
        let price: String
        let badge: String
    }

    private var plans: [PreviewPlan] {
        [
            PreviewPlan(
                id: "monthly",
                title: localization.localized("appstore.paywall.plan.monthly.title"),
                price: localization.localized("appstore.paywall.plan.monthly.price"),
                badge: localization.localized("appstore.paywall.plan.monthly.badge")
            ),
            PreviewPlan(
                id: "yearly",
                title: localization.localized("appstore.paywall.plan.yearly.title"),
                price: localization.localized("appstore.paywall.plan.yearly.price"),
                badge: localization.localized("appstore.paywall.plan.yearly.badge")
            )
        ]
    }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text(localization.localized("appstore.paywall.title"))
                        .font(.title3.weight(.semibold))
                    Text(localization.localized("appstore.paywall.subtitle"))
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 6)
            }

            Section(localization.localized("appstore.paywall.section.plans")) {
                ForEach(plans) { plan in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(plan.title)
                            Text(plan.price)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Text(plan.badge)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.blue)
                    }
                }
            }

            Section {
                Button(localization.localized("appstore.paywall.restore")) {}
                    .disabled(true)
            }
        }
        .navigationTitle(localization.localized("appstore.paywall.navigation_title"))
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct AppStoreHealthPermissionPreviewView: View {
    @ObservedObject private var localization = LocalizationManager.shared

    private var bulletPoints: [String] {
        [
            localization.localized("appstore.health_permission.bullet.read"),
            localization.localized("appstore.health_permission.bullet.progress"),
            localization.localized("appstore.health_permission.bullet.optional")
        ]
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                GlassCard {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(localization.localized("appstore.health_permission.title"))
                            .font(.title2.bold())
                            .foregroundStyle(Color.textPrimary)

                        Text(localization.localized("appstore.health_permission.subtitle"))
                            .font(.subheadline)
                            .foregroundStyle(Color.textSecondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                GlassCard {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(localization.localized("appstore.health_permission.section"))
                            .font(.headline)
                            .foregroundStyle(Color.textPrimary)

                        ForEach(bulletPoints, id: \.self) { point in
                            Label(point, systemImage: "checkmark.circle.fill")
                                .foregroundStyle(Color.textSecondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                Button(localization.localized("appstore.health_permission.cta")) {}
                    .buttonStyle(.borderedProminent)
                    .disabled(true)
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 24)
        }
        .background(Color.navy.ignoresSafeArea())
        .navigationTitle(localization.localized("appstore.health_permission.navigation_title"))
        .navigationBarTitleDisplayMode(.inline)
    }
}
