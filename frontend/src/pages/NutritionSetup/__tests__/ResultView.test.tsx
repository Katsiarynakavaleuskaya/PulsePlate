/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi } from "vitest";
import type { Mock } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ResultView from "../ResultView";
import { mockPlateData } from "../mocks";
import { mockValues } from "./test-utils";

const translations: Record<string, string> = {
  "nutrition.macros.title": "Макронутриенты и калории",
  "nutrition.macros.caloriesLabel": "Калории (цель)",
  "nutrition.macros.carbs": "Углеводы",
  "nutrition.macros.carbsLabel": "Углеводы",
  "nutrition.macros.protein": "Белки",
  "nutrition.macros.proteinLabel": "Белки",
  "nutrition.macros.fat": "Жиры",
  "nutrition.macros.fatLabel": "Жиры",
  "nutrition.macros.fiberLabel": "Клетчатка",
  "nutrition.macros.bmrLabel": "BMR",
  "nutrition.macros.tdeeLabel": "TDEE",
  "nutrition.macros.bmrDescription": "базовый метаболизм",
  "nutrition.macros.tdeeDescription": "общий расход калорий",
  "nutrition.units.kcalPerDay": "ккал/день",
  "nutrition.units.gPerDay": "г/день",
  "nutrition.loadingPlate": "Рассчитываем вашу персональную тарелку...",
  "nutrition.error.title": "Ошибка расчета",
  "nutrition.error.description": "Не удалось загрузить данные. Проверьте подключение к интернету.",
  "nutrition.error.editButton": "Изменить данные",
  "nutrition.header.title": "Ваша персональная тарелка",
  "nutrition.header.subtitle": "Расчет основан на ваших параметрах",
  "nutrition.header.editButton": "Изменить анкету",
  "nutrition.summary.bmr": "BMR (ккал)",
  "nutrition.summary.tdee": "TDEE (ккал)",
  "nutrition.summary.goal": "Цель (ккал)",
  "nutrition.summary.method": "Метод",
  "nutrition.micros.title": "Цели по микроэлементам",
  "nutrition.micros.description": "Рекомендуемые суточные нормы витаминов и минералов для вашего возраста и пола",
  "nutrition.water.title": "Вода",
  "nutrition.water.subtitle": "Рекомендуемое суточное потребление воды",
  "nutrition.water.unit": "л/день",
  "nutrition.water.tip": "💡 Совет: Пейте воду равномерно в течение дня. Увеличивайте потребление при физической активности или жаркой погоде.",
  "common.retrying": "Повторная попытка...",
  "common.tryAgain": "Попробовать снова",
};

const translate = (key: string) => translations[key] || key;

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    i18n: { language: "ru" },
    t: translate,
  }),
}));

// Mock hooks
vi.mock("../hooks", () => ({
  useSetupCalc: vi.fn(),
  useTargets: vi.fn(),
  resolveSetupLang: vi.fn(() => 'ru'),
}));

// Get references to mocked functions for test manipulation
import * as setupHooks from "../hooks";
const mockUseSetupCalc = setupHooks.useSetupCalc as unknown as Mock;
const mockUseTargets = setupHooks.useTargets as unknown as Mock;
const mockResolveSetupLang = setupHooks.resolveSetupLang as unknown as Mock;

