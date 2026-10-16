import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { createServer as createHttpServer, request, type Server } from "node:http";
import { mkdtemp, rm } from "node:fs/promises";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer, resolveConfig, type ViteDevServer } from "vite";

const root = process.cwd();
const configFile = join(root, "vite.config.ts");
const syntheticHeaderValue = "test";
const received: Array<{
  url: string;
  body: string;
  apiKey: string | string[] | undefined;
  cookie: string | undefined;
}> = [];
let backend: Server | undefined;
let cacheDirectory: string;
const viteServers: ViteDevServer[] = [];

async function closeBackend(): Promise<void> {
  const owned = backend;
  if (!owned) return;
  backend = undefined;
  owned.closeAllConnections();
  await new Promise<void>((resolve, reject) => {
    owned.close((error) => (error ? reject(error) : resolve()));
  });
}

async function startVite(mode: string): Promise<number> {
  const server = await createServer({
    root,
    configFile,
    configLoader: "runner",
    mode,
    cacheDir: join(cacheDirectory, mode),
    appType: "custom",
    logLevel: "silent",
    optimizeDeps: { noDiscovery: true, include: [] },
    server: {
      host: "127.0.0.1",
      port: 0,
      strictPort: true,
      hmr: false,
      watch: null,
      preTransformRequests: false,
    },
  });
  viteServers.push(server);
  const httpServer = server.httpServer;
  if (!httpServer) throw new Error("Missing owned Vite HTTP server");
  // Vite's convenience listen() treats port zero as its default port. Its
  // native HTTP listener retains port-zero allocation and Vite's startup hook.
  await new Promise<void>((resolve, reject) => {
    httpServer.once("error", reject);
    httpServer.listen(0, "127.0.0.1", () => {
      httpServer.removeListener("error", reject);
      resolve();
    });
  });
  const address = httpServer.address();
  if (!address || typeof address === "string") throw new Error("Missing owned Vite listener");
  return (address as AddressInfo).port;
}

async function send(
  port: number,
  path: string,
  body?: string,
): Promise<{
  status: number;
  contentType: string | undefined;
  location: string | undefined;
  body: string;
}> {
  return new Promise((resolve, reject) => {
    const req = request(
      {
        hostname: "127.0.0.1",
        port,
        path,
        method: body === undefined ? "GET" : "POST",
        agent: false,
        headers: {
          "X-API-Key": syntheticHeaderValue,
          Cookie: "rdev_session=synthetic",
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        },
      },
      (response) => {
        let text = "";
        response.setEncoding("utf8");
        response.on("data", (chunk: string) => {
          text += chunk;
        });
        response.on("error", reject);
        response.on("end", () =>
          resolve({
            status: response.statusCode ?? 0,
            contentType: response.headers["content-type"],
            location: response.headers.location,
            body: text,
          }),
        );
      },
    );
    req.setTimeout(3000, () => req.destroy(new Error("Owned HTTP request timed out")));
    req.on("error", reject);
    req.end(body);
  });
}

