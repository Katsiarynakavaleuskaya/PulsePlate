// MSW setup for testing - using browser version for jsdom
import { setupWorker } from "msw";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);
