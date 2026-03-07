import SwiftUI

struct AIInsightView: View {
    @State private var vm: AIInsightViewModel

    init(vm: AIInsightViewModel) {
        _vm = State(initialValue: vm)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                heroCard
                composerCard
                resultSection
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 24)
        }
        .background(Color.navy.ignoresSafeArea())
        .navigationTitle(localized("ai_insight.navigation.title"))
        .navigationBarTitleDisplayMode(.inline)
    }

    private func localized(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }

    private var heroCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(localized("ai_insight.hero.title"))
                    .font(.title2.weight(.bold))
                    .foregroundStyle(Color.textPrimary)

                Text(localized("ai_insight.hero.subtitle"))
                    .font(.subheadline)
                    .foregroundStyle(Color.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var composerCard: some View {
        @Bindable var bindableVM = vm
        let maxAIQueryLength = AIInsightViewModel.maxQueryLength

        return GlassCard {
            VStack(alignment: .leading, spacing: 12) {
                Text(localized("ai_insight.input.title"))
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)

                ZStack(alignment: .topLeading) {
                    if bindableVM.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Text(localized("ai_insight.input.placeholder"))
                            .font(.body)
                            .foregroundStyle(Color.textTertiary)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 16)
                            .allowsHitTesting(false)
                    }

                    TextEditor(text: $bindableVM.query)
                        .scrollContentBackground(.hidden)
                        .frame(minHeight: 140)
                        .padding(10)
                        .background(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .fill(Color.white.opacity(0.08))
                        )
                        .foregroundStyle(Color.textPrimary)
                        .onChange(of: bindableVM.query) { _, _ in
                            bindableVM.enforceQueryLimit()
                        }
                }

                Text("\(bindableVM.query.count)/\(maxAIQueryLength)")
                    .font(.caption)
                    .foregroundStyle(Color.textTertiary)

                Button {
                    vm.submit()
                } label: {
                    HStack {
                        if vm.state.isLoading {
                            ProgressView()
                                .tint(Color.navy)
                        }
                        Text(localized(vm.state.isLoading ? "ai_insight.submit.loading" : "ai_insight.submit"))
                            .font(.headline)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color.appPrimary)
                .disabled(!vm.canSubmit)
            }
        }
    }

    @ViewBuilder
    private var resultSection: some View {
        switch vm.state {
        case .idle:
            EmptyView()

        case .loading:
            GlassCard {
                VStack(alignment: .leading, spacing: 12) {
                    Text(localized("ai_insight.loading.title"))
                        .font(.headline)
                        .foregroundStyle(Color.textPrimary)
                    ProgressView()
                        .tint(Color.appPrimary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

        case .failed(let message):
            GlassCard {
                VStack(alignment: .leading, spacing: 12) {
                    Text(localized("ai_insight.error.title"))
                        .font(.headline)
                        .foregroundStyle(Color.textPrimary)

                    Text(message)
                        .font(.subheadline)
                        .foregroundStyle(Color.textSecondary)

                    Button(localized("ai_insight.retry")) {
                        vm.retry()
                    }
                    .buttonStyle(.bordered)
                    .disabled(vm.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

        case .loaded(let response):
            LoadedInsightView(response: response)
        }
    }
}

private struct LoadedInsightView: View {
    let response: CBTInsightResponseDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            GlassCard {
                VStack(alignment: .leading, spacing: 12) {
                    Text(localized("ai_insight.result.title"))
                        .font(.headline)
                        .foregroundStyle(Color.textPrimary)

                    Text(response.insight)
                        .font(.body)
                        .foregroundStyle(Color.textPrimary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            GlassCard {
                VStack(alignment: .leading, spacing: 10) {
                    Text(localized("ai_insight.metadata.title"))
                        .font(.headline)
                        .foregroundStyle(Color.textPrimary)

                    metadataRow(
                        label: localized("ai_insight.metadata.confidence"),
                        value: percentString(response.confidence)
                    )
                    metadataRow(
                        label: localized("ai_insight.metadata.uncertainty"),
                        value: percentString(response.uncertainty)
                    )
                    metadataRow(
                        label: localized("ai_insight.metadata.rag_used"),
                        value: localized(response.ragUsed ? "ai_insight.boolean.yes" : "ai_insight.boolean.no")
                    )
                    metadataRow(
                        label: localized("ai_insight.metadata.mode"),
                        value: localizedToken(response.mode, prefix: "ai_insight.mode")
                    )
                    metadataRow(
                        label: localized("ai_insight.metadata.quota_state"),
                        value: localizedToken(response.quotaState, prefix: "ai_insight.quota_state")
                    )
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            if !response.warnings.isEmpty {
                GlassCard {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(localized("ai_insight.warnings.title"))
                            .font(.headline)
                            .foregroundStyle(Color.textPrimary)

                        ForEach(response.warnings, id: \.self) { warning in
                            Label {
                                Text(localizedToken(warning, prefix: "ai_insight.warning"))
                                    .font(.subheadline)
                                    .foregroundStyle(Color.textSecondary)
                            } icon: {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundStyle(Color.warning)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }

            if !response.sources.isEmpty {
                GlassCard {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(localized("ai_insight.sources.title"))
                            .font(.headline)
                            .foregroundStyle(Color.textPrimary)

                        ForEach(response.sources) { source in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(source.file)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(Color.appPrimary)
                                Text(source.preview)
                                    .font(.subheadline)
                                    .foregroundStyle(Color.textSecondary)
                                Text(
                                    String(
                                        format: localized("ai_insight.source.score_format"),
                                        percentValue(source.score)
                                    )
                                )
                                .font(.caption)
                                .foregroundStyle(Color.textTertiary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 4)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private func localized(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }

    private func localizedToken(_ token: String, prefix: String) -> String {
        let key = "\(prefix).\(token.replacingOccurrences(of: "-", with: "_"))"
        let value = localized(key)
        return value == key ? token : value
    }

    private func metadataRow(label: String, value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(Color.textSecondary)
            Spacer(minLength: 16)
            Text(value)
                .multilineTextAlignment(.trailing)
                .foregroundStyle(Color.textPrimary)
        }
        .font(.subheadline)
    }

    private func percentString(_ value: Double) -> String {
        value.formatted(.percent.precision(.fractionLength(0)))
    }

    private func percentValue(_ value: Double) -> Double {
        value * 100
    }
}
