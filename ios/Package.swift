// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PulsePlate",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "PulsePlate",
            targets: ["PulsePlate"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/airbnb/lottie-ios.git", from: "4.4.0")
    ],
    targets: [
        .target(
            name: "PulsePlate",
            dependencies: [
                .product(name: "Lottie", package: "lottie-ios")
            ]
        ),
    ]
)
