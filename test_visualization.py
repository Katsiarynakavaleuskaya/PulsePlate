# -*- coding: utf-8 -*-
"""
Test script for BMI visualization functionality.
"""

def test_bmi_visualization_without_matplotlib():
    """Test that visualization gracefully handles missing matplotlib."""
    from bmi_visualization import MATPLOTLIB_AVAILABLE, generate_bmi_visualization

    print(f"Matplotlib available: {MATPLOTLIB_AVAILABLE}")

    if not MATPLOTLIB_AVAILABLE:
        result = generate_bmi_visualization(
            bmi=24.5, age=30, gender="male",
            pregnant="no", athlete="no", lang="en"
        )

        print("Result without matplotlib:")
        print(result)
        assert not result["available"]
        assert "error" in result
        print("✅ Graceful degradation works correctly")
    else:
        result = generate_bmi_visualization(
            bmi=24.5, age=30, gender="male",
            pregnant="no", athlete="no", lang="en"
        )

        print("Result with matplotlib:")
        print("Available:", result["available"])
        print("Category:", result.get("category"))
        print("Group:", result.get("group"))
        if result.get("chart_base64"):
            print("Chart generated (base64 length):", len(result["chart_base64"]))
        print("✅ Visualization generation works")

def test_enhanced_segmentation():
    """Test the enhanced segmentation logic."""
    from bmi_core import auto_group, bmi_category, group_display_name

    # Test new teen category
    teen_group = auto_group(16, "male", "no", "no", "en")
    print(f"16-year-old categorized as: {teen_group}")
    assert teen_group == "teen"

    # Test BMI category with age and group
    teen_bmi_cat = bmi_category(22.0, "en", 16, "teen")
    adult_bmi_cat = bmi_category(22.0, "en", 30, "general")
    print(f"BMI 22.0 for teen: {teen_bmi_cat}")
    print(f"BMI 22.0 for adult: {adult_bmi_cat}")

    # Test group display names
    teen_display = group_display_name("teen", "en")
    print(f"Teen display name: {teen_display}")
    assert teen_display == "teenager"

    print("✅ Enhanced segmentation works correctly")

if __name__ == "__main__":
    print("🧪 Testing BMI visualization and enhanced segmentation...")
    test_bmi_visualization_without_matplotlib()
    test_enhanced_segmentation()
    print("🎉 All tests passed!")
