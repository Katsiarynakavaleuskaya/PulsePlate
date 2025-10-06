import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import toast from "react-hot-toast";
import { AuthProvider } from "../../../auth/AuthContext";
import EnterKey from "../EnterKey";
import { SettingsStore } from "../../../settings/index";

// Use a fake API key constant to avoid triggering security scanners
const TEST_API_KEY = "sk-fake_key_12345678901234567890";

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
  // Clean store
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
  fireEvent.click(screen.getByText(/Save/i));
  expect(toastErrorSpy).toHaveBeenCalledWith("Invalid or missing API key.");
  expect(setItemSpy).not.toHaveBeenCalled();

  toastErrorSpy.mockRestore();
});

it("rejects invalid API key format", () => {
  const toastErrorSpy = vi.spyOn(toast, "error").mockReturnValue("");

  render(<AuthProvider><EnterKey/></AuthProvider>);
  fireEvent.change(screen.getByPlaceholderText(/Paste X-API-Key/i), { target: { value: "invalid-key" } });
  fireEvent.click(screen.getByText(/Save/i));

  expect(toastErrorSpy).toHaveBeenCalledWith("Invalid API key format. Key must start with 'sk-', be at least 20 characters long, and no longer than 256 characters.");
  expect(setItemSpy).not.toHaveBeenCalled();

  toastErrorSpy.mockRestore();
});

it("trims and saves key", () => {
it("trims and saves key", () => {
  const sessionSetSpy = vi.spyOn(window.sessionStorage.__proto__, 'setItem');
  render(<AuthProvider><EnterKey/></AuthProvider>);
  fireEvent.change(
    screen.getByPlaceholderText(/Paste X-API-Key/i),
    { target: { value: ` ${TEST_API_KEY} ` } }
  );
  fireEvent.click(screen.getByText(/Save/i));
  expect(sessionSetSpy).toHaveBeenCalledWith(
    "pulseplate.settings.v1.apiKey",
    TEST_API_KEY
  );
});

it("clears input and removes key on clear button click", () => {
  // Pre-populate with an API key
  localStorage.setItem("pulseplate.settings.v1", JSON.stringify({ apiKey: TEST_API_KEY }));

  render(<AuthProvider><EnterKey/></AuthProvider>);

  const input = screen.getByPlaceholderText(/Paste X-API-Key/i);
  const clearButton = screen.getByText(/Clear/i);

  // Initially should show the existing key
  expect(input).toHaveValue(TEST_API_KEY);

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

  const input = screen.getByPlaceholderText(/Paste X-API-Key/i);
  const saveButton = screen.getByText(/Save/i);

  // Enter a valid key
  fireEvent.change(input, { target: { value: TEST_API_KEY } });

  // Click save
  fireEvent.click(saveButton);

  // Should navigate to the from route with replace: true
  expect(mockNavigate).toHaveBeenCalledWith("/some-route", { replace: true });
});

it("displays existing apiKey in input on initial render", () => {
  // Pre-populate with an API key with whitespace that should be trimmed in display
  localStorage.setItem("pulseplate.settings.v1", JSON.stringify({ apiKey: "  sk-existing12345678901234567890  " }));

  render(<AuthProvider><EnterKey/></AuthProvider>);

  const input = screen.getByPlaceholderText(/Paste X-API-Key/i);

  // Should display the existing key (trimmed)
  expect(input).toHaveValue("sk-existing12345678901234567890");
});

it("displays error message when save fails", () => {
  // Mock SettingsStore.setApiKey to throw an error
  const setApiKeySpy = vi.spyOn(SettingsStore, "setApiKey").mockImplementation(() => {
    throw new Error("Storage quota exceeded");
  });

  // Mock toast.error
  const toastErrorSpy = vi.spyOn(toast, "error").mockReturnValue("");

  render(<AuthProvider><EnterKey/></AuthProvider>);

  const input = screen.getByPlaceholderText(/Paste X-API-Key/i);
  const saveButton = screen.getByText(/Save/i);

  // Enter a valid key
  fireEvent.change(input, { target: { value: TEST_API_KEY } });

  // Click save
  fireEvent.click(saveButton);

  // Should display error message
  expect(toastErrorSpy).toHaveBeenCalledWith("Failed to save key. try again.");

  // Restore mocks
  setApiKeySpy.mockRestore();
  toastErrorSpy.mockRestore();
});