describe.sequential("remote development native API transport", () => {
  beforeAll(async () => {
    cacheDirectory = await mkdtemp(join(tmpdir(), "pulseplate-rdev-vite-"));
    const owned = createHttpServer((req, res) => {
      let body = "";
      req.setEncoding("utf8");
      req.on("data", (chunk: string) => {
        body += chunk;
      });
      req.on("end", () => {
        received.push({
          url: req.url ?? "",
          body,
          apiKey: req.headers["x-api-key"],
          cookie: req.headers.cookie,
        });
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        if (req.url === "/api/v1/invalid") {
          res.statusCode = 422;
          res.end(
            JSON.stringify({
              detail: [
                {
                  loc: ["body", "weight_kg"],
                  type: "missing",
                  msg: "Field required",
                },
              ],
            }),
          );
        } else if (req.url === "/api/v1/redirect") {
          res.statusCode = 302;
          res.setHeader("Location", "https://example.invalid/rdev-synthetic");
          res.end(JSON.stringify({ redirected: true }));
        } else {
          res.end(JSON.stringify({ source: "owned-synthetic-backend", url: req.url }));
        }
      });
    });
    await new Promise<void>((resolve, reject) => {
      owned.once("error", reject);
      owned.listen(8001, "127.0.0.1", () => {
        owned.removeListener("error", reject);
        backend = owned;
        resolve();
      });
    });
  });

  afterAll(async () => {
    try {
      await Promise.all(viteServers.map((server) => server.close()));
    } finally {
      try {
        await closeBackend();
      } finally {
        if (cacheDirectory) await rm(cacheDirectory, { recursive: true });
      }
    }
  });

  it("preserves canonical path, query, JSON body and synthetic credential headers", async () => {
    const port = await startVite("remote");
    const payload = JSON.stringify({ weight_kg: 70, height_cm: 170 });
    const response = await send(port, "/api/v1/rdev-acceptance?probe=synthetic", payload);
    expect(response.status).toBe(200);
    expect(response.contentType).toMatch(/^application\/json/);
    expect(JSON.parse(response.body)).toEqual({
      source: "owned-synthetic-backend",
      url: "/api/v1/rdev-acceptance?probe=synthetic",
    });
    expect(received[received.length - 1]).toEqual({
      url: "/api/v1/rdev-acceptance?probe=synthetic",
      body: payload,
      apiKey: syntheticHeaderValue,
      cookie: "rdev_session=synthetic",
    });

    const exactRoot = await send(port, "/api/v1?probe=root");
    expect(exactRoot.status).toBe(200);
    expect(exactRoot.contentType).toMatch(/^application\/json/);
    expect(JSON.parse(exactRoot.body).url).toBe("/api/v1?probe=root");

    const invalid = await send(port, "/api/v1/invalid", "{}");
    expect(invalid.status).toBe(422);
    expect(invalid.contentType).toMatch(/^application\/json/);
    expect(JSON.parse(invalid.body)).toEqual({
      detail: [{ loc: ["body", "weight_kg"], type: "missing", msg: "Field required" }],
    });
  });

  it("does not forward neighboring namespaces or non-API paths", async () => {
    const port = await startVite("remote");
    const count = received.length;
    for (const path of ["/api/v10", "/api/v1x", "/api", "/rdev-not-an-api"]) {
      expect((await send(port, path)).status).toBe(404);
    }
    expect(received).toHaveLength(count);
  });

  it("keeps default and test development modes on their original transport", async () => {
    const count = received.length;
    for (const mode of ["development", "test"]) {
      const port = await startVite(mode);
      expect((await send(port, "/api/v1/rdev-acceptance")).status).toBe(404);
    }
    expect(received).toHaveLength(count);
  });

  it("does not inherit the development proxy for build or remote preview", async () => {
    const inline = {
      root,
      configFile,
      configLoader: "runner" as const,
      mode: "remote",
      cacheDir: join(cacheDirectory, "resolved"),
      logLevel: "silent" as const,
    };
    const build = await resolveConfig(inline, "build");
    const preview = await resolveConfig(inline, "serve", "remote", "production", true);
    expect(build.server.proxy).toBeUndefined();
    expect(preview.server.proxy).toBeUndefined();
    expect(preview.preview.proxy).toBeUndefined();
  });

  it("keeps the upstream fixed even when a browser API base names another origin", async () => {
    vi.stubEnv("VITE_API_BASE", "http://127.0.0.1:9/api/v1");
    try {
      const port = await startVite("remote");
      const response = await send(port, "/api/v1/rdev-fixed-upstream");
      expect(response.status).toBe(200);
      expect(response.contentType).toMatch(/^application\/json/);
      expect(JSON.parse(response.body).source).toBe("owned-synthetic-backend");
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("returns backend redirects without following them to an external upstream", async () => {
    const port = await startVite("remote");
    const count = received.length;
    const response = await send(port, "/api/v1/redirect");
    expect(response.status).toBe(302);
    expect(response.location).toBe("https://example.invalid/rdev-synthetic");
    expect(received).toHaveLength(count + 1);
  });

  it("fails with the native gateway error when the fixed upstream is unavailable", async () => {
    const port = await startVite("remote");
    await closeBackend();
    const response = await send(port, "/api/v1/rdev-acceptance");
    expect(response.status).toBe(502);
    expect(response.body).not.toContain("owned-synthetic-backend");
  });
});
