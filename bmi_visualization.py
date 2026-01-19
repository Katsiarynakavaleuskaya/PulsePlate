# -*- coding: utf-8 -*-
"""
BMI Visualization Module - Generate BMI charts and visual reports.
Supports BMI category visualization, progress tracking, and population-specific charts.
"""

import base64
import io
from collections.abc import Iterable
from typing import Any, Protocol

# Import canonical BMI engine functions
from core.bmi.engine import (
    BMIGroup,
    HEALTHY_BMI_RANGE,
    _auto_group,
    _bmi_category,
    _group_display_name,
    _normalize_bool_flag,
)
from core.bmi.risk import (
    BMI_NORMAL_MIN,
    BMI_OBESE_THRESHOLD,
    BMI_OVERWEIGHT_THRESHOLD,
)
from core.i18n import Language, normalize_lang, t


def _t_or_none(lang_norm: Language, key: str) -> str | None:
    """
    Return translation if present; None if i18n misses and returns the key.

    Args:
        lang_norm: Normalized language code
        key: i18n translation key

    Returns:
        Translated string if valid, None if translation missing
    """
    try:
        val = t(lang_norm, key)
        # Guard: if translation missing and t() returns the key itself, treat as miss
        if val == key:
            return None
        return val
    except KeyError:
        return None


def _localize_bmi_category(lang_norm: Language, category_key: str) -> str:
    """
    Localize BMI category using canonical i18n keys.
    Never returns raw keys or alternative wording that diverges from i18n.

    Args:
        lang_norm: Normalized language code
        category_key: BMI category key (e.g., "underweight", "obesity_1")

    Returns:
        Localized category string, or safe generic label if i18n fails
    """
    # Try canonical key format: bmi.<category_key> (works for underweight, normal, overweight)
    primary_key = f"bmi.{category_key}"
    localized = _t_or_none(lang_norm, primary_key)
    if localized:
        return localized

    # For obesity tiers, try legacy keys (bmi_obese_1, bmi_obese_2, bmi_obese_3)
    if category_key.startswith("obesity_"):
        legacy_key = f"bmi_obese_{category_key.split('_')[1]}"
        localized = _t_or_none(lang_norm, legacy_key)
        if localized:
            return localized

        # If specific tier key missing, try generic obesity label
        generic = _t_or_none(lang_norm, "bmi.obesity")
        if generic:
            return generic

    # Last resort: safe generic label (not category-specific, avoids drift)
    # This ensures we never return raw keys or alternative wording
    safe_labels = {
        "en": "BMI category",
        "ru": "Категория ИМТ",
        "es": "Categoría de IMC",
    }
    return safe_labels.get(str(lang_norm), safe_labels["en"])


MATPLOTLIB_AVAILABLE = False
plt: Any | None
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot

    plt = matplotlib.pyplot

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None


class _BarLike(Protocol):
    def get_height(self) -> float: ...  # pragma: no cover

    def get_width(self) -> float: ...  # pragma: no cover

    def get_x(self) -> float: ...  # pragma: no cover


