import Foundation

/// BMI test fixtures matching backend contract.
///
/// IMPORTANT: These fixtures MUST match real backend responses from tests.
/// Source of truth: `tests/test_bmi_calculate_endpoint.py` and backend schema.
/// If backend contract changes → update fixtures first, no fallback logic in iOS.
///
/// NOTE: Thresholds (18.5, 25, 30) in fixtures are ALLOWED because they're backend contract examples.
/// These values must NOT appear in Swift code (only in test fixtures).
enum BMIFixtures {
    static func successJSON() -> Data {
        // Keep this JSON aligned with backend examples (no invented fields).
        // Source: backend test responses from POST /api/v1/bmi/calculate
        """
        {
          "bmi": 22.86,
          "category": "normal",
          "group": "general",
          "group_display": "General",
          "interpretation": "Your BMI is within the normal range for your age group.",
          "wht_ratio": 0.49,
          "waist_risk": {
            "wht_ratio": 0.49,
            "risk_level": "low",
            "notes": []
          },
          "notes": [],
          "age_band": "adult",
          "visualization": {
            "kind": "bmi_scale_v1",
            "bmi": 22.86,
            "min": 0.0,
            "max": 60.0,
            "ranges": [
              {"key": "bmi.underweight", "from": 0, "to": 18.5},
              {"key": "bmi.normal", "from": 18.5, "to": 25.0},
              {"key": "bmi.overweight", "from": 25.0, "to": 30.0},
              {"key": "bmi.obesity", "from": 30.0, "to": 60.0}
            ],
            "marker": {"value": 22.86}
          },
          "interpretation_v1": null,
          "soft_paywall": null
        }
        """.data(using: .utf8)!
    }

    static func pregnantJSON() -> Data {
        """
        {
          "bmi": 24.5,
          "category": null,
          "group": "pregnant",
          "group_display": "Pregnant",
          "interpretation": "BMI is not valid during pregnancy.",
          "wht_ratio": null,
          "waist_risk": null,
          "notes": [],
          "age_band": "adult",
          "visualization": null,
          "interpretation_v1": null,
          "soft_paywall": null
        }
        """.data(using: .utf8)!
    }

    static func validation422JSON() -> Data {
        """
        {
          "detail": [
            {
              "type": "greater_than",
              "loc": ["body", "weight_kg"],
              "msg": "Input should be greater than 0",
              "input": -1
            }
          ]
        }
        """.data(using: .utf8)!
    }

    static func error400JSON() -> Data {
        """
        {
          "detail": "Некорректные параметры для расчета BMI"
        }
        """.data(using: .utf8)!
    }
}
