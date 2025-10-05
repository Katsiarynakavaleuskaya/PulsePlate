/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../../../auth/AuthContext";
import EnterKey from "../EnterKey";

const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
  dismissAll: vi.fn(),
};

vi.mock("../../../components/ui/useToast", () => ({
  useToast: () => toastMock,
}));

describe("EnterKey", () => {
  const storageKey = "pulseplate.settings.v1";

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("rejects empty values", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <EnterKey />
        </AuthProvider>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText(/Сохранить/i));

    expect(toastMock.error).toHaveBeenCalledWith("Введите непустой API-ключ.");
    expect(window.localStorage.getItem(storageKey)).toBeNull();
  });

  it("saves trimmed key to settings store", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <EnterKey />
        </AuthProvider>
      </MemoryRouter>
    );

    const input = screen.getByPlaceholderText(/X-API-Key/i);
    fireEvent.change(input, { target: { value: "  secret-key  " } });
    fireEvent.click(screen.getByText(/Сохранить/i));

    expect(toastMock.success).toHaveBeenCalledWith("Ключ сохранён.");

    const stored = window.localStorage.getItem(storageKey);
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored as string)).toEqual({ apiKey: "secret-key" });
  });

  it("clears key when requested", () => {
    window.localStorage.setItem(storageKey, JSON.stringify({ apiKey: "existing" }));

    render(
      <MemoryRouter>
        <AuthProvider>
          <EnterKey />
        </AuthProvider>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText(/Очистить/i));

    expect(toastMock.success).toHaveBeenCalledWith("Ключ удалён.");
    expect(window.localStorage.getItem(storageKey)).toEqual("{}");
  });
});
