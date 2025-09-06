"""
WHO/EFSA Reference Tables and Standards (simplified version)

RU: Сокращённая таблица норм (пример). Для продa расширить возрастные группы.
"""

# RU: Сокращённая таблица норм (пример). Для продa расширить возрастные группы.
WHO_ACTIVITY = {"adult": {"moderate_min_week": 150, "vigorous_min_week": 75}}

WHO_MICRO_RDA = {
    ("female", "19-50"): {
        "Fe_mg": 18,
        "Ca_mg": 1000,
        "Folate_ug": 400,
        "Iodine_ug": 150,
        "VitD_IU": 600,
        "B12_ug": 2.4,
        "K_mg": 90,
        "Mg_mg": 310,
    },
    ("male", "19-50"): {
        "Fe_mg": 8,
        "Ca_mg": 1000,
        "Folate_ug": 400,
        "Iodine_ug": 150,
        "VitD_IU": 600,
        "B12_ug": 2.4,
        "K_mg": 120,
        "Mg_mg": 400,
    },
}