describe("ResultView", () => {
  const mockOnEdit = vi.fn();

  const renderResult = () =>
    render(
      <MemoryRouter>
        <ResultView values={mockValues} onEdit={mockOnEdit} />
      </MemoryRouter>
    );

  beforeEach(() => {
    vi.clearAllMocks();
    mockResolveSetupLang.mockReturnValue('en');

    // Default mock implementations
    mockUseSetupCalc.mockReturnValue({
      bmrData: {
        bmr: 1400,
        tdee: 1800,
        method: "Mifflin-St Jeor",
      },
      plateData: mockPlateData,
      loading: false,
      error: null,
    });

    mockUseTargets.mockReturnValue({
      data: {
        micros: [
          { id: "fe", name: "Железо", unit: "мг", target: 18 },
          { id: "ca", name: "Кальций", unit: "мг", target: 1000 },
        ],
        water_l: 2.5,
      },
      loading: false,
      error: null,
    });
  });

  it("renders loading state", () => {
    const baseMock = {
      bmrData: { bmr: 1400, tdee: 1800, method: "Mifflin-St Jeor" },
      plateData: mockPlateData,
      loading: false,
      error: null,
    };
    mockUseSetupCalc.mockReturnValue({
      bmrData: null,
      plateData: null,
      loading: true,
      error: null,
    });
    mockUseTargets.mockReturnValue({
      data: null,
      loading: true,
      error: null,
    });

    renderResult();

    // Check that loading spinner is present
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseSetupCalc.mockImplementationOnce(() => ({
      bmrData: null,
      plateData: null,
      loading: false,
      error: "API Error",
    }));

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.getByText("API Error")).toBeInTheDocument();
  });

  it("renders error state from useTargets", () => {
    mockUseSetupCalc.mockImplementationOnce(() => ({
      bmrData: { bmr: 1400, tdee: 1800, method: "Mifflin-St Jeor" },
      plateData: mockPlateData,
      loading: false,
      error: null,
    }));

    mockUseTargets.mockReturnValue({
      error: "Targets API Error",
      data: null,
      loading: false,
    });

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.getByText("Targets API Error")).toBeInTheDocument();
  });

  it("renders results successfully", () => {
    renderResult();

    expect(screen.getByText("Ваша персональная тарелка")).toBeInTheDocument();
    expect(screen.getByText("BMR (ккал)")).toBeInTheDocument();
    expect(screen.getByText("TDEE (ккал)")).toBeInTheDocument();
    expect(screen.getByText("Цель (ккал)")).toBeInTheDocument();
    expect(screen.getByText("Макронутриенты и калории")).toBeInTheDocument();
    expect(screen.getByText("Цели по микроэлементам")).toBeInTheDocument();
  });

  it("displays BMR and TDEE values", () => {
    renderResult();

    // Check BMR summary card
    expect(screen.getByText("BMR (ккал)")).toBeInTheDocument();
    expect(screen.getByText("TDEE (ккал)")).toBeInTheDocument();
    expect(screen.getByText("Цель (ккал)")).toBeInTheDocument();
  });

  it("displays macronutrient distribution", () => {
    renderResult();

    expect(screen.getByText("Углеводы: 50%")).toBeInTheDocument();
    expect(screen.getByText("Белки: 25%")).toBeInTheDocument();
    expect(screen.getByText("Жиры: 25%")).toBeInTheDocument();
  });

  it("displays non-standard macronutrient percentages", () => {
    const base = mockUseSetupCalc();
    mockUseSetupCalc.mockReturnValue({
      ...base,
      plateData: {
        ...base.plateData,
        plate: {
          ...base.plateData.plate,
          carbs_pct: 80,
          protein_pct: 10,
          fat_pct: 5,
        },
      },
    });

    renderResult();

    expect(screen.getByText("Углеводы: 80%")).toBeInTheDocument();
    expect(screen.getByText("Белки: 10%")).toBeInTheDocument();
    expect(screen.getByText("Жиры: 5%")).toBeInTheDocument();
  });

  it("handles macronutrient percentages totaling more than 100%", () => {
    const base = mockUseSetupCalc();
    mockUseSetupCalc.mockReturnValue({
      ...base,
      plateData: {
        ...base.plateData,
        plate: {
          ...base.plateData.plate,
          carbs_pct: 60,
          protein_pct: 30,
          fat_pct: 30,
        },
      },
    });

    renderResult();

    expect(screen.getByText("Углеводы: 60%")).toBeInTheDocument();
    expect(screen.getByText("Белки: 30%")).toBeInTheDocument();
    expect(screen.getByText("Жиры: 30%")).toBeInTheDocument();
  });

  it("handles macronutrient percentages with edge values (0% and 100%)", () => {
    const base = mockUseSetupCalc();
    mockUseSetupCalc.mockReturnValue({
      ...base,
      plateData: {
        ...base.plateData,
        plate: {
          ...base.plateData.plate,
          carbs_pct: 0,
          protein_pct: 100,
          fat_pct: 0,
        },
      },
    });

    renderResult();

    expect(screen.getByText("Углеводы: 0%")).toBeInTheDocument();
    expect(screen.getByText("Белки: 100%")).toBeInTheDocument();
    expect(screen.getByText("Жиры: 0%")).toBeInTheDocument();
  });

  it("displays macro cards", () => {
    renderResult();

    expect(screen.getByText("Калории (цель)")).toBeInTheDocument();
    expect(screen.getByText("Углеводы")).toBeInTheDocument();
    expect(screen.getByText("Белки")).toBeInTheDocument();
    expect(screen.getByText("Жиры")).toBeInTheDocument();
    expect(screen.getByText("Клетчатка")).toBeInTheDocument();
  });

  it("displays water recommendation", () => {
    renderResult();

    expect(screen.getByText("Вода")).toBeInTheDocument();
    expect(screen.getByText("2.5 л/день")).toBeInTheDocument();
  });

  it("displays micronutrient targets", () => {
    renderResult();

    expect(screen.getByText("Железо")).toBeInTheDocument();
    expect(screen.getByText("Кальций")).toBeInTheDocument();
    // Check that we have the targets grid
    expect(screen.getByText("Цели по микроэлементам")).toBeInTheDocument();
  });

  it("handles missing bmrData gracefully", () => {
    mockUseSetupCalc.mockReturnValue({
      bmrData: null,
      plateData: mockUseSetupCalc().plateData,
      loading: false,
      error: "BMR calculation failed",
    });

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.queryByText("BMR (ккал)")).not.toBeInTheDocument();
  });

  it("handles missing plateData gracefully", () => {
    mockUseSetupCalc.mockReturnValue({
      bmrData: mockUseSetupCalc().bmrData,
      plateData: null,
      loading: false,
      error: "Plate calculation failed",
    });

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.queryByText("Ваша персональная тарелка")).not.toBeInTheDocument();
  });

  it("handles missing targetsData gracefully", () => {
    mockUseTargets.mockReturnValue({
      data: null,
      loading: false,
      error: null,
    });

    renderResult();

    // Should still render main content, just without micronutrients section
    expect(screen.getByText("Ваша персональная тарелка")).toBeInTheDocument();
    expect(screen.queryByText("Цели по микроэлементам")).not.toBeInTheDocument();
  });

  it("handles undefined bmrData, plateData, and targetsData", () => {
    mockUseSetupCalc.mockReturnValue({
      bmrData: undefined,
      plateData: undefined,
      loading: false,
      error: "All data undefined",
    });
    mockUseTargets.mockReturnValue({
      data: undefined,
      loading: false,
      error: null,
    });

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.getByText("All data undefined")).toBeInTheDocument();
  });

  it("calls onEdit when edit button is clicked", () => {
    renderResult();

    const editButton = screen.getByText("Изменить анкету");
    fireEvent.click(editButton);

    expect(mockOnEdit).toHaveBeenCalledTimes(1);
  });

  it("handles retry functionality correctly", () => {
    // Start with error state
    mockUseSetupCalc.mockReturnValue({
      bmrData: null,
      plateData: null,
      loading: false,
      error: "Network Error",
    });
    mockUseTargets.mockReturnValue({
      data: null,
      loading: false,
      error: null,
    });

    renderResult();

    // Check that retry button is present and enabled
    const retryButton = screen.getByText("Попробовать снова");
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).not.toBeDisabled();

    // Setup mocks to return loading state for the retry
    mockUseSetupCalc.mockImplementationOnce(() => ({
      bmrData: null,
      plateData: null,
      loading: true,
      error: null,
    }));
    mockUseTargets.mockImplementationOnce(() => ({
      data: null,
      loading: true,
      error: null,
    }));

    // Click retry - should trigger hooks with new retryKey
    fireEvent.click(retryButton);

    // After retry click, hooks should be called with retryKey = 1
    expect(mockUseSetupCalc).toHaveBeenLastCalledWith(mockValues, "en", 1);
    expect(mockUseTargets).toHaveBeenLastCalledWith(mockValues, "en", 1);

    // Should show loading state with retry message
    expect(screen.getByText("Повторная попытка...")).toBeInTheDocument();

    // Setup mocks to return success data for subsequent renders
    mockUseSetupCalc.mockReturnValue({
      bmrData: {
        bmr: 1400,
        tdee: 1800,
        method: "Mifflin-St Jeor",
      },
      plateData: mockPlateData,
      loading: false,
      error: null,
    });
    mockUseTargets.mockReturnValue({
      data: {
        micros: [
          { id: "fe", name: "Железо", unit: "мг", target: 18 },
          { id: "ca", name: "Кальций", unit: "мг", target: 1000 },
        ],
        water_l: 2.5,
      },
      loading: false,
      error: null,
    });

    // Re-render to simulate successful data load (component will re-render when hooks return success)
    renderResult();

    // Should now show success UI
    expect(screen.getByText("Ваша персональная тарелка")).toBeInTheDocument();
    expect(screen.getByText("BMR (ккал)")).toBeInTheDocument();
    expect(screen.getByText("TDEE (ккал)")).toBeInTheDocument();
    expect(screen.getByText("Цель (ккал)")).toBeInTheDocument();
    expect(screen.getByText("Цели по микроэлементам")).toBeInTheDocument();
  });
});
