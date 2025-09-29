# PulsePlate iOS Project Structure

## 📁 Project Organization

```
ios/
├── PulsePlate/                 # Main iOS app source code
│   ├── Assets.xcassets/        # App icons, colors, images
│   ├── Models/                 # Data models
│   ├── Views/                  # SwiftUI views
│   ├── Extensions/             # Swift extensions
│   ├── Resources/              # App resources (animations, etc.)
│   └── Tests/                  # Unit tests
├── scripts/                    # Shell scripts for automation
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
├── config/                     # Configuration files
│   ├── .swiftlint.yml          # SwiftLint configuration
│   └── .swiftformat            # SwiftFormat configuration
├── PulsePlate.xcodeproj/       # Xcode project
├── Package.swift               # Swift Package Manager
└── swift_tools.sh              # Main entry point
```

## 🚀 Quick Start

### 1. Organize Project Structure
```bash
# Run the organization script
chmod +x organize_project.sh
./organize_project.sh
```

### 2. Install Swift Tools
```bash
./scripts/install_swift_tools.sh
```

### 3. Run Swift Tools
```bash
# Format and lint code
./swift_tools.sh all

# Check code quality only
./swift_tools.sh lint

# Format code only
./swift_tools.sh format
```

### 4. Xcode Integration
Add `scripts/xcode_build_phase.sh` as a Build Phase in Xcode for automatic formatting and linting.

## 📋 Available Scripts

### Main Scripts
- `swift_tools.sh` - Main entry point for all Swift tools
- `scripts/install_swift_tools.sh` - Install SwiftLint & SwiftFormat
- `scripts/xcode_build_phase.sh` - Xcode build phase integration

### Utility Scripts
- `scripts/install_lottie.sh` - Install Lottie animations
- `scripts/install_icons_from_zip.sh` - Install app icons
- `scripts/update_icons.sh` - Update app icons
- `scripts/move_mascot.sh` - Move mascot assets

### Python Tools
- `tools/generate_app_icons.py` - Generate app icons from source
- `tools/quick_icon_generator.py` - Quick icon generation

## ⚙️ Configuration

### SwiftLint
Configuration file: `config/.swiftlint.yml`
- Apple HIG compliant rules
- Health app specific rules
- 120 character line limit

### SwiftFormat
Configuration file: `config/.swiftformat`
- Apple HIG style formatting
- 4-space indentation
- Automatic code cleanup

## 🔧 Development Workflow

1. **Before coding**: Run `./swift_tools.sh format` to format existing code
2. **During development**: Use Xcode build phase for automatic formatting
3. **Before commit**: Run `./swift_tools.sh all` to format and lint
4. **CI/CD**: Use scripts in GitHub Actions

## 📚 Documentation

- `docs/SWIFT_TOOLS_SETUP.md` - Detailed Swift tools setup
- `docs/LOTTIE_SETUP_GUIDE.md` - Lottie animation setup
- `docs/ICON_INSTRUCTIONS.md` - App icon setup
- `docs/VIDEO_SETUP_GUIDE.md` - Video asset setup

## 🎯 Best Practices

1. **Keep organized**: Use the folder structure for all new files
2. **Document changes**: Update relevant docs when adding new features
3. **Use automation**: Leverage scripts for repetitive tasks
4. **Follow Apple HIG**: Use SwiftLint and SwiftFormat configurations
5. **Test regularly**: Run tools before committing code

## 🛠️ Troubleshooting

### Problem: "Permission denied"
```bash
chmod +x organize_project.sh
chmod +x swift_tools.sh
chmod +x scripts/*.sh
```

### Problem: "SwiftLint not found"
```bash
./scripts/install_swift_tools.sh
```

### Problem: "Config files not found"
```bash
# Make sure you ran the organization script
./organize_project.sh
```
