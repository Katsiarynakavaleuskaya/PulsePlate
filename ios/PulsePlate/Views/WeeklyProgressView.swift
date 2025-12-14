import SwiftUI
import Charts

struct WeeklyProgressView: View {
    @StateObject private var hk = HealthKitManager()
    @State private var week: [DailyNutritionTotals] = []
    @State private var latestWeightKg: Double?
    @State private var showAlert = false

    // Статический форматтер для осей и подписей
    static let axisFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "EE"
        f.locale = Locale.current
        return f
    }()
    static let shortFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .short
        f.locale = Locale.current
        return f
    }()

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if hk.isAuthorized {
                        if week.isEmpty {
                            Text(LocalizationManager.shared.localized("week_no_data"))
                                .foregroundStyle(.secondary)
                        } else {
                            Chart(week) {
                                BarMark(
                                    x: .value(LocalizationManager.shared.localized("axis_day"), $0.date, unit: .day),
                                    y: .value(LocalizationManager.shared.localized("unit_kcal"), $0.energyKCal)
                                )
                                .cornerRadius(6)
                                .foregroundStyle(.blue)
                            }
                            .chartXAxis {
                                AxisMarks(values: .stride(by: .day)) { v in
                                    if let d: Date = v.as(Date.self) {
                                        AxisValueLabel(Self.axisFormatter.string(from: d).uppercased())
                                    }
                                }
                            }
                            .frame(height: 220)
                            .accessibilityLabel(LocalizationManager.shared.localized("week_chart_accessibility"))

                            if let w = latestWeightKg {
                                Text(String(format: "%@ %.1f %@", LocalizationManager.shared.localized("weight_label"), w, LocalizationManager.shared.localized("unit_kg")))
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
                        Text(LocalizationManager.shared.localized("health_permission_message"))
                            .foregroundStyle(.secondary)
                    }

                    Button(hk.isAuthorized ? LocalizationManager.shared.localized("week_refresh") : LocalizationManager.shared.localized("health_request")) {
                        if hk.isAuthorized { Task { await reloadWeek() } }
                        else { hk.requestAuthorization() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .padding()
            }
            .navigationTitle(LocalizationManager.shared.localized("week_title"))
        }
        .task {
            if hk.isAuthorized {
                await reloadWeek()
            }
        }
        .alert(LocalizationManager.shared.localized("healthkit_alert_title"), isPresented: $showAlert) {
            Button(LocalizationManager.shared.localized("ok_button"), role: .cancel) { hk.error = nil; showAlert = false }
        } message: {
            Text(hk.error?.localizedDescription ?? "")
        }
        .onChange(of: hk.error?.localizedDescription) {
            showAlert = hk.error != nil
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
        let df = Self.shortFormatter
        let energyUnit = LocalizationManager.shared.localized("unit_kcal")
        let proteinAbbr = LocalizationManager.shared.localized("abbr_protein")
        let fatAbbr = LocalizationManager.shared.localized("abbr_fat")
        let carbsAbbr = LocalizationManager.shared.localized("abbr_carbs")
        let gramUnit = LocalizationManager.shared.localized("unit_gram")
        let formatString = LocalizationManager.shared.localized("weekly_progress_accessibility_line")
        return String(format: formatString,
                      df.string(from: d.date),
                      Int(d.energyKCal), energyUnit,
                      proteinAbbr, Int(d.proteinG), gramUnit,
                      fatAbbr, Int(d.fatG), gramUnit,
                      carbsAbbr, Int(d.carbsG), gramUnit)
    }
}
