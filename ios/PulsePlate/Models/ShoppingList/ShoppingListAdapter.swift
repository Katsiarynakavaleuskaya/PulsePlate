import Foundation

// MARK: - View Models (Typed, UI-ready)

public struct ShoppingListViewData: Sendable, Equatable {
    public let headerTitle: String
    public let totalItemsText: String
    public let categories: [Category]
    public let warnings: [Warning]
    public let footerText: String?

    public struct Category: Sendable, Equatable, Identifiable {
        public var id: String { key }
        public let key: String
        public let title: String
        public let items: [Item]
    }

    public struct Item: Sendable, Equatable, Identifiable {
        public var id: String { key }
        public let key: String
        public let name: String
        public let quantityText: String
        public let recipeRefs: [String]
    }

    public struct Warning: Sendable, Equatable, Identifiable {
        public var id: String { code }
        public let code: String
    }
}

// MARK: - Adapter

public enum ShoppingListAdapter {
    /// Adapt backend DTO to typed view model with localized quantities
    public static func adapt(dto: ShoppingListDTO, locale: Locale = .current) -> ShoppingListViewData {
        let totalText = String(
            format: NSLocalizedString("shopping_list_total_items_fmt", comment: "Total items format"),
            dto.totalItems
        )

        let categories: [ShoppingListViewData.Category] = dto.categories.map { cat in
            .init(
                key: cat.key,
                title: cat.title,
                items: cat.items.map { item in
                    .init(
                        key: item.key,
                        name: item.name,
                        quantityText: formatQuantity(item.quantity, unit: item.unit, locale: locale),
                        recipeRefs: item.recipeRefs
                    )
                }
            )
        }

        let warnings = dto.meta.warnings.map { ShoppingListViewData.Warning(code: $0) }

        let header = NSLocalizedString("shopping_list_title", comment: "Shopping List title")
        let footer: String? = dto.meta.source.isEmpty ? nil :
            String(format: NSLocalizedString("shopping_list_source_fmt", comment: "Source format"), dto.meta.source)

        return .init(
            headerTitle: header,
            totalItemsText: totalText,
            categories: categories,
            warnings: warnings,
            footerText: footer
        )
    }

    private static func formatQuantity(_ value: Double, unit: String, locale: Locale) -> String {
        let nf = NumberFormatter()
        nf.locale = locale
        nf.maximumFractionDigits = 2
        nf.minimumFractionDigits = value.rounded() == value ? 0 : 1
        let num = nf.string(from: NSNumber(value: value)) ?? "\(value)"
        return "\(num) \(unit)"
    }
}
