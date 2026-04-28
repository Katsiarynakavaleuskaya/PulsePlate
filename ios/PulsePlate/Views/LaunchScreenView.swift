import SwiftUI

private enum LaunchScreenMetrics {
    static let logoSize: CGFloat = 180
}

struct LaunchScreenView: View {
    var body: some View {
        ZStack {
            PPDesignTokens.Brand.navy
                .ignoresSafeArea()
            VStack {
                Image("FitChef")
                    .resizable()
                    .scaledToFit()
                    .frame(width: LaunchScreenMetrics.logoSize, height: LaunchScreenMetrics.logoSize)
                Text("PulsePlate")
                    .ppStyle(.heading, color: .primary)
                    .padding(.top, PPDesignTokens.Spacing.large)
            }
        }
    }
}

#Preview {
    LaunchScreenView()
}
