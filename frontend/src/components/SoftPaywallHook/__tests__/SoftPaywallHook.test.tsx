/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SoftPaywallHook from "../SoftPaywallHook";
import type { components } from "../../../api/schema";

// Mock react-router-dom useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("SoftPaywallHook", () => {
  const mockHook: components["schemas"]["SoftPaywallHook"] = {
    id: "bmi.pro_interpretation_v1",
    kind: "cta",
    position: "post_result",
    priority: 50,
    target: "pro_paywall",
    message: {
      lang: "en",
      title_key: "soft_paywall.title",
      body_key: "soft_paywall.body",
      cta_key: "soft_paywall.cta",
      default_title: "More accurate interpretation",
      default_body: "BMI doesn't account for muscle mass, bone density, and body composition. Get PRO insights.",
      default_cta: "See PRO",
    },
    availability: { pro_available: true },
  };

  beforeEach((): void => {
    vi.clearAllMocks();
  });

  it("renders when hook provided", (): void => {
    render(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} />
      </MemoryRouter>
    );

    expect(screen.getByText("More accurate interpretation")).toBeInTheDocument();
    expect(screen.getByText("BMI doesn't account for muscle mass, bone density, and body composition. Get PRO insights.")).toBeInTheDocument();
    expect(screen.getByText("See PRO")).toBeInTheDocument();
    expect(screen.getByTestId("soft-paywall-cta")).toBeInTheDocument();
  });

  it("does not crash and renders nothing for null hook", (): void => {
    const { container } = render(
      <MemoryRouter>
        <SoftPaywallHook hook={null} />
      </MemoryRouter>
    );
    expect(container.firstChild).toBeNull();
  });

  it("does not crash and renders nothing for undefined hook", (): void => {
    const { container } = render(
      <MemoryRouter>
        <SoftPaywallHook hook={undefined} />
      </MemoryRouter>
    );
    expect(container.firstChild).toBeNull();
  });

  it("does not render when pro_available is false", (): void => {
    const hookWithFalseAvailability: components["schemas"]["SoftPaywallHook"] = {
      ...mockHook,
      availability: { pro_available: false },
    };

    const { container } = render(
      <MemoryRouter>
        <SoftPaywallHook hook={hookWithFalseAvailability} />
      </MemoryRouter>
    );
    expect(container.firstChild).toBeNull();
  });

  it("navigates to /pro on CTA click when no custom handler", (): void => {
    render(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} />
      </MemoryRouter>
    );

    // Assert no navigation on mount
    expect(mockNavigate).not.toHaveBeenCalled();

    const ctaButton = screen.getByTestId("soft-paywall-cta");
    fireEvent.click(ctaButton);

    // Assert exactly one navigation call with correct path
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/pro");
  });

  it("calls custom onCtaClick handler when provided", (): void => {
    const customHandler = vi.fn();

    render(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} onCtaClick={customHandler} />
      </MemoryRouter>
    );

    const ctaButton = screen.getByTestId("soft-paywall-cta");
    fireEvent.click(ctaButton);

    expect(customHandler).toHaveBeenCalledTimes(1);
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
