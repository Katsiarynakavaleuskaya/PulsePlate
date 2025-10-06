/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ResultView from "../ResultView";
import type { SetupFormValues } from "../schema";

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
      plateData: {
        plate: {
          carbs_pct: 50,
          protein_pct: 25,
          fat_pct: 25,
          kcal: 2000,
        },
        macros: {
          carbs_g: 250,
          protein_g: 125,
          fat_g: 55,
          fiber_g: 25,
        },
        water_l: 2.5,
      },
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
    mockUseSetupCalc.mockReturnValue({
      ...mockUseSetupCalc(),
      error: "API Error",
      bmrData: null,
      plateData: null,
    });

    renderResult();

    expect(screen.getByText("Ошибка расчета")).toBeInTheDocument();
    expect(screen.getByText("API Error")).toBeInTheDocument();
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

  it("calls onEdit when edit button is clicked", () => {
    renderResult();

    const editButton = screen.getByText("Изменить анкету");
    fireEvent.click(editButton);

    expect(mockOnEdit).toHaveBeenCalledTimes(1);
  });
});
