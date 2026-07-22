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
            path: "PulsePlate",
            resources: [
                .process("Assets.xcassets"),
                .process("Resources")
            ]
            // The Xcode app runtime resolves local Lottie resources from Bundle.main.
            // Package-only Bundle.module semantics must not rewrite the app UI contract.
        ),
    ]
)
