"""Extra coverage for BMI visualization guidance chart branches."""

import pytest

import bmi_visualization as vizmod


def test_guidance_chart_covers_all_recommendation_branches():
    try:
        import matplotlib.pyplot as plt  # Local import to avoid stale references
    except ImportError:  # pragma: no cover - environment without matplotlib
        pytest.skip("matplotlib required for guidance chart")

    # Construct visualizer instance without triggering __init__ guard
    visualizer = object.__new__(vizmod.BMIVisualizer)

    fig_low, ax_low = plt.subplots()
    try:
        visualizer._create_guidance_chart(
            ax_low,
            bmi=15.0,
            age=70,
            gender="female",
            group="elderly",
            lang="en",
        )
    finally:
        plt.close(fig_low)

    fig_high, ax_high = plt.subplots()
    try:
        visualizer._create_guidance_chart(
            ax_high,
            bmi=35.0,
            age=30,
            gender="male",
            group="athlete",
            lang="ru",
        )
    finally:
        plt.close(fig_high)

    fig_mid, ax_mid = plt.subplots()
    try:
        visualizer._create_guidance_chart(
            ax_mid,
            bmi=23.0,
            age=30,
            gender="male",
            group="general",
            lang="ru",
        )
    finally:
        plt.close(fig_mid)

    assert ax_low.texts, "expected annotations for low BMI scenario"
    assert ax_high.texts, "expected annotations for high BMI scenario"
    assert ax_mid.texts, "expected annotations for mid BMI scenario"
