import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { RequireKey } from "../RequireKey";

vi.mock("../AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../AuthContext";

function EnterKeyProbe() {
  const location = useLocation();
  const fromPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "none";
  return <div data-testid="enter-key-probe">{fromPath}</div>;
}

describe("RequireKey", () => {
  it("redirects to /enter-key and preserves source path when key is missing", () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: false,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/plate"]}>
        <Routes>
          <Route
            path="/plate"
            element={
              <RequireKey>
                <div data-testid="protected-content">protected</div>
              </RequireKey>
            }
          />
          <Route path="/enter-key" element={<EnterKeyProbe />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(screen.getByTestId("enter-key-probe")).toHaveTextContent("/plate");
  });

  it("renders children when key exists", () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: "AAAAAAAAAAAAAAAAAAAAA", // pragma: allowlist secret
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/plate"]}>
        <Routes>
          <Route
            path="/plate"
            element={
              <RequireKey>
                <div data-testid="protected-content">protected</div>
              </RequireKey>
            }
          />
          <Route path="/enter-key" element={<EnterKeyProbe />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    expect(screen.queryByTestId("enter-key-probe")).not.toBeInTheDocument();
  });
});
