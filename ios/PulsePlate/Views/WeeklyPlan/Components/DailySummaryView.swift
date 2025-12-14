import SwiftUI

struct DailySummaryView: View {
    let macros: MacroTotalsVM

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 10) {
                Text("Daily total").font(.headline)

                Text(macros.kcal.map { "\($0.formatted()) kcal" } ?? "—")
                    .font(.title2)
                    .fontWeight(.semibold)

                ViewThatFits {
                    HStack(spacing: 12) { pills }
                    VStack(alignment: .leading, spacing: 8) { pills }
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Daily total")
        .accessibilityValue(accessibilityValueText)
    }

    private var pills: some View {
        Group {
            summaryPill(label: "Protein", value: macros.proteinG.map { "\($0)g" } ?? "—")
            summaryPill(label: "Fat", value: macros.fatG.map { "\($0)g" } ?? "—")
            summaryPill(label: "Carbs", value: macros.carbsG.map { "\($0)g" } ?? "—")
        }
    }

    private var accessibilityValueText: String {
        let kcalText = macros.kcal.map { "\($0) kilocalories" } ?? "no calories data"
        let p = macros.proteinG.map { "protein \($0) grams" } ?? "protein no data"
        let f = macros.fatG.map { "fat \($0) grams" } ?? "fat no data"
        let c = macros.carbsG.map { "carbs \($0) grams" } ?? "carbs no data"
        return "\(kcalText), \(p), \(f), \(c)"
    }

    private func summaryPill(label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.subheadline).fontWeight(.semibold)
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 10)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(label)
        .accessibilityValue(value)
    }
}
