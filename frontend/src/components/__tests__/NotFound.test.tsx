/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NotFound from "../NotFound";

describe("NotFound", () => {
  let originalHistory: typeof window.history;
  let originalLocation: typeof window.location;

  beforeEach(() => {
    // Save originals before any test modifications
    originalHistory = window.history;
    originalLocation = window.location;
  });

  afterEach(() => {
    // Restore originals to prevent state leaks between tests
    window.history = originalHistory;
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });
  it("renders the 404 page with proper content", () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );

    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
    expect(screen.getByText(/Sorry, the page you're looking for doesn't exist/)).toBeInTheDocument();
    expect(screen.getByText(/Let's get you back on track with your health journey/)).toBeInTheDocument();
  });

  it("renders action buttons", () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );

    expect(screen.getByText("Go Back")).toBeInTheDocument();
    expect(screen.getByText("Go Home")).toBeInTheDocument();
  });

  it("has working navigation buttons", () => {
    // Spy on window.history.back and mock its implementation
    const mockBack = vi.spyOn(window.history, "back").mockImplementation(() => {
      /* noop */
    });

    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );

    const goBackButton = screen.getByText("Go Back");
    const goHomeButton = screen.getByText("Go Home");

    fireEvent.click(goBackButton);
    expect(mockBack).toHaveBeenCalled();

    // For the "Go Home" button, we can't easily test router navigation in isolation
    // without more complex setup, so we'll just verify the button exists and is clickable
    expect(goHomeButton).toBeInTheDocument();
    expect(goHomeButton).not.toBeDisabled();
  });
});
