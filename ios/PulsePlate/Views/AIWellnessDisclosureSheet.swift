import SwiftUI

/// Wellness-only disclosure sheet shown before the first AI insight request.
///
/// The user must explicitly accept before any free-text query is sent
/// to the backend. Declining dismisses the sheet without sending data.
struct AIWellnessDisclosureSheet: View {
    let onAccept: () -> Void
    let onDecline: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    headerSection
                    disclosureSection
                    buttonsSection
                }
                .padding(.horizontal, 20)
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
            .background(Color.navy.ignoresSafeArea())
            .navigationTitle(localized("ai_consent.title"))
            .navigationBarTitleDisplayMode(.inline)
        }
        .interactiveDismissDisabled()
        .presentationDetents([.large])
    }

    private var headerSection: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 12) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 36))
                    .foregroundStyle(Color.appPrimary)

                Text(localized("ai_consent.header"))
                    .font(.title3.weight(.bold))
                    .foregroundStyle(Color.textPrimary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var disclosureSection: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 16) {
                disclosurePoint(
                    icon: "leaf.fill",
                    text: localized("ai_consent.point.wellness_only")
                )
                disclosurePoint(
                    icon: "stethoscope",
                    text: localized("ai_consent.point.not_medical")
                )
                disclosurePoint(
                    icon: "server.rack",
                    text: localized("ai_consent.point.data_processing")
                )
                disclosurePoint(
                    icon: "exclamationmark.shield.fill",
                    text: localized("ai_consent.point.no_emergency")
                )
                disclosurePoint(
                    icon: "hand.raised.fill",
                    text: localized("ai_consent.point.voluntary")
                )
            }
        }
    }

    private var buttonsSection: some View {
        VStack(spacing: 12) {
            Button {
                onAccept()
            } label: {
                Text(localized("ai_consent.accept"))
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .tint(Color.appPrimary)

            Button {
                onDecline()
            } label: {
                Text(localized("ai_consent.decline"))
                    .font(.subheadline)
                    .foregroundStyle(Color.textSecondary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
            }
        }
    }

    private func disclosurePoint(icon: String, text: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.body)
                .foregroundStyle(Color.appPrimary)
                .frame(width: 24)

            Text(text)
                .font(.subheadline)
                .foregroundStyle(Color.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func localized(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }
}
