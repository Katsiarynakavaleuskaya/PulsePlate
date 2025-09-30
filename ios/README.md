# PulsePlate iOS Project Structure

## 📁 Project Organization

ios/
├── PulsePlate/                 # Main iOS app source code
│   ├── Assets.xcassets/        # App icons, colors, images
│   ├── Models/                 # Data models
│   ├── Views/                  # SwiftUI views
│   ├── Extensions/             # Swift extensions
│   ├── Resources/              # App resources (animations, etc.)
│   └── Tests/                  # Unit tests
├── Scripts/                    # Shell scripts for automation
│   ├── swift_tools.sh          # Main Swift tools script
│   ├── install_swift_tools.sh  # Install SwiftLint & SwiftFormat
│   ├── xcode_build_phase.sh    # Xcode build phase script
│   └── ...                     # Other automation scripts
├── docs/                       # Documentation
│   ├── SWIFT_TOOLS_SETUP.md    # Swift tools documentation
│   ├── LOTTIE_SETUP_GUIDE.md   # Lottie animation setup
│   └── ...                     # Other documentation
├── assets/                     # Media assets
│   ├── *.mp4                   # Video files
│   ├── *.png                   # Image files
│   └── ...                     # Other media
├── tools/                      # Python tools and utilities
│   ├── generate_app_icons.py   # Icon generation
│   └── ...                     # Other Python tools
├── .swiftlint.yml              # SwiftLint configuration
├── .swiftformat                # SwiftFormat configuration
├── PulsePlate.xcodeproj/       # Xcode project
├── Package.swift               # Swift Package Manager
└── swift_tools.sh              # Main entry point
