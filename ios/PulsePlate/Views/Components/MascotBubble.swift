import SwiftUI

/// RU: Облачко маскота c локализуемой репликой.
/// EN: Mascot speech bubble with localized line.
struct MascotBubble: View {
  var textKey: LocalizedStringKey

  var body: some View {
    HStack(alignment: .top, spacing: 12) {
      Image("FitChef")
        .resizable().scaledToFit().frame(width: 48, height: 48)
        .accessibilityHidden(true)
      VStack(alignment: .leading, spacing: 6) {
        Text(textKey).foregroundStyle(.white)
        Text("FitChef").font(.caption).foregroundStyle(.white.opacity(0.7))
      }
      .padding(12)
      .background(Color.white.opacity(0.08))
      .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
      .overlay(
        RoundedRectangle(cornerRadius: 12, style: .continuous)
          .stroke(Color.white.opacity(0.12), lineWidth: 1)
      )
    }
    .accessibilityElement(children: .combine)
    .accessibilityLabel(Text("FitChef, ") + Text(textKey))
  }
}
