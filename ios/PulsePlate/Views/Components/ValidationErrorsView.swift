import SwiftUI

struct ValidationErrorsView: View {
    let error: BMIServiceError

    var body: some View {
        GroupBox("Error") {
            switch error {
            case .validation(let errors):
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(Array(errors.enumerated()), id: \.offset) { _, e in
                        Text("• \(e.msg)")
                    }
                }
            default:
                Text(error.localizedDescription)
            }
        }
        .foregroundStyle(.red)
    }
}
