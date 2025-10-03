/* @vitest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import PremiumGate from "../PremiumGate";
import "../../test/setup";
import { vi, describe, test, expect } from "vitest";

vi.mock("../Paywall/BeforeAfter", () => {
  return {
    default: ({
      onClose,
      onPurchase,
    }: {
      onClose: () => void;
      source?: string;
      via?: string;
      onPurchase?: () => void;
    }) => (
      <div role="dialog">
        Mocked Paywall
        <button data-testid="paywall-close" onClick={onClose}>
          Close
        </button>
        <button data-testid="paywall-purchase" onClick={onPurchase}>
          Purchase
        </button>
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
    expect(screen.getByTestId("content")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("dims and gates content when not premium, opens Paywall on click", () => {
    render(
      <PremiumGate isPremium={false}>
        <div data-testid="content">Gated content</div>
      </PremiumGate>
    );

    expect(screen.getByTestId("content")).toBeInTheDocument();

    const unlock = screen.getByRole("button", { name: /continue/i });
    fireEvent.click(unlock);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  test("applies accessibility attributes for non-premium preview", () => {
    render(
      <PremiumGate isPremium={false}>
        <div data-testid="content">Gated content</div>
      </PremiumGate>
    );

    const previewWrapper = screen.getByTestId("content").parentElement;
    expect(previewWrapper).not.toBeNull();
    expect(previewWrapper).toHaveAttribute("aria-hidden", "true");

    const description = screen.getByText(/Unlock Premium/i);
    expect(description).toHaveClass("sr-only");

    const button = screen.getByRole("button", { name: /continue/i });
    expect(button).toHaveAttribute("aria-haspopup", "dialog");
    expect(button).toHaveAttribute("aria-describedby", description.id);
  });

  test("toggles paywall visibility and handles purchase callback", () => {
    const onPurchase = vi.fn();

    render(
      <PremiumGate isPremium={false} source="test_source">
        <div data-testid="content">Gated content</div>
      </PremiumGate>
    );

    const continueButton = screen.getByRole("button", { name: /continue/i });
    fireEvent.click(continueButton);

    const paywall = screen.getByRole("dialog");
    expect(paywall).toBeInTheDocument();

    const purchaseButton = screen.getByTestId("paywall-purchase");
    fireEvent.click(purchaseButton);
    expect(onPurchase).not.toHaveBeenCalled();

    const closeButton = screen.getByTestId("paywall-close");
    fireEvent.click(closeButton);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
