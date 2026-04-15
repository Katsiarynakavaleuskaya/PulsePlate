/* @vitest-environment jsdom */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PremiumGate from "../PremiumGate";
// Initialize i18n so t() resolves labels
import "../../i18n";
// Import test setup for jest-dom matchers
import "../../test/setup";
import { vi, describe, test, expect, beforeEach } from "vitest";

const gateInteracted = vi.fn();
const upgradeClicked = vi.fn();
const paywallDismissed = vi.fn();

vi.mock("../../lib/useTelemetry", () => ({
  useTelemetry: () => ({
    track: {
      gateInteracted,
      upgradeClicked,
      paywallDismissed,
      moduleViewed: vi.fn(),
      featureClicked: vi.fn(),
      paywallViewed: vi.fn(),
      badgeViewed: vi.fn(),
    },
    isEnabled: true,
    isVip: false,
  }),
}));

vi.mock("../Paywall/BeforeAfter", () => {
  return {
    default: ({ onClose }: { onClose: () => void }) => (
      <div role="dialog">
        Mocked Paywall
        <button onClick={onClose}>Close</button>
      </div>
    ),
  };
});

describe("PremiumGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("shows children directly when premium", () => {
    render(
      <PremiumGate isPremium={true}>
        <div data-testid="content">Premium content</div>
      </PremiumGate>
    );
    expect(screen.getAllByTestId("content")[0]).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("dims and gates content when not premium, opens Paywall on click", () => {
    render(
      <PremiumGate isPremium={false}>
        <div data-testid="content">Gated content</div>
      </PremiumGate>
    );

    expect(screen.getAllByTestId("content")[0]).toBeInTheDocument();

    const unlock = screen.getByRole("button", { name: /continue/i });
    expect(unlock).toHaveAttribute("aria-haspopup", "dialog");
    expect(unlock.className).toContain("min-h-11");
    expect(unlock.className).toContain("bg-[var(--pp-primary)]");
    expect(unlock.className).toContain("text-[var(--color-primary-foreground)]");
    fireEvent.click(unlock);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  test("preview has no aria-label (sr-only copy + inert handle context); telemetry and focus restore on close", async () => {
    render(
      <PremiumGate isPremium={false} source="plate_test">
        <div data-testid="content">Gated content</div>
      </PremiumGate>
    );

    const preview = screen.getByTestId("content").parentElement;
    expect(preview).not.toHaveAttribute("aria-label");

    const unlock = screen.getByRole("button", { name: /continue/i });
    fireEvent.click(unlock);

    expect(gateInteracted).toHaveBeenCalledWith("premium_preview", "click");
    expect(upgradeClicked).toHaveBeenCalledWith("plate_test", "premium_preview_gate");

    fireEvent.click(screen.getByText("Close"));

    expect(paywallDismissed).toHaveBeenCalledWith("plate_test", "close_button");
    await waitFor(() => {
      expect(document.activeElement).toBe(unlock);
    });
  });
});
