import SwiftUI

struct WeeklyCoverageView: View {
    let coverage: [CoverageItemVM]
    let isExpanded: Bool
    let onToggle: () -> Void

    private static let maxVisibleItems = 12
    private static let maxPercentForProgressBar: Double = 300.0

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 10) {
                Button(action: onToggle) {
                    HStack {
                        Text("📊")
                            .accessibilityHidden(true)
                        Text("Weekly Coverage")
                            .font(.headline)
                        Spacer()
                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                            .foregroundStyle(.secondary)
                    }
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Weekly coverage")
                .accessibilityHint(isExpanded ? "Collapse" : "Expand")

                if isExpanded {
                    let topItems = Array(coverage.prefix(Self.maxVisibleItems))

                    VStack(spacing: 10) {
                        ForEach(topItems) { item in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text(item.label).font(.subheadline)
                                    Spacer()
                                    Text("\(item.percent, specifier: "%.0f")%")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                ProgressView(value: min(item.percent, Self.maxPercentForProgressBar), total: Self.maxPercentForProgressBar)
                            }
                            .accessibilityElement(children: .combine)
                            .accessibilityLabel("\(item.label), \(Int(item.percent.rounded())) percent")
                        }
                    }
                    .transition(.opacity)
                }
            }
        }
    }
}
