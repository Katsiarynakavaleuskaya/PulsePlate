import SwiftUI

struct MealSectionView: View {
    let section: MealSectionVM
    @State private var isExpanded: Bool = true

    var body: some View {
        GlassCard {
            VStack(spacing: 0) {
                Button {
                    withAnimation(.snappy(duration: 0.2)) { isExpanded.toggle() }
                } label: {
                    header
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(accessibilityHeaderLabel)
                .accessibilityValue(isExpanded ? "Expanded" : "Collapsed")
                .accessibilityHint(isExpanded ? "Collapse section" : "Expand section")

                if isExpanded {
                    bodyContent
                        .padding(.horizontal, 14)
                        .padding(.bottom, 14)
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            Text(section.mealType.emoji).font(.title3)

            VStack(alignment: .leading, spacing: 2) {
                Text(section.title).font(.headline)
                Text(section.kcal.map { "\($0) kcal" } ?? "—")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                .foregroundStyle(.secondary)
                .imageScale(.medium)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }

    @ViewBuilder
    private var bodyContent: some View {
        VStack(alignment: .leading, spacing: 10) {
            if section.items.isEmpty {
                Text("No items")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .accessibilityLabel("No items in this section")
            } else {
                ForEach(section.items) { item in
                    HStack(alignment: .top, spacing: 10) {
                        Circle()
                            .fill(.secondary.opacity(0.6))
                            .frame(width: 6, height: 6)
                            .padding(.top, 7)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.name).font(.subheadline)
                            if let p = item.portions {
                                Text("Portions: \(p, specifier: "%.1f")")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                    }
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }

    private var accessibilityHeaderLabel: String {
        let kcalText = section.kcal.map { "\($0) kilocalories" } ?? "calories not available"
        return "\(section.title), \(kcalText)"
    }
}
