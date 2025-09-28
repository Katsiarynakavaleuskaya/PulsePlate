import SwiftUI
import Charts

struct WeeklyProgressView: View {
    @StateObject private var hk = HealthKitManager()
    @ObservedObject var localization = LocalizationManager.shared
    @State private var week: [DailyNutritionTotals] = []
    @State private var latestWeightKg: Double?

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if hk.isAuthorized {
                        if week.isEmpty {
                            Text(localization.localized("weekly_progress_no_data")).foregroundStyle(.secondary)
                        } else {
                            Chart(week) {
                                BarMark(
                                    x: .value("День", $0.date, unit: .day),
                                    y: .value("ккал", $0.energyKCal)
                                )
                                .cornerRadius(6)
                                .foregroundStyle(.blue)
                            }
                            .chartXAxis {
                                AxisMarks(values: .stride(by: .day)) { v in
                                    if let d: Date = v.as(Date.self) {
                                        let f = DateFormatter(); f.dateFormat = "EE"
                                        AxisValueLabel(f.string(from: d).uppercased())
                                    }
                                }
                            }
                            .frame(height: 220)
                            .accessibilityLabel(localization.localized("weekly_progress_chart_accessibility"))

                            if let w = latestWeightKg {
                                Text(String(format: localization.localized("weekly_progress_weight"), w))
                                    .font(.callout)
                                    .foregroundStyle(.secondary)
                            }

                            // Озвучиваем ключевые цифры для VO
                            VStack(alignment: .leading, spacing: 4) {
                                ForEach(week) { d in
                                    Text(accessibleLine(for: d))
                                        .font(.caption)
                                }
                            }
                            .accessibilityHidden(true)
                        }
                    } else {
                        Text(localization.localized("weekly_progress_health_permission"))
                            .foregroundStyle(.secondary)
                    }

                    Button(hk.isAuthorized ? localization.localized("weekly_progress_update") : localization.localized("weekly_progress_request_access")) {
                        if hk.isAuthorized { Task { await reloadWeek() } }
                        else { hk.requestAuthorization() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .padding()
            }
            .navigationTitle(localization.localized("weekly_progress_title"))
        }
        .task {
            if hk.isAuthorized {
                await reloadWeek()
            }
        }
        .alert("HealthKit", isPresented: .constant(hk.error != nil)) {
            Button("OK", role: .cancel) { hk.error = nil }
        } message: {
            Text(hk.error?.localizedDescription ?? "")
        }
    }

    private func reloadWeek() async {
        do {
            week = try await hk.fetchWeekTotals(weekOf: Date())
            latestWeightKg = try await hk.fetchLatestBodyMass()
        } catch {
            hk.error = error
        }
    }

    private func accessibleLine(for d: DailyNutritionTotals) -> String {
        let df = DateFormatter(); df.dateStyle = .short
        return "\(df.string(from: d.date)): \(Int(d.energyKCal)) ккал, Б \(Int(d.proteinG))г, Ж \(Int(d.fatG))г, У \(Int(d.carbsG))г"
    }
}
