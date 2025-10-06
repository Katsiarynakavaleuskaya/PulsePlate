import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import toast from "react-hot-toast";
import { AuthProvider } from "../../../auth/AuthContext";
import EnterKey from "../EnterKey";
import { SettingsStore } from "../../../settings/index";

let setItemSpy: ReturnType<typeof vi.spyOn>;

// Mock useNavigate globally to prevent errors in tests that don't explicitly mock it
const mockNavigate = vi.fn();
let mockLocationState: any = null;

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: mockLocationState }),
  };
});

beforeEach(() => {
  // чистый стор
  localStorage.clear();
  mockLocationState = null;
  mockNavigate.mockClear();
  setItemSpy = vi.spyOn(window.localStorage.__proto__, 'setItem');
});

afterEach(() => {
  vi.restoreAllMocks();
});

it("rejects empty key", () => {
  const toastErrorSpy = vi.spyOn(toast, "error").mockReturnValue("");

  render(<AuthProvider><EnterKey/></AuthProvider>);
  fireEvent.click(screen.getByText(/Сохранить/i));
  expect(toastErrorSpy).toHaveBeenCalledWith("Введите непустой API-ключ.");
  expect(setItemSpy).not.toHaveBeenCalled();

  toastErrorSpy.mockRestore();
});

it("trims and saves key", () => {
  render(<AuthProvider><EnterKey/></AuthProvider>);
  fireEvent.change(screen.getByPlaceholderText(/X-API-Key|Вставьте/i), { target: { value: " secret " } });
  fireEvent.click(screen.getByText(/Сохранить/i));
  expect(setItemSpy).toHaveBeenCalled(); // детальнее можно проверить содержимое NS
});

it("clears input and removes key on clear button click", () => {
  // Pre-populate with an API key
  localStorage.setItem("pulseplate.settings.v1", JSON.stringify({ apiKey: "test-key" }));

  render(<AuthProvider><EnterKey/></AuthProvider>);

  const input = screen.getByPlaceholderText(/X-API-Key|Вставьте/i);
  const clearButton = screen.getByText(/Очистить/i);

  // Initially should show the existing key
  expect(input).toHaveValue("test-key");

  // Click clear button
  fireEvent.click(clearButton);

  // Input should be emptied
  expect(input).toHaveValue("");

  // localStorage.setItem should have been called to remove the key
  expect(setItemSpy).toHaveBeenCalledWith("pulseplate.settings.v1", JSON.stringify({}));
});

it("navigates to from route after saving valid key", () => {
  // Clear previous calls
  mockNavigate.mockClear();
  mockLocationState = { from: "/some-route" };

  render(
    <MemoryRouter initialEntries={[{ pathname: "/enter-key", state: { from: "/some-route" } }]}>
      <AuthProvider>
        <EnterKey />
      </AuthProvider>
    </MemoryRouter>
  );

  const input = screen.getByPlaceholderText(/X-API-Key|Вставьте/i);
  const saveButton = screen.getByText(/Сохранить/i);

  // Enter a valid key
  fireEvent.change(input, { target: { value: "valid-api-key" } });

  // Click save
  fireEvent.click(saveButton);

  // Should navigate to the from route with replace: true
  expect(mockNavigate).toHaveBeenCalledWith("/some-route", { replace: true });
});

it("displays existing apiKey in input on initial render", () => {
  // Pre-populate with an API key with whitespace that should be trimmed in display
  localStorage.setItem("pulseplate.settings.v1", JSON.stringify({ apiKey: "  existing-key  " }));

  render(<AuthProvider><EnterKey/></AuthProvider>);

  const input = screen.getByPlaceholderText(/X-API-Key|Вставьте/i);

  // Should display the existing key (trimmed)
  expect(input).toHaveValue("existing-key");
});

it("displays error message when save fails", () => {
  // Mock SettingsStore.setApiKey to throw an error
  const originalSetApiKey = SettingsStore.setApiKey;
  SettingsStore.setApiKey = vi.fn(() => {
    throw new Error("Storage quota exceeded");
  });

  // Mock toast.error
  const toastErrorSpy = vi.spyOn(toast, "error").mockReturnValue("");

  render(<AuthProvider><EnterKey/></AuthProvider>);

  const input = screen.getByPlaceholderText(/X-API-Key|Вставьте/i);
  const saveButton = screen.getByText(/Сохранить/i);

  // Enter a valid key
  fireEvent.change(input, { target: { value: "valid-api-key" } });

  // Click save
  fireEvent.click(saveButton);

  // Should display error message
  expect(toastErrorSpy).toHaveBeenCalledWith("Не удалось сохранить ключ. Попробуйте ещё раз.");

  // Restore mocks
  SettingsStore.setApiKey = originalSetApiKey;
  toastErrorSpy.mockRestore();
});
