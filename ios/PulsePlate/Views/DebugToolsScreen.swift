import SwiftUI

private enum Layout {
    /// Extra spacing to keep List content above the floating tab bar capsule in debug builds.
    /// (Standard TabView inset is not enough in this UI.)
    static let bottomInset: CGFloat = 140
    /// Maximum message length for network error truncation.
    static let maxMessageLength = 50
}

struct DebugToolsScreen: View {
    @State private var networkTestResult: String = "Not tested"
    private let apiClient: APIClientProtocol

    init(apiClient: APIClientProtocol = APIClient(baseURL: AppConfig.baseURL())) {
        self.apiClient = apiClient
    }

    var body: some View {
        List {
            Section("PRO Features") {
                NavigationLink("Shopping List Generator") {
                    makeShoppingListScreen()
                }
            }

            Section("Network Test") {
                Button("Test Backend Connection") {
                    Task {
                        await testBackendConnection()
                    }
                }

                Text(networkTestResult)
                    .font(.caption)
                    .foregroundStyle(networkResultColor)
                    .accessibilityLabel("\(networkResultA11yPrefix): \(networkTestResult)")
            }

            Section("Configuration") {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Base URL")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(AppConfig.baseURL().absoluteString)
                        .font(.footnote)
                        .foregroundStyle(.primary)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("PRO API Key")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if let key = ProKeyProvider.value() {
                        Text(String(key.prefix(8)) + "...")
                            .font(.footnote)
                            .foregroundStyle(.primary)
                    } else {
                        Text("Not configured")
                            .font(.footnote)
                            .foregroundStyle(.orange)
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Debug Tools")
        .navigationBarTitleDisplayMode(.large)
        .safeAreaInset(edge: .bottom) {
            Color.clear.frame(height: Layout.bottomInset)
        }
    }

    private var networkResultColor: Color {
        if networkTestResult.contains("✅") { return .green }
        if networkTestResult.contains("❌") { return .red }
        return .orange
    }

    private var networkResultA11yPrefix: String {
        if networkTestResult.contains("✅") { return "Success" }
        if networkTestResult.contains("❌") { return "Error" }
        return "Status"
    }

    private func makeShoppingListScreen() -> some View {
        let service = DefaultShoppingListService(baseURL: AppConfig.baseURL())
        let vm = ShoppingListReaderViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() }
        )
        return ShoppingListReaderScreen(
            vm: vm,
            planData: ShoppingListStubPlan.minimal()
        )
    }

    private func testBackendConnection() async {
        networkTestResult = "Testing..."
        do {
            // Transport-only probe via APIClient (no direct URLSession in UI).
            // We intentionally keep this tolerant: decoding failures still confirm connectivity.
            let _: DebugHealthProbe = try await apiClient.get(path: "health")
            networkTestResult = "✅ Connected: /health"
        } catch let apiError as APIError {
            switch apiError {
            case .decodingFailed:
                // Response is reachable but not JSON in expected shape (still confirms connectivity).
                networkTestResult = "✅ Connected (unexpected payload): /health"
            case .api(let statusCode, _):
                networkTestResult = "✅ Connected: HTTP \(statusCode)"
            case .validation:
                networkTestResult = "✅ Connected: HTTP 422"
            case .invalidResponse:
                networkTestResult = "⚠️ Invalid response type"
            default:
                networkTestResult = "⚠️ Error: \(String(describing: apiError).prefix(Layout.maxMessageLength))..."
            }
        } catch let error as NSError {
            let msg = error.localizedDescription
            if msg.contains("App Transport Security") {
                networkTestResult = "❌ ATS BLOCKED: \(msg.prefix(Layout.maxMessageLength))..."
            } else if msg.contains("refused") || msg.contains("offline") {
                networkTestResult = "✅ ATS OK (backend not running): \(msg.prefix(Layout.maxMessageLength))..."
            } else {
                networkTestResult = "⚠️ Error: \(msg.prefix(Layout.maxMessageLength))..."
            }
        }
    }
}

/// Minimal probe DTO for `/health`.
/// We accept any JSON object; extra keys are ignored.
private struct DebugHealthProbe: Decodable {
    let status: String?
    let ok: Bool?
}

#Preview {
    DebugToolsScreen()
}
