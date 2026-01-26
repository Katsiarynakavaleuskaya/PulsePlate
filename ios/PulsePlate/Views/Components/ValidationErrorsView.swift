import SwiftUI

struct ValidationErrorsView: View {
    let error: APIError

    var body: some View {
        GroupBox {
            switch error {
            case .validation(let response):
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(Array(response.detail.enumerated()), id: \.offset) { _, e in
                        Text("• \(e.msg)")
                    }
                }
            default:
                Text(error.localizedDescription)
            }
        } label: {
            Text(LocalizedStringKey("Error"))
        }
        .foregroundStyle(.red)
    }
}
