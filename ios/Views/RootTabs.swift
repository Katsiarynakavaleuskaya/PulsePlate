import SwiftUI

struct RootTabs: View {
  var body: some View {
    TabView {
      Text("Home").tabItem { Label("Home", systemImage: "house") }.accessibilityLabel("Home")
      Text("Plate").tabItem { Label("Plate", systemImage: "fork.knife") }.accessibilityLabel("Plate")
      Text("Progress").tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }.accessibilityLabel("Progress")
      Text("Profile").tabItem { Label("Profile", systemImage: "person") }.accessibilityLabel("Profile")
    }
    .dynamicTypeSize(.large ... .accessibility5)
  }
}
