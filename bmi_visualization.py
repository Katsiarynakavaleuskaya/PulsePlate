# -*- coding: utf-8 -*-
"""
BMI Visualization Module - Generate BMI charts and visual reports.
Supports BMI category visualization, progress tracking, and population-specific charts.
"""

import base64
import io
from typing import Any, Dict

from bmi_core import auto_group, bmi_category, group_display_name

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None


class BMIVisualizer:
    """BMI visualization generator with population-specific charts."""

    # BMI category colors
    COLORS = {
        'underweight': '#3498db',  # Blue
        'normal': '#27ae60',       # Green
        'overweight': '#f39c12',   # Orange
        'obese': '#e74c3c'         # Red
    }

    # Age-specific BMI ranges for visualization
    BMI_RANGES = {
        'general': [(0, 18.5), (18.5, 25), (25, 30), (30, 45)],
        'elderly': [(0, 17.5), (17.5, 26), (26, 31), (31, 45)],
        'teen': [(0, 17.5), (17.5, 24.5), (24.5, 29.5), (29.5, 45)],
        'athlete': [(0, 18.5), (18.5, 27), (27, 32), (32, 45)]
    }

    def __init__(self):
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib not available for visualization")

    def create_bmi_chart(
        self,
        bmi: float,
        age: int,
        gender: str,
        group: str = "general",
        lang: str = "en",
        include_guidance: bool = True
    ) -> str:
        """Generate BMI visualization chart as base64 encoded PNG."""

        if plt is None:
            raise ImportError("matplotlib not available for visualization")

        # Set up the figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        fig.suptitle(
            f"BMI Analysis - {group_display_name(group, lang).title()}" +
            (f" (Age: {age})" if age else ""),
            fontsize=16, fontweight='bold'
        )

        # Left plot: BMI gauge chart
        self._create_bmi_gauge(ax1, bmi, group, lang)

        # Right plot: BMI over time (placeholder for future enhancement)
        self._create_guidance_chart(ax2, bmi, age, gender, group, lang)

        # Convert to base64
        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)

        return image_base64

    def _create_bmi_gauge(self, ax, bmi: float, group: str, lang: str):
        """Create BMI gauge chart showing current BMI position."""
        ranges = self.BMI_RANGES.get(group, self.BMI_RANGES['general'])
        colors = ['#3498db', '#27ae60', '#f39c12', '#e74c3c']

        # Create horizontal bar chart
        y_pos = 0
        bar_height = 0.8

        for i, ((start, end), color) in enumerate(zip(ranges, colors)):
            width = end - start
            ax.barh(y_pos, width, left=start, height=bar_height,
                   color=color, alpha=0.7, edgecolor='white', linewidth=2)

            # Add category labels
            category_names = {
                0: "Under" if lang == "en" else "Недовес",
                1: "Normal" if lang == "en" else "Норма",
                2: "Over" if lang == "en" else "Избыток",
                3: "Obese" if lang == "en" else "Ожирение"
            }

            mid_point = start + width / 2
            ax.text(mid_point, y_pos, category_names[i],
                   ha='center', va='center', fontweight='bold', fontsize=10)

        # Mark current BMI
        ax.plot([bmi, bmi], [-0.6, 0.6], 'k-', linewidth=4, label=f'BMI: {bmi}')
        ax.plot(bmi, y_pos, 'ko', markersize=12, markerfacecolor='black',
               markeredgecolor='white', markeredgewidth=2)

        # Customize axes
        ax.set_xlim(15, 40)
        ax.set_ylim(-1, 1)
        ax.set_xlabel('BMI Value', fontsize=12)
        ax.set_yticks([])
        ax.grid(axis='x', alpha=0.3)
        ax.legend(loc='upper right')
        ax.set_title(f'Current BMI: {bmi}', fontsize=14, fontweight='bold')

    def _create_guidance_chart(self, ax, bmi: float, age: int, gender: str, group: str, lang: str):
        """Create guidance and recommendations chart."""

        # Calculate healthy weight range based on height (assume 1.7m for demo)
        height = 1.7  # This would come from actual data
        healthy_min = 18.5 * height * height
        healthy_max = 25.0 * height * height

        if group == "elderly":
            healthy_max = 26.0 * height * height
        elif group == "athlete":
            healthy_max = 27.0 * height * height

        current_weight = bmi * height * height

        # Create weight recommendation chart
        weights = [healthy_min, current_weight, healthy_max]
        labels = ['Healthy Min', 'Current', 'Healthy Max']
        colors = [
            'lightgreen',
            'blue' if healthy_min <= current_weight <= healthy_max else 'orange',
            'lightgreen'
        ]

        bars = ax.bar(labels, weights, color=colors, alpha=0.7, edgecolor='black')

        # Add value labels on bars
        for bar, weight in zip(bars, weights):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{weight:.1f}kg', ha='center', va='bottom', fontweight='bold')

        ax.set_ylabel('Weight (kg)', fontsize=12)
        ax.set_title('Weight Recommendations', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        # Add recommendation text
        if current_weight < healthy_min:
            recommendation = (
                "Consider healthy weight gain" if lang == "en"
                else "Рекомендуется здоровый набор веса"
            )
        elif current_weight > healthy_max:
            recommendation = (
                "Consider healthy weight loss" if lang == "en"
                else "Рекомендуется здоровое снижение веса"
            )
        else:
            recommendation = (
                "Maintain current weight" if lang == "en"
                else "Поддерживайте текущий вес"
            )

        ax.text(0.5, 0.95, recommendation, transform=ax.transAxes,
               ha='center', va='top', fontsize=11, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))


def generate_bmi_visualization(
    bmi: float,
    age: int,
    gender: str,
    pregnant: str = "no",
    athlete: str = "no",
    lang: str = "en"
) -> Dict[str, Any]:
    """Generate BMI visualization and return as base64 encoded image."""

    if not MATPLOTLIB_AVAILABLE:
        return {
            "error": "Visualization not available - matplotlib not installed",
            "available": False
        }

    try:
        # Determine user group
        group = auto_group(age, gender, pregnant, athlete, lang)

        # Create visualizer
        visualizer = BMIVisualizer()

        # Generate chart
        chart_base64 = visualizer.create_bmi_chart(
            bmi=bmi,
            age=age,
            gender=gender,
            group=group,
            lang=lang
        )

        # Get BMI category
        category = bmi_category(bmi, lang, age, group)

        return {
            "chart_base64": chart_base64,
            "category": category,
            "group": group,
            "group_display": group_display_name(group, lang),
            "available": True,
            "format": "png",
            "encoding": "base64"
        }

    except Exception as e:
        return {
            "error": f"Visualization generation failed: {str(e)}",
            "available": False
        }


# Export functions for API usage
__all__ = ['generate_bmi_visualization', 'BMIVisualizer', 'MATPLOTLIB_AVAILABLE']
