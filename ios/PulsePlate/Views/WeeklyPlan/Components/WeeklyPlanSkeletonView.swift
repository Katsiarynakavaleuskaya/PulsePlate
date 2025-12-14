import SwiftUI

struct WeeklyPlanSkeletonView: View {
    var body: some View {
        VStack(spacing: 12) {
            RoundedRectangle(cornerRadius: 12).fill(.quaternary).frame(height: 54)
            RoundedRectangle(cornerRadius: 18).fill(.quaternary).frame(height: 120)
            RoundedRectangle(cornerRadius: 18).fill(.quaternary).frame(height: 120)
            RoundedRectangle(cornerRadius: 18).fill(.quaternary).frame(height: 120)
            RoundedRectangle(cornerRadius: 18).fill(.quaternary).frame(height: 100)
            Spacer()
        }
        .padding()
        .redacted(reason: .placeholder)
        .accessibilityHidden(true)
    }
}
