import SwiftUI

struct PlanMetricsView: View {
    let cost: Double
    let adherence: Double
    let shoppingListCount: Int

    // TODO: when Region Catalog / currency settings available — inject currencyCode from environment
    private let currencyCode: String = Locale.current.currency?.identifier ?? "USD"

    private var clampedAdherence: Double {
        min(max(adherence, 0), 1)
    }

    private var moneyText: String {
        cost.formatted(.currency(code: currencyCode).precision(.fractionLength(0)))
    }

    private var adherenceText: String {
        (clampedAdherence * 100).formatted(.number.precision(.fractionLength(0))) + "%"
    }

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 10) {
                Text("Plan metrics")
                    .font(.headline)

                ViewThatFits(in: .horizontal) {
                    HStack(spacing: 12) {
                        MetricCardView(icon: "💰", title: "Estimated cost", value: moneyText)
                        MetricCardView(icon: "⭐", title: "Adherence", value: adherenceText)
                    }

                    VStack(spacing: 12) {
                        MetricCardView(icon: "💰", title: "Estimated cost", value: moneyText)
                        MetricCardView(icon: "⭐", title: "Adherence", value: adherenceText)
                    }
                }

                if shoppingListCount > 0 {
                    Text("Shopping items: \(shoppingListCount)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .accessibilityLabel("Shopping items")
                        .accessibilityValue("\(shoppingListCount)")
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Plan metrics")
        .accessibilityValue("Estimated cost \(moneyText), adherence \(adherenceText)")
    }
}

private struct MetricCardView: View {
    let icon: String
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(icon).font(.title2)
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.headline)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
        .accessibilityValue(value)
    }
}
