"""
Shared constants for iOS icon generation scripts.
Contains the standard iOS icon sizes mapping.
"""

# iOS icon sizes mapping: filename -> size in pixels
IOS_ICON_SIZES: dict[str, int] = {
    # iPhone
    "icon_iphone_20pt@2x.png": 40,  # 20x20 @2x
    "icon_iphone_20pt@3x.png": 60,  # 20x20 @3x
    "icon_iphone_29pt@2x.png": 58,  # 29x29 @2x
    "icon_iphone_29pt@3x.png": 87,  # 29x29 @3x
    "icon_iphone_40pt@2x.png": 80,  # 40x40 @2x
    "icon_iphone_40pt@3x.png": 120,  # 40x40 @3x
    "icon_iphone_60pt@2x.png": 120,  # 60x60 @2x
    "icon_iphone_60pt@3x.png": 180,  # 60x60 @3x
    # iPad
    "icon_ipad_20pt.png": 20,  # 20x20 @1x
    "icon_ipad_20pt@2x.png": 40,  # 20x20 @2x
    "icon_ipad_29pt.png": 29,  # 29x29 @1x
    "icon_ipad_29pt@2x.png": 58,  # 29x29 @2x
    "icon_ipad_40pt.png": 40,  # 40x40 @1x
    "icon_ipad_40pt@2x.png": 80,  # 40x40 @2x
    "icon_ipad_76pt.png": 76,  # 76x76 @1x
    "icon_ipad_76pt@2x.png": 152,  # 76x76 @2x
    "icon_ipad_83_5pt@2x.png": 167,  # 83.5x83.5 @2x
    # App Store (ios-marketing)
    "icon_marketing_1024.png": 1024,  # 1024x1024
}

IOS_APPICON_NAME_MAP: dict[str, str] = {
    "AppIcon-20@2x.png": "icon_iphone_20pt@2x.png",
    "AppIcon-20@3x.png": "icon_iphone_20pt@3x.png",
    "AppIcon-29@2x.png": "icon_iphone_29pt@2x.png",
    "AppIcon-29@3x.png": "icon_iphone_29pt@3x.png",
    "AppIcon-40@2x.png": "icon_iphone_40pt@2x.png",
    "AppIcon-40@3x.png": "icon_iphone_40pt@3x.png",
    "AppIcon-60@2x.png": "icon_iphone_60pt@2x.png",
    "AppIcon-60@3x.png": "icon_iphone_60pt@3x.png",
    "AppIcon-20@1x.png": "icon_ipad_20pt.png",
    "AppIcon-29@1x.png": "icon_ipad_29pt.png",
    "AppIcon-40@1x.png": "icon_ipad_40pt.png",
    "AppIcon-76@1x.png": "icon_ipad_76pt.png",
    "AppIcon-76@2x.png": "icon_ipad_76pt@2x.png",
    "AppIcon-83.5@2x.png": "icon_ipad_83_5pt@2x.png",
    "AppIcon-1024.png": "icon_marketing_1024.png",
}

IOS_APPICON_SIZES: dict[str, int] = {
    app_filename: IOS_ICON_SIZES[source_filename]
    for app_filename, source_filename in IOS_APPICON_NAME_MAP.items()
}

# Duplicate sizes allowlist: size -> tuple of filenames that are allowed to share this size
# Some iOS icons intentionally share the same pixel dimensions (e.g., 40px, 58px, 80px, 120px)
IOS_ICON_DUPLICATE_ALLOWLIST: dict[int, tuple[str, ...]] = {
    40: ("icon_iphone_20pt@2x.png", "icon_ipad_20pt@2x.png", "icon_ipad_40pt.png"),
    58: ("icon_iphone_29pt@2x.png", "icon_ipad_29pt@2x.png"),
    80: ("icon_iphone_40pt@2x.png", "icon_ipad_40pt@2x.png"),
    120: ("icon_iphone_40pt@3x.png", "icon_iphone_60pt@2x.png"),
}
