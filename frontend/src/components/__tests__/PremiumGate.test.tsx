/* @vitest-environment jsdom */
import { render, screen, fireEvent } from "@testing-library/react";
import PremiumGate from "../PremiumGate";
// Initialize i18n so t() resolves labels
import "../../i18n";
// Import test setup for jest-dom matchers
import "../../test/setup";
import { vi, describe, test, expect } from "vitest";

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
    expect(unlock.className).toContain("bg-[var(--color-primary)]");
    expect(unlock.className).toContain("text-[var(--color-primary-foreground)]");
    fireEvent.click(unlock);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
