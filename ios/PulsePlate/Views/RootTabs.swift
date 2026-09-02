import SwiftUI
import UIKit

struct RootTabs: View {
  @ObservedObject private var localization = LocalizationManager.shared
  @State private var selection: AppSection = .home

  @ViewBuilder
  var body: some View {
    if #available(iOS 18.0, *) {
      systemTabs
        .tabViewStyle(.sidebarAdaptable)
    } else {
      systemTabs
    }
  }

  private var systemTabs: some View {
    TabView(selection: $selection) {
      ForEach(AppSection.productionSections) { section in
        destination(for: section)
          .tabItem {
            Label(
              section.localizedTitle(using: localization),
              systemImage: runtimeSystemImage(for: section)
            )
          }
          .tag(section)
      }
    }
    .environment(\.locale, Locale(identifier: localization.currentLanguage))
    .tint(PPDesignTokens.ColorToken.primary)
  }

  @ViewBuilder
  private func destination(for section: AppSection) -> some View {
    switch section {
    case .home:
      NavigationStack {
        HomeView()
      }
    case .bmi:
      NavigationStack {
        BMICalculatorScreen()
      }
    case .today:
      PlateViewPP()
    case .progress:
      ProgressViewPP()
    case .profile:
      ProfileView()
    }
  }

  private func runtimeSystemImage(for section: AppSection) -> String {
    guard section == .bmi else { return section.systemImage }
    return UIImage(systemName: section.systemImage) == nil ? "gauge" : section.systemImage
  }
}
