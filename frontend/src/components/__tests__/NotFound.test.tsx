/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NotFound from "../NotFound";

// Mock useNavigate globally for all tests
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("NotFound", () => {
  let originalHistory: typeof window.history;
  let originalLocation: typeof window.location;

  beforeEach(() => {
    // Reset mock for each test
    mockNavigate.mockReset();
    // Save originals before any test modifications
    originalHistory = window.history;
    originalLocation = window.location;
  });

  afterEach(() => {
    // Restore originals to prevent state leaks between tests
    window.history = originalHistory;
    window.location = originalLocation;
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
    // Mock window.history.back
    const mockBack = vi.fn();
    delete (window as any).history;
    window.history = { back: mockBack } as any;

    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );

    const goBackButton = screen.getByText("Go Back");
    const goHomeButton = screen.getByText("Go Home");

    fireEvent.click(goBackButton);
    expect(mockBack).toHaveBeenCalled();

    fireEvent.click(goHomeButton);
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });
});
