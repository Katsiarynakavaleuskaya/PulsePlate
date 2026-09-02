import Foundation

enum AppSection: String, CaseIterable, Hashable, Identifiable {
    case home
    case bmi
    case today
    case progress
    case profile

    static let productionSections: [AppSection] = [
        .home,
        .bmi,
        .today,
        .progress,
        .profile,
    ]

    var id: String { rawValue }

    var localizationKey: String {
        switch self {
        case .home:
            "navigation.tab.home"
        case .bmi:
            "navigation.tab.bmi"
        case .today:
            "navigation.tab.today"
        case .progress:
            "navigation.tab.progress"
        case .profile:
            "navigation.tab.profile"
        }
    }

    var systemImage: String {
        switch self {
        case .home:
            "house"
        case .bmi:
            "scalemass"
        case .today:
            "fork.knife"
        case .progress:
            "chart.line.uptrend.xyaxis"
        case .profile:
            "person"
        }
    }

    func localizedTitle(using localization: LocalizationManager) -> String {
        localization.localized(localizationKey)
    }
}
