// RU: Расширяем expect матчерами jest-dom для RTL.
// EN: Extend expect with jest-dom matchers for RTL.
import "@testing-library/jest-dom";
import { expect, vi, describe, it } from "vitest";
import { server } from "./mocks/server";

// Поднимаем MSW до тестов
beforeAll(() => {
  server.listen({
    onUnhandledRequest: "bypass",
  });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
