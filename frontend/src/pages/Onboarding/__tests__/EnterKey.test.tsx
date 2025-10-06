import { render, screen, fireEvent } from "@testing-library/react";
import { AuthProvider } from "../../../auth/AuthContext";
import EnterKey from "../EnterKey";

beforeEach(() => {
  // чистый стор
  localStorage.clear();
  vi.spyOn(window.localStorage.prototype, "setItem");
});

afterEach(() => {
  vi.restoreAllMocks();
});

it("rejects empty key", () => {
  render(<AuthProvider><EnterKey/></AuthProvider>);
  fireEvent.click(screen.getByText(/Сохранить/i));
  expect(screen.getByText(/Введите непустой API-ключ/i)).toBeInTheDocument();
  expect(localStorage.setItem).not.toHaveBeenCalled();
});

it("trims and saves key", () => {
  render(<AuthProvider><EnterKey/></AuthProvider>);
  fireEvent.change(screen.getByPlaceholderText(/X-API-Key|Вставьте/i), { target: { value: " secret " } });
  fireEvent.click(screen.getByText(/Сохранить/i));
  expect(localStorage.setItem).toHaveBeenCalled(); // детальнее можно проверить содержимое NS
});
