/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ResultView from "../ResultView";
import type { SetupFormValues } from "../schema";
import { mockPlateData } from "../mocks";

// Mock hooks
const mockUseSetupCalc = vi.fn();
const mockUseTargets = vi.fn();

vi.mock("../hooks", () => ({
  useSetupCalc: (...args: any[]) => mockUseSetupCalc(...args),
  useTargets: (...args: any[]) => mockUseTargets(...args),
}));

describe("ResultView", () => {
  const mockValues: SetupFormValues = {
    sex: "female",
    age: 30,
    height_cm: 170,
    weight_kg: 65,
    activity: "moderate",
    goal: "maintain",
    diet_flags: [],
  };

  const mockOnEdit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

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
      },
      loading: false,
      error: null,
    });
  });

  const renderResult = () =>
    render(
      <MemoryRouter>
        <ResultView values={mockValues} onEdit={mockOnEdit} />
      </MemoryRouter>
    );

  it("renders loading state", () => {
    mockUseSetupCalc.mockReturnValue({
      ...mockUseSetupCalc(),
      loading: true,
    });

    renderResult();

    expect(screen.getByText("Рассчитываем вашу персональную тарелку...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    const base = mockUseSetupCalc();
    mockUseSetupCalc.mockReturnValue({
      ...base,
      error: "API Error",
      bmrData: null,
      plateData: null,
    });

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.getByText("API Error")).toBeInTheDocument();
  });

  it("renders error state from useTargets", () => {
    mockUseSetupCalc.mockReturnValue({
      ...mockUseSetupCalc(),
      error: null,
      bmrData: { calories: 2000 },
      plateData: { protein: 100, fat: 70, carbs: 250 },
    });

    mockUseTargets.mockReturnValue({
      error: "Targets API Error",
      targets: null,
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
    expect(screen.getByText("Распределение макронутриентов")).toBeInTheDocument();
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
});
