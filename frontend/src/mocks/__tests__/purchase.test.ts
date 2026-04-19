import { HttpHandler } from "msw";
import type { RequestHandler } from "msw";
import { expect, test } from "vitest";
import { handlers } from "../handlers";

const LEGACY_RELEASE_PATHS = ["/api/purchase", "/api/restore"] as const;
const HTTP_MATCH_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"] as const;
const LOCAL_RUNTIME_ORIGIN = "http://localhost";

const matchesLegacyReleasePath = async (
  handler: RequestHandler,
  legacyPath: string
): Promise<boolean> => {
  if (!(handler instanceof HttpHandler)) {
    return false;
  }

  // RU: Проверяем реальный runtime matching MSW, чтобы regex/catch-all handlers тоже ловились.
  // EN: Evaluate actual MSW runtime matching so regex/catch-all handlers are also detected.
  for (const method of HTTP_MATCH_METHODS) {
    const request = new Request(`${LOCAL_RUNTIME_ORIGIN}${legacyPath}`, { method });
    const parsedResult = await handler.parse({ request });
    const isMatch: boolean = await handler.predicate({ request, parsedResult });

    if (isMatch) {
      return true;
    }
  }

  return false;
};

test(
  "shared MSW surface does not expose legacy purchase or restore release paths",
  async (): Promise<void> => {
    const exposedLegacyPaths: string[] = [];

    for (const legacyPath of LEGACY_RELEASE_PATHS) {
      const matchResults: boolean[] = await Promise.all(
        handlers.map((handler): Promise<boolean> => matchesLegacyReleasePath(handler, legacyPath))
      );

      if (matchResults.some((isMatch): boolean => isMatch)) {
        exposedLegacyPaths.push(legacyPath);
      }
    }

    expect(exposedLegacyPaths).toEqual([]);
  }
);
