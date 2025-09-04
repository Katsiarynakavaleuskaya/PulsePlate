def iu_vitd_from_ug(vitd_ug: float) -> float:
    """
    RU: Конвертировать витамин D из µg в IU.
    EN: Convert vitamin D from µg to IU.

    Args:
        vitd_ug: Vitamin D in µg

    Returns:
        Vitamin D in IU (1 µg ≈ 40 IU)
    """
    # 1 µg VitD ≈ 40 IU
    return float(vitd_ug) * 40.0


def mg_from_ug(value_ug: float) -> float:
    """
    RU: Конвертировать из µg в mg.
    EN: Convert from µg to mg.

    Args:
        value_ug: Value in µg

    Returns:
        Value in mg
    """
    return float(value_ug) / 1000.0


def mg_from_g(value_g: float) -> float:
    """
    RU: Конвертировать из г в мг.
    EN: Convert from g to mg.

    Args:
        value_g: Value in g

    Returns:
        Value in mg
    """
    return float(value_g) * 1000.0
