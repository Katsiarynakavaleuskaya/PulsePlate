// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PulsePlate",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v17),
        .macOS(.v10_15)
    ],
    products: [
        .library(
            name: "PulsePlate",
            targets: ["PulsePlate"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/airbnb/lottie-ios.git", from: "4.5.2")
    ],
    targets: [
        .target(
            name: "PulsePlate",
            dependencies: [
                .product(name: "Lottie", package: "lottie-ios")
            ],
            path: "PulsePlate",
            resources: [
                .process("Assets.xcassets"),
                .process("Resources")
            ]
            // Note: Assets loaded via SPM require Bundle.module
            // In UI code, use: Image("FitChef", bundle: .module)
            // instead of: Image("FitChef")
        ),
    ]
)
