import SwiftUI

struct ShoppingListReaderScreen: View {
    @StateObject private var vm: ShoppingListReaderViewModel

    private let planData: ShoppingPlan?
    private let preferences: [String: Any]?

    init(
        vm: ShoppingListReaderViewModel,
        planData: ShoppingPlan?,
        preferences: [String: Any]? = nil
    ) {
        _vm = StateObject(wrappedValue: vm)
        self.planData = planData
        self.preferences = preferences
    }

    var body: some View {
        content
            .navigationTitle(NSLocalizedString("shopping_list_title", comment: ""))
            .task {
                await vm.load(planData: planData, preferences: preferences)
            }
    }

    @ViewBuilder
    private var content: some View {
        switch vm.state {
        case .idle, .loading:
            ProgressView()

        case .empty:
            ContentUnavailableView(
                NSLocalizedString("shopping_list_empty_title", comment: ""),
                systemImage: "cart",
                description: Text(NSLocalizedString("shopping_list_empty_description", comment: ""))
            )

        case .error(let message):
            VStack(spacing: 12) {
                Text(NSLocalizedString("shopping_list_error_title", comment: ""))
                    .font(.headline)
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding()

        case .loaded(let data):
            List {
                Section {
                    Text(data.totalItemsText)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                ForEach(data.categories) { cat in
                    Section(header: Text(cat.title)) {
                        ForEach(cat.items) { item in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(item.name)
                                    Spacer()
                                    Text(item.quantityText).foregroundStyle(.secondary)
                                }
                                if !item.recipeRefs.isEmpty {
                                    Text(item.recipeRefs.joined(separator: ", "))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }

                if !data.warnings.isEmpty {
                    Section(header: Text(NSLocalizedString("shopping_list_warnings_title", comment: ""))) {
                        ForEach(data.warnings) { w in
                            Text(w.code)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if let footer = data.footerText {
                    Section {
                        Text(footer)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }
}
