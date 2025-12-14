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

    private var isFirstDay: Bool {
        dayIndex <= 0
    }

    private var isLastDay: Bool {
        dayIndex >= totalDays - 1
    }

    var body: some View {
        HStack(spacing: 12) {
            Button(action: {
                guard !isFirstDay else { return }
                onPrevious()
            }) {
                Image(systemName: "chevron.left")
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.bordered)
            .accessibilityLabel("Previous day")
            .disabled(isFirstDay)

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

            Button(action: {
                guard !isLastDay else { return }
                onNext()
            }) {
                Image(systemName: "chevron.right")
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.bordered)
            .accessibilityLabel("Next day")
            .disabled(isLastDay)
        }
        .padding(.top, 8)
    }
}
