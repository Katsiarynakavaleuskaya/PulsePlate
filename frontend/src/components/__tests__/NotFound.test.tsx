/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
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
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(window, 'history', {
      value: originalHistory,
      configurable: true,
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


  it("has working navigation buttons", () => {
    // Spy on window.history.back and mock its implementation
    const mockBack = vi.spyOn(window.history, "back").mockImplementation(() => {
      /* noop */
    });

    // Create a wrapper component to expose the current location
    const LocationWrapper = ({ children }: { children: React.ReactNode }) => {
      const location = useLocation();
      return (
        <>
          <div data-testid="location-pathname">{location.pathname}</div>
          {children}
        </>
      );
    };

    render(
      <MemoryRouter initialEntries={["/some-page"]}>
        <LocationWrapper>
          <NotFound />
        </LocationWrapper>
      </MemoryRouter>
    );

    const goBackButton = screen.getByText("Go Back");
    const goHomeButton = screen.getByText("Go Home");
    const locationElement = screen.getByTestId("location-pathname");

    // Test Go Back button
    fireEvent.click(goBackButton);
    expect(mockBack).toHaveBeenCalled();

    // Test Go Home button navigation
    expect(locationElement).toHaveTextContent("/some-page");
    fireEvent.click(goHomeButton);
    expect(locationElement).toHaveTextContent("/");
  });
});
