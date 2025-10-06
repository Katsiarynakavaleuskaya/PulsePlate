/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NotFound from "../NotFound";

describe("NotFound", () => {
  it("renders the 404 page with proper content", () => {
    render(<NotFound />);

    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
    expect(screen.getByText(/Sorry, the page you're looking for doesn't exist/)).toBeInTheDocument();
    expect(screen.getByText(/Let's get you back on track with your health journey/)).toBeInTheDocument();
  });

  it("renders action buttons", () => {
    render(<NotFound />);

    expect(screen.getByText("Go Back")).toBeInTheDocument();
    expect(screen.getByText("Go Home")).toBeInTheDocument();
  });

  it("has working navigation buttons", () => {
    // Mock window.history.back
    const mockBack = vi.fn();
    delete (window as any).history;
    window.history = { back: mockBack } as any;

    // Mock window.location.href assignment
    let hrefValue = '';
    delete (window as any).location;
    window.location = { href: '' } as any;
    Object.defineProperty(window.location, 'href', {
      set: (value) => { hrefValue = value; },
      get: () => hrefValue,
    });

    render(<NotFound />);

    const goBackButton = screen.getByText("Go Back");
    const goHomeButton = screen.getByText("Go Home");

    fireEvent.click(goBackButton);
    expect(mockBack).toHaveBeenCalled();

    fireEvent.click(goHomeButton);
    expect(hrefValue).toBe('/');
  });
});
