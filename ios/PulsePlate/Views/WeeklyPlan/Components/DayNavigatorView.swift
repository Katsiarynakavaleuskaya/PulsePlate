import SwiftUI

struct DayNavigatorView: View {
    let dayTitle: String
    let dayIndex: Int
    let totalDays: Int
    let onPrevious: () -> Void
    let onNext: () -> Void

    private var dayIndexText: String {
        "Day \(dayIndex + 1)/\(totalDays)"
    }

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onPrevious) {
                Image(systemName: "chevron.left")
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.bordered)
            .accessibilityLabel("Previous day")

            VStack(spacing: 2) {
                Text(dayTitle)
                    .font(.headline)
                Text(dayIndexText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("\(dayTitle), \(dayIndexText)")

            Button(action: onNext) {
                Image(systemName: "chevron.right")
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.bordered)
            .accessibilityLabel("Next day")
        }
        .padding(.top, 8)
    }
}
