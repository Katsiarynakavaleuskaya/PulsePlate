export function createWebSocketConnection(url: string): WebSocket {
  return new WebSocket(url);
}
import { getApiBase } from "./client";

export type WsConnectionState = "connecting" | "open" | "closed" | "error";

export interface RealtimeWsEnvelope {
  version: "1";
  type: string;
  [key: string]: unknown;
}

export interface RealtimeWsConnectOptions {
  path?: string;
  token?: string;
  onMessage?: (event: RealtimeWsEnvelope) => void;
  onStateChange?: (state: WsConnectionState) => void;
}

const DEFAULT_WS_PATH = "/ws";

function toWsBaseUrl(apiBase: string): string {
  const parsed = new URL(apiBase);
  const protocol = parsed.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${parsed.host}`;
}

export function buildRealtimeWsUrl(path: string = DEFAULT_WS_PATH, token?: string): string {
  const wsBase = toWsBaseUrl(getApiBase());
  const url = new URL(path, wsBase);
  if (token) {
    url.searchParams.set("token", token);
  }
  return url.toString();
}

function isRealtimeWsEnvelope(value: unknown): value is RealtimeWsEnvelope {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const maybeEnvelope = value as { version?: unknown; type?: unknown };
  return maybeEnvelope.version === "1" && typeof maybeEnvelope.type === "string";
}

export function connectRealtimeWs(options: RealtimeWsConnectOptions = {}): WebSocket {
  const url = buildRealtimeWsUrl(options.path ?? DEFAULT_WS_PATH, options.token);
  const socket = new WebSocket(url);

  options.onStateChange?.("connecting");

  socket.onopen = (): void => {
    options.onStateChange?.("open");
  };

  socket.onclose = (): void => {
    options.onStateChange?.("closed");
  };

  socket.onerror = (): void => {
    options.onStateChange?.("error");
  };

  socket.onmessage = (event: MessageEvent<string>): void => {
    try {
      const parsed: unknown = JSON.parse(event.data);
      if (!isRealtimeWsEnvelope(parsed)) {
        options.onStateChange?.("error");
        return;
      }
      options.onMessage?.(parsed);
    } catch {
      options.onStateChange?.("error");
    }
  };

  return socket;
}
