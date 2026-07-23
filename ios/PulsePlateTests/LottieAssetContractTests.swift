import Lottie
import XCTest
@testable import PulsePlate

final class LottieAssetContractTests: XCTestCase {
    func testCatalogContainsOnlyTheBundledBlinkAsset() {
        XCTAssertEqual(FitChefLottieAsset.allCases.map(\.rawValue), ["fitchef_blink"])
    }

    func testCatalogResourcesExistInTheMainBundle() {
        for asset in FitChefLottieAsset.allCases {
            XCTAssertNotNil(
                Bundle.main.url(forResource: asset.rawValue, withExtension: "json"),
                "Missing bundled Lottie resource: \(asset.rawValue).json"
            )
        }
    }

    func testCatalogResourcesParseWithLottie() {
        for asset in FitChefLottieAsset.allCases {
            XCTAssertNotNil(
                LottieAnimation.named(asset.rawValue, bundle: .main),
                "Invalid bundled Lottie resource: \(asset.rawValue).json"
            )
        }
    }

    func testPlaybackPolicyAnimatesOnlyLoadedAssetsWithoutReduceMotion() {
        XCTAssertEqual(
            FitChefLottiePlaybackPolicy.resolve(reduceMotion: false, animationLoaded: true),
            .animated
        )
        XCTAssertEqual(
            FitChefLottiePlaybackPolicy.resolve(reduceMotion: true, animationLoaded: true),
            .staticFallback(.reduceMotion)
        )
        XCTAssertEqual(
            FitChefLottiePlaybackPolicy.resolve(reduceMotion: false, animationLoaded: false),
            .staticFallback(.assetUnavailable)
        )
    }
}
