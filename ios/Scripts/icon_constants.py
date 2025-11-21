"""
iOS Icon Constants for PulsePlate
Defines standard iOS icon sizes and filenames
"""

# iOS icon sizes mapping: filename -> size in pixels
IOS_ICON_SIZES: dict[str, int] = {
    # iPhone
    "icon_iphone_20pt@2x.png": 40,
    "icon_iphone_20pt@3x.png": 60,
    "icon_iphone_29pt@2x.png": 58,
    "icon_iphone_29pt@3x.png": 87,
    "icon_iphone_40pt@2x.png": 80,
    "icon_iphone_40pt@3x.png": 120,
    "icon_iphone_60pt@2x.png": 120,
    "icon_iphone_60pt@3x.png": 180,
    # iPad
    "icon_ipad_20pt.png": 20,
    "icon_ipad_20pt@2x.png": 40,
    "icon_ipad_29pt.png": 29,
    "icon_ipad_29pt@2x.png": 58,
    "icon_ipad_40pt.png": 40,
    "icon_ipad_40pt@2x.png": 80,
    "icon_ipad_76pt.png": 76,
    "icon_ipad_76pt@2x.png": 152,
    "icon_ipad_83_5pt@2x.png": 167,
    # App Store
    "icon_marketing_1024.png": 1024,
}

# Duplicate sizes allowlist: size -> tuple of filenames that share this size
# This is expected behavior for iOS icons (e.g., 40px is used for multiple icon types)
# Only includes sizes that are actually duplicated (used by multiple filenames)
IOS_ICON_DUPLICATE_ALLOWLIST: dict[int, tuple[str, ...]] = {
    40: (
        "icon_iphone_20pt@2x.png",
        "icon_ipad_20pt@2x.png",
        "icon_ipad_40pt.png",
    ),
    58: (
        "icon_iphone_29pt@2x.png",
        "icon_ipad_29pt@2x.png",
    ),
    80: (
        "icon_iphone_40pt@2x.png",
        "icon_ipad_40pt@2x.png",
    ),
    120: (
        "icon_iphone_40pt@3x.png",
        "icon_iphone_60pt@2x.png",
    ),
}
