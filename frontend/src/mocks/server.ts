// MSW setup for testing - using server version for jsdom
import { setupServer } from "msw";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
