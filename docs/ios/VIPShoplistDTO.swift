//
//  VIPShoplistDTO.swift
//  PulsePlate iOS
//
//  VIP Shoplist API DTOs (Swift models)
//  Contract: docs/VIP_Shoplist_API.md
//
//  Generated: PR-5
//

import Foundation

// MARK: - Enums

enum Unit: String, Codable, Hashable {
    case g = "G"
    case ml = "ML"
    case pcs = "PCS"
    case kg = "KG"
    case l = "L"
}

enum FoodForm: String, Codable {
    case raw = "RAW"
    case cooked = "COOKED"
    case frozen = "FROZEN"
    case dried = "DRIED"
    case canned = "CANNED"
}

enum RoundingMode: String, Codable {
    case ceil = "CEIL"
    case nearest = "NEAREST"
    case none = "NONE"
}

// MARK: - Common DTOs

struct QuantityDTO: Codable {
    /// Decimal serialized as string (e.g., "100.0", "150.5")
    let value: String
    let unit: Unit
}

struct ShoplistItemDTO: Codable {
    let foodId: String
    let qty: QuantityDTO
    let form: FoodForm

    enum CodingKeys: String, CodingKey {
        case foodId = "food_id"
        case qty, form
    }
}

struct PackageRuleDTO: Codable {
    let foodId: String
    let packSize: QuantityDTO
    let rounding: RoundingMode
    let minPacks: Int

    enum CodingKeys: String, CodingKey {
        case foodId = "food_id"
        case packSize = "pack_size"
        case rounding
        case minPacks = "min_packs"
    }
}

// MARK: - Requests

struct ShoplistGenerateRequest: Codable {
    let items: [ShoplistItemDTO]
    let packagingRules: [PackagingRuleDTO]?

    enum CodingKeys: String, CodingKey {
        case items
        case packagingRules = "packaging_rules"
    }
}

typealias ShoplistDailyRequest = ShoplistGenerateRequest

struct ShoplistWeeklyDayRequest: Codable {
    let items: [ShoplistItemDTO]
    let packagingRules: [PackagingRuleDTO]?

    enum CodingKeys: String, CodingKey {
        case items
        case packagingRules = "packaging_rules"
    }
}

struct ShoplistWeeklyRequest: Codable {
    let days: [ShoplistWeeklyDayRequest]
}

// MARK: - Responses

struct PackedLineDTO: Codable {
    let foodId: String
    let requested: QuantityDTO
    let packSize: QuantityDTO
    let packs: Int
    let provided: QuantityDTO
    let overage: QuantityDTO
    let rounding: RoundingMode
    let minPacks: Int
    /// Explainability reasons (stable order, deterministic)
    let reasons: [String]

    enum CodingKeys: String, CodingKey {
        case foodId = "food_id"
        case requested
        case packSize = "pack_size"
        case packs
        case provided
        case overage
        case rounding
        case minPacks = "min_packs"
        case reasons
    }
}

struct UnpackedLineDTO: Codable {
    let foodId: String
    let requested: QuantityDTO
    /// Why item is unpacked (default: "no_packaging_rule")
    let reason: String

    enum CodingKeys: String, CodingKey {
        case foodId = "food_id"
        case requested
        case reason
    }
}

struct ShoplistAnalyticsDTO: Codable {
    let totalLines: Int
    let packedLines: Int
    let unpackedLines: Int
    /// Aggregated overage per unit type (Decimal serialized as string)
    let totalOverageByUnit: [Unit: String]

    enum CodingKeys: String, CodingKey {
        case totalLines = "total_lines"
        case packedLines = "packed_lines"
        case unpackedLines = "unpacked_lines"
        case totalOverageByUnit = "total_overage_by_unit"
    }
}

struct ShoplistGenerateResponse: Codable {
    let packed: [PackedLineDTO]
    let unpacked: [UnpackedLineDTO]
    /// Analytics summary (included by default in generate/daily/weekly endpoints)
    let analytics: ShoplistAnalyticsDTO?
}

struct ShoplistWeeklyResponse: Codable {
    /// One response per day (length = as requested by client)
    let days: [ShoplistGenerateResponse]
}

// MARK: - Utilities

extension String {
    /// Parse Decimal string to Decimal (locale: en_US_POSIX for consistency)
    func asDecimal() -> Decimal? {
        Decimal(string: self, locale: Locale(identifier: "en_US_POSIX"))
    }
}

extension QuantityDTO {
    /// Convenience: parse value to Decimal
    var decimalValue: Decimal? {
        value.asDecimal()
    }
}
