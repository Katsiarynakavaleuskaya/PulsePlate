import Foundation

public enum WeeklyPlanAdapter {
    public static func toVM(dto: WeeklyPlanDTO) -> WeeklyPlanVM {
        let root = dto.root

        let days = parseDays(from: root)
        let coverage = parseWeeklyCoverage(from: root)
        let metrics = parseMetrics(from: root)
        let shop = parseShoppingList(from: root)

        return WeeklyPlanVM(days: days, weeklyCoverage: coverage, metrics: metrics, shoppingList: shop)
    }

    // MARK: - Parsers

    private static func parseDays(from root: JSONValue) -> [DayPlanVM] {
        let arr = root["daily_menus"].arrayValue ?? root["days"].arrayValue ?? []
        if arr.isEmpty { return [] }

        return arr.enumerated().map { idx, dayVal in
            let dayTitle =
                dayVal["title"].stringValue ??
                dayVal["day_name"].stringValue ??
                dayVal["weekday"].stringValue ??
                "Day \(idx + 1)"

            let meals = parseMeals(from: dayVal)

            // Fallback: daily_totals OR totals
            let totalsRoot = dayVal["daily_totals"].objectValue != nil
                ? dayVal["daily_totals"]
                : dayVal["totals"]

            let totals = MacroTotalsVM(
                kcal: totalsRoot["kcal"].intRounded,
                proteinG: totalsRoot["protein_g"].intRounded,
                fatG: totalsRoot["fat_g"].intRounded,
                carbsG: totalsRoot["carbs_g"].intRounded
            )

            return DayPlanVM(
                id: dayVal["id"].stringValue ?? "day-\(idx)",
                index: idx,
                title: dayTitle,
                meals: meals,
                totals: totals.kcal == nil && totals.proteinG == nil && totals.fatG == nil && totals.carbsG == nil ? nil : totals
            )
        }
    }

    private static func parseMeals(from dayVal: JSONValue) -> [MealSectionVM] {
        let mealsArr = dayVal["meals"].arrayValue ?? []
        let sections = mealsArr.enumerated().compactMap { i, mealVal -> MealSectionVM? in
            let typeRaw = mealVal["meal_type"].stringValue?.lowercased()
                ?? mealVal["type"].stringValue?.lowercased()

            let mealType = MealType(rawValue: typeRaw ?? "") ?? .other
            let title = mealVal["title"].stringValue ?? mealType.displayName

            // kcal can be at meal.kcal OR meal.totals.kcal
            let kcal = mealVal["kcal"].intRounded
                ?? mealVal["totals"]["kcal"].intRounded

            let recipes = mealVal["recipes"].arrayValue ?? mealVal["items"].arrayValue ?? []
            let items: [MealItemVM] = recipes.enumerated().map { j, r in
                let name = r["name"].stringValue ?? r["title"].stringValue ?? "Item"
                let id = r["id"].stringValue ?? "\(mealType.rawValue)-\(i)-\(j)"
                let portions = r["portions"].doubleValue ?? r["portion"].doubleValue
                return MealItemVM(id: id, name: name, portions: portions)
            }

            // Skip empty sections (no kcal and no items)
            if items.isEmpty && kcal == nil {
                return nil
            }

            return MealSectionVM(
                id: mealVal["id"].stringValue ?? "\(mealType.rawValue)-\(i)",
                mealType: mealType,
                title: title,
                kcal: kcal,
                items: items
            )
        }

        // Enforce stable meal order: breakfast → lunch → dinner → snacks → other
        return sections.sorted { $0.mealType.sortRank < $1.mealType.sortRank }
    }

    private static func parseWeeklyCoverage(from root: JSONValue) -> [CoverageItemVM] {
        // Possible forms:
        // weekly_coverage: { "protein": 98.5, "iron": 95.1 }
        // or weeklyCoverage: [{label, percent}]
        if let dict = root["weekly_coverage"].objectValue {
            let items = dict.compactMap { k, v -> CoverageItemVM? in
                guard let p = v.doubleValue else { return nil }
                // Clamp to prevent UI breaking on bad data
                let clamped = min(max(p, 0), 300)
                return CoverageItemVM(label: prettifyKey(k), percent: clamped)
            }

            // Sort: deficits first (under 100), then overs; within each group by percent
            return items.sorted {
                if $0.isOver != $1.isOver { return !$0.isOver }
                return $0.percent < $1.percent
            }
        }

        let arr = root["weekly_coverage"].arrayValue ?? root["weeklyCoverage"].arrayValue ?? []
        let items = arr.compactMap { v -> CoverageItemVM? in
            guard let label = v["label"].stringValue ?? v["name"].stringValue else { return nil }
            guard let p = v["percent"].doubleValue ?? v["value"].doubleValue else { return nil }
            let clamped = min(max(p, 0), 300)
            return CoverageItemVM(label: label, percent: clamped)
        }

        // Same sorting
        return items.sorted {
            if $0.isOver != $1.isOver { return !$0.isOver }
            return $0.percent < $1.percent
        }
    }

    private static func parseMetrics(from root: JSONValue) -> PlanMetricsVM? {
        let cost = root["total_cost"].doubleValue ?? root["metrics"]["total_cost"].doubleValue
        let adherence = root["adherence_score"].doubleValue ?? root["metrics"]["adherence_score"].doubleValue
        if cost == nil && adherence == nil { return nil }
        return PlanMetricsVM(totalCost: cost, adherenceScore: adherence)
    }

    private static func parseShoppingList(from root: JSONValue) -> [String: Double]? {
        // Fallback: shopping_list OR shoppingList
        let obj = root["shopping_list"].objectValue ?? root["shoppingList"].objectValue
        guard let dict = obj else { return nil }

        var out: [String: Double] = [:]
        for (rawKey, v) in dict {
            guard let qty = v.doubleValue, qty != 0 else { continue }
            // Normalize keys (trim whitespace)
            let key = rawKey.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !key.isEmpty else { continue }
            out[key] = qty
        }

        return out.isEmpty ? nil : out
    }

    private static func prettifyKey(_ k: String) -> String {
        // Normalize separators and trim
        let cleaned = k
            .replacingOccurrences(of: "-", with: "_")
            .replacingOccurrences(of: " ", with: "_")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard !cleaned.isEmpty else { return k }

        // Units (keep human-friendly lowercase)
        let unitLower: Set<String> = ["mg", "g", "kg", "kcal"]
        // Units uppercase
        let unitUpper: Set<String> = ["iu"]
        // Chemical symbols (capitalize properly: Fe, Zn, Ca)
        let chem: [String: String] = [
            "fe": "Fe", "zn": "Zn", "ca": "Ca", "na": "Na", "k": "K"
        ]

        let parts = cleaned.split(separator: "_").map { String($0) }

        let pretty = parts.map { part -> String in
            let lower = part.lowercased()

            // Handle units
            if unitLower.contains(lower) { return lower }          // mg, g, kg, kcal
            if unitUpper.contains(lower) { return lower.uppercased() } // IU

            // Handle chemical elements
            if let c = chem[lower] { return c }                   // Fe, Zn, Ca, Na, K

            // Handle special cases
            if lower == "vitamin" { return "Vitamin" }

            // Handle B-vitamins: B12, B6, B3
            if lower.hasPrefix("b"), lower.dropFirst().allSatisfy({ $0.isNumber }) {
                return lower.uppercased()
            }

            // Default: Title case
            return lower.prefix(1).uppercased() + lower.dropFirst()
        }
        .joined(separator: " ")

        return pretty
    }
}
