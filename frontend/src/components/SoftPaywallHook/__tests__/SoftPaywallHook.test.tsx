/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SoftPaywallHook from "../SoftPaywallHook";
import type { components } from "../../../api/schema";

const analyticsMock = vi.hoisted(() => ({
  createAnalyticsEventId: vi.fn(),
  logPaywallExposure: vi.fn(),
}));

vi.mock("../../../lib/analytics", () => analyticsMock);

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
  const { createAnalyticsEventId, logPaywallExposure } = analyticsMock;
  let analyticsIdCounter = 0;
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
  const mockNextBestAction: components["schemas"]["NextBestAction"] = {
    type: "unlock_targets",
    recommended_surface: "pro_targets",
    recommended_tier: "PRO",
    trigger_reason: "targets_ready",
    why_now: "post_bmi_baseline_body_metrics",
  };

  beforeEach((): void => {
    vi.clearAllMocks();
    analyticsIdCounter = 0;
    createAnalyticsEventId.mockImplementation(() => `analytics-id-${++analyticsIdCounter}`);
  });

  afterEach((): void => {
    cleanup();
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

    const ctaPayload = logPaywallExposure.mock.calls.at(-1)?.[0] as
      | Record<string, unknown>
      | undefined;

    // Assert exactly one navigation call with correct path
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/pro", {
      state: {
        exposureId: "analytics-id-1",
        source: "bmi_soft_paywall",
        triggerReason: "post_bmi",
        via: "pro_page",
      },
    });
    expect(ctaPayload?.event_name).toBe("cta_clicked");
    expect(ctaPayload?.exposure_id).toBe("analytics-id-1");
  });

  it("reuses one exposure lifecycle id for shown and CTA events", (): void => {
    render(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByTestId("soft-paywall-cta"));
    expect(logPaywallExposure).toHaveBeenCalledTimes(2);

    const [shownPayload, ctaPayload] = logPaywallExposure.mock.calls.map(
      ([payload]) => payload as Record<string, unknown>
    );

    expect(shownPayload).toMatchObject({
      event_name: "shown",
      source_surface: "bmi_soft_paywall",
      trigger_reason: "post_bmi",
      via: "soft_paywall_hook",
      metadata: {
        hook_id: "bmi.pro_interpretation_v1",
        position: "post_result",
        target: "pro_paywall",
      },
    });
    expect(ctaPayload).toMatchObject({
      event_name: "cta_clicked",
      source_surface: "bmi_soft_paywall",
      trigger_reason: "post_bmi",
      via: "soft_paywall_hook",
      metadata: {
        hook_id: "bmi.pro_interpretation_v1",
        position: "post_result",
        target: "pro_paywall",
      },
    });
    expect(shownPayload.exposure_id).toBe(ctaPayload.exposure_id);
    expect(shownPayload.client_event_id).not.toBe(ctaPayload.client_event_id);
  });

  it("starts a fresh exposure lifecycle when the hook is hidden and shown again", (): void => {
    const { rerender } = render(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} />
      </MemoryRouter>
    );

    rerender(
      <MemoryRouter>
        <SoftPaywallHook hook={null} />
      </MemoryRouter>
    );

    rerender(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} />
      </MemoryRouter>
    );

    const shownCalls = logPaywallExposure.mock.calls
      .map(([payload]) => payload as Record<string, unknown>)
      .filter((payload) => payload.event_name === "shown");

    expect(shownCalls).toHaveLength(2);
    expect(shownCalls[0].exposure_id).not.toBe(shownCalls[1].exposure_id);
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

  it("forwards next_best_action context through the existing paywall route state", (): void => {
    render(
      <MemoryRouter>
        <SoftPaywallHook hook={mockHook} nextBestAction={mockNextBestAction} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByTestId("soft-paywall-cta"));

    expect(mockNavigate).toHaveBeenCalledWith("/pro", {
      state: {
        exposureId: "analytics-id-1",
        source: "bmi_soft_paywall",
        triggerReason: "targets_ready",
        via: "pro_page",
        actionType: "unlock_targets",
        recommendedSurface: "pro_targets",
        recommendedTier: "PRO",
        whyNow: "post_bmi_baseline_body_metrics",
      },
    });

    const ctaPayload = logPaywallExposure.mock.calls.at(-1)?.[0] as
      | Record<string, unknown>
      | undefined;
    expect(ctaPayload?.trigger_reason).toBe("targets_ready");
  });
});