class _AxesLike(Protocol):
    def bar(self, *args: object, **kwargs: object) -> Iterable[_BarLike]: ...  # pragma: no cover

    def barh(self, *args: object, **kwargs: object) -> Iterable[_BarLike]: ...  # pragma: no cover

    def grid(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def legend(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def plot(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def set_xlabel(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def set_ylabel(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def set_title(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def set_xlim(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def set_ylim(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def set_yticks(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    def text(self, *args: object, **kwargs: object) -> object: ...  # pragma: no cover

    transAxes: object


class BMIVisualizer:
    """BMI visualization generator with population-specific charts."""

    # BMI category colors
    COLORS = {
        "underweight": "#3498db",  # Blue
        "normal": "#27ae60",  # Green
        "overweight": "#f39c12",  # Orange
        "obese": "#e74c3c",  # Red
    }

    # Visual-only BMI ranges for chart display (not used for classification)
    # Classification uses core/bmi/engine and core/bmi/risk thresholds
    BMI_RANGES = {
        "general": [
            (0, BMI_NORMAL_MIN),
            (BMI_NORMAL_MIN, BMI_OVERWEIGHT_THRESHOLD),
            (BMI_OVERWEIGHT_THRESHOLD, BMI_OBESE_THRESHOLD),
            (BMI_OBESE_THRESHOLD, 45),
        ],
        "elderly": [
            (0, 17.5),  # Elderly-specific visual threshold
            (17.5, 26.0),  # Elderly-specific visual threshold
            (26.0, 31.0),  # Elderly-specific visual threshold
            (31.0, 45),
        ],
        "teen": [
            (0, 17.5),  # Teen-specific visual threshold
            (17.5, 24.5),  # Teen-specific visual threshold
            (24.5, 29.5),  # Teen-specific visual threshold
            (29.5, 45),
        ],
        "athlete": [
            (0, BMI_NORMAL_MIN),
            (BMI_NORMAL_MIN, 27.0),  # Athlete-specific visual threshold
            (27.0, 32.0),  # Athlete-specific visual threshold
            (32.0, 45),
        ],
    }

    def __init__(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib not available for visualization")

    def create_bmi_chart(
        self,
        bmi: float,
        age: int,
        gender: str,
        group: BMIGroup = "general",
        lang: str = "en",
        include_guidance: bool = True,
    ) -> str:
        """Generate BMI visualization chart as base64 encoded PNG."""

        if plt is None:
            raise ImportError("matplotlib not available for visualization")

        # Set up the figure
        # Normalize language if not already normalized (defensive)
        lang_norm = normalize_lang(lang) if isinstance(lang, str) else Language.EN
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        fig.suptitle(
            f"BMI Analysis - {_group_display_name(group, lang_norm).title()}"
            + (f" (Age: {age})" if age else ""),
            fontsize=16,
            fontweight="bold",
        )

        # Left plot: BMI gauge chart (use normalized language for consistency)
        self._create_bmi_gauge(ax1, bmi, group, str(lang_norm))

        # Right plot: BMI over time (placeholder for future enhancement)
        self._create_guidance_chart(ax2, bmi, age, gender, group, str(lang_norm))

        # Convert to base64
        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close(fig)

        return image_base64

    def _create_bmi_gauge(self, ax: _AxesLike, bmi: float, group: BMIGroup, lang: str) -> None:
        """Create BMI gauge chart showing current BMI position."""
        ranges = self.BMI_RANGES.get(group, self.BMI_RANGES["general"])
        colors = ["#3498db", "#27ae60", "#f39c12", "#e74c3c"]

        # Create horizontal bar chart
        y_pos = 0
        bar_height = 0.8

        for i, ((start, end), color) in enumerate(zip(ranges, colors)):
            width = end - start
            ax.barh(
                y_pos,
                width,
                left=start,
                height=bar_height,
                color=color,
                alpha=0.7,
                edgecolor="white",
                linewidth=2,
            )

            # Add category labels (simple dict for EN/RU/ES, no new i18n keys)
            category_names_map = {
                "en": {0: "Under", 1: "Normal", 2: "Over", 3: "Obese"},
                "ru": {0: "Недовес", 1: "Норма", 2: "Избыток", 3: "Ожирение"},
                "es": {0: "Bajo", 1: "Normal", 2: "Sobre", 3: "Obeso"},
            }
            category_names = category_names_map.get(lang, category_names_map["en"])

            mid_point = start + width / 2
            ax.text(
                mid_point,
                y_pos,
                category_names[i],
                ha="center",
                va="center",
                fontweight="bold",
                fontsize=10,
            )

        # Mark current BMI
        ax.plot([bmi, bmi], [-0.6, 0.6], "k-", linewidth=4, label=f"BMI: {bmi}")
        ax.plot(
            bmi,
            y_pos,
            "ko",
            markersize=12,
            markerfacecolor="black",
            markeredgecolor="white",
            markeredgewidth=2,
        )

        # Customize axes
        ax.set_xlim(15, 40)
        ax.set_ylim(-1, 1)
        ax.set_xlabel("BMI Value", fontsize=12)
        ax.set_yticks([])
        ax.grid(axis="x", alpha=0.3)
        ax.legend(loc="upper right")
        ax.set_title(f"Current BMI: {bmi}", fontsize=14, fontweight="bold")

    def _create_guidance_chart(
        self,
        ax: _AxesLike,
        bmi: float,
        age: int,
        gender: str,
        group: BMIGroup,
        lang: str,
    ) -> None:
        """Create guidance and recommendations chart."""

        # Calculate healthy weight range based on height (assume 1.7m for demo)
        height = 1.7  # This would come from actual data
        # Use canonical HEALTHY_BMI_RANGE from engine (general population)
        healthy_min = HEALTHY_BMI_RANGE.min * height * height
        healthy_max = HEALTHY_BMI_RANGE.max * height * height

        # Group-specific adjustments (visual only, not for classification)
        if group == "elderly":
            healthy_max = 26.0 * height * height  # Elderly-specific (visual only)
        elif group == "athlete":
            healthy_max = 27.0 * height * height  # Athlete-specific (visual only)

        current_weight = bmi * height * height

        # Create weight recommendation chart
        weights = [healthy_min, current_weight, healthy_max]
        labels = ["Healthy Min", "Current", "Healthy Max"]
        colors = [
            "lightgreen",
            "blue" if healthy_min <= current_weight <= healthy_max else "orange",
            "lightgreen",
        ]

        bars = ax.bar(labels, weights, color=colors, alpha=0.7, edgecolor="black")

        # Add value labels on bars
        for bar, weight in zip(bars, weights):
            bar_height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar_height + 1,
                f"{weight:.1f}kg",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_ylabel("Weight (kg)", fontsize=12)
        ax.set_title("Weight Recommendations", fontsize=14, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)

        # Add recommendation text (simple dict for EN/RU/ES, no new i18n keys)
        recommendations_map = {
            "en": {
                "gain": "Consider healthy weight gain",
                "loss": "Consider healthy weight loss",
                "maintain": "Maintain current weight",
            },
            "ru": {
                "gain": "Рекомендуется здоровый набор веса",
                "loss": "Рекомендуется здоровое снижение веса",
                "maintain": "Поддерживайте текущий вес",
            },
            "es": {
                "gain": "Considere ganar peso saludable",
                "loss": "Considere perder peso saludable",
                "maintain": "Mantenga el peso actual",
            },
        }
        rec_map = recommendations_map.get(lang, recommendations_map["en"])
        if current_weight < healthy_min:
            recommendation = rec_map["gain"]
        elif current_weight > healthy_max:
            recommendation = rec_map["loss"]
        else:
            recommendation = rec_map["maintain"]

        ax.text(
            0.5,
            0.95,
            recommendation,
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=11,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7),
        )


def generate_bmi_visualization(
    bmi: float,
    age: int,
    gender: str,
    pregnant: bool | str = "no",
    athlete: bool | str = "no",
    lang: str = "en",
) -> dict[str, Any]:
    """Generate BMI visualization and return as base64 encoded image."""

    if not MATPLOTLIB_AVAILABLE:
        return {
            "error": "Visualization not available - matplotlib not installed",
            "available": False,
        }

    try:
        # Normalize inputs for canonical engine
        lang_norm = normalize_lang(lang)
        pregnant_bool = (
            _normalize_bool_flag(pregnant) if isinstance(pregnant, str) else bool(pregnant)
        )
        # Preserve athlete_text for backward compatibility (string inputs like "спортсмен"/"athlete")
        athlete_text: str | None = None
        if isinstance(athlete, str):
            athlete_bool = _normalize_bool_flag(athlete)
            # If string is not recognized as yes/no, preserve it for engine heuristics
            # This allows legacy behavior where "спортсмен"/"athlete" strings trigger athlete group
            athlete_lower = athlete.strip().lower()
            if athlete_bool is False and athlete_lower not in {
                "no",
                "false",
                "0",
                "",
                "нет",
                "н",
                "не",
            }:
                athlete_text = athlete
        else:
            athlete_bool = bool(athlete)

        # Determine user group using canonical engine
        group = _auto_group(
            age=age,
            gender=gender,
            pregnant=pregnant_bool,
            athlete=athlete_bool,
            athlete_text=athlete_text,
        )

        # Create visualizer
        visualizer = BMIVisualizer()

        # Generate chart with normalized language for consistency
        chart_base64 = visualizer.create_bmi_chart(
            bmi=bmi, age=age, gender=gender, group=group, lang=str(lang_norm)
        )

        # Get BMI category using canonical engine
        category_result = _bmi_category(bmi=bmi, age=age, group=group)

        # Localize category key to string (backward compatibility with bmi_core behavior)
        if category_result is None:
            category_str = None
        else:
            category_key = str(category_result)
            category_str = _localize_bmi_category(lang_norm, category_key)

        return {
            "chart_base64": chart_base64,
            "category": category_str,
            "group": group,
            "group_display": _group_display_name(group, lang_norm),
            "available": True,
            "format": "png",
            "encoding": "base64",
        }

    except Exception as e:
        return {
            "error": f"Visualization generation failed: {str(e)}",
            "available": False,
        }


# Export functions for API usage
__all__ = ["generate_bmi_visualization", "BMIVisualizer", "MATPLOTLIB_AVAILABLE"]
