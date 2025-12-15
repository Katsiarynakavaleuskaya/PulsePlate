import SwiftUI

struct DebugToolsScreen: View {
    @State private var networkTestResult: String = "Not tested"

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
                    .foregroundStyle(networkTestResult.contains("✅") ? .green : .orange)
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
            let url = URL(string: "\(AppConfig.baseURL())/docs")!
            let (_, response) = try await URLSession.shared.data(from: url)
            if let http = response as? HTTPURLResponse {
                networkTestResult = "✅ Connected: HTTP \(http.statusCode)"
            } else {
                networkTestResult = "⚠️ Invalid response type"
            }
        } catch let error as NSError {
            let msg = error.localizedDescription
            if msg.contains("App Transport Security") {
                networkTestResult = "❌ ATS BLOCKED: \(msg.prefix(60))..."
            } else if msg.contains("refused") || msg.contains("offline") {
                networkTestResult = "✅ ATS OK (backend not running): \(msg.prefix(40))..."
            } else {
                networkTestResult = "⚠️ Error: \(msg.prefix(50))..."
            }
        }
    }
}

#Preview {
    DebugToolsScreen()
}
