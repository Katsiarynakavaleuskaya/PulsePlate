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
        .package(url: "https://github.com/airbnb/lottie-ios", exact: "4.6.1")
    ],
    targets: [
        .target(
            name: "PulsePlate",
            dependencies: [
                .product(name: "Lottie", package: "lottie-ios")
            ],
            path: "../../../PulsePlate",
            resources: [
                .process("Assets.xcassets"),
                .process("Resources")
            ]
            // Note: In hybrid Xcode/SPM setup, use Bundle.main for assets
            // In UI code, use: Image("FitChef", bundle: .main)
            // instead of: Image("FitChef")
        ),
    ]
)
