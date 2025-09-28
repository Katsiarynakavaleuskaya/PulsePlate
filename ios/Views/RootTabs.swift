import SwiftUI

struct RootTabs: View {
  var body: some View {
    TabView {
      HomeView().tabItem { Label("Home", systemImage: "house") }
      PlateViewPP().tabItem { Label("Plate", systemImage: "fork.knife") }
      ProgressViewPP().tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }
      ProfileView().tabItem { Label("Profile", systemImage: "person") }
    }
    .dynamicTypeSize(.large ... .accessibility5)
  }
}
