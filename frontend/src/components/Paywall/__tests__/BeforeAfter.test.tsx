/* @vitest-environment jsdom */
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { vi, describe, test, expect, afterEach } from "vitest";
import BeforeAfter from "../BeforeAfter";

// Initialize i18n so t() returns strings
import "../../../i18n";

// Mock analytics to verify calls
vi.mock("../../../lib/analytics", () => {
  return {
    log: vi.fn(),
    Events: {
      PAYWALL_VIEW: "paywall_view",
      PURCHASE_ATTEMPT: "purchase_attempt",
      PURCHASE_CANCEL: "purchase_cancel",
      PURCHASE_SUCCESS: "purchase_success",
      RESTORE_SUCCESS: "restore_success",
    },
  };
});

import { log, Events } from "../../../lib/analytics";

afterEach(() => {
  cleanup();
});

describe("Paywall BeforeAfter", () => {
  test("renders dialog and logs view", () => {
    render(<BeforeAfter onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW);
  });

import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { vi, describe, test, expect, afterEach } from "vitest";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("fires purchase_attempt on CTA click", () => {
  const onPurchase = vi.fn();
  render(<BeforeAfter onClose={() => {}} onPurchase={onPurchase} />);

  fireEvent.click(screen.getByTestId("paywall-cta"));
  expect(onPurchase).toHaveBeenCalled();
  expect(log).toHaveBeenCalledTimes(1);
  expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW);
  expect(log).not.toHaveBeenCalledWith(Events.PURCHASE_ATTEMPT);
});

test("fires purchase_cancel on Cancel click", () => {
  const onClose = vi.fn();
  render(<BeforeAfter onClose={onClose} />);

  fireEvent.click(screen.getByTestId("paywall-cancel"));
  expect(onClose).toHaveBeenCalled();
  expect(log).toHaveBeenCalledTimes(1);
  expect(log).toHaveBeenCalledWith(Events.PAYWALL_VIEW);
  expect(log).not.toHaveBeenCalledWith(Events.PURCHASE_CANCEL);
});
});
