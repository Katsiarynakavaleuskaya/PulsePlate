import { getApiBase } from "./client";

export type WsConnectionState = "connecting" | "open" | "closing" | "closed" | "error";

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

export function connectRealtimeWs(options: RealtimeWsConnectOptions = {}): WebSocket {
  const url = buildRealtimeWsUrl(options.path ?? DEFAULT_WS_PATH, options.token);
  const socket = new WebSocket(url);

  options.onStateChange?.("connecting");

  socket.onopen = () => {
    options.onStateChange?.("open");
  };

  socket.onclose = () => {
    options.onStateChange?.("closed");
  };

  socket.onerror = () => {
    options.onStateChange?.("error");
  };

  socket.onmessage = (event: MessageEvent<string>) => {
    try {
      const parsed = JSON.parse(event.data) as RealtimeWsEnvelope;
      options.onMessage?.(parsed);
    } catch {
      options.onStateChange?.("error");
    }
  };

  return socket;
}
