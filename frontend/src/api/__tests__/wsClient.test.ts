import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildRealtimeWsUrl,
  connectRealtimeWs,
  type RealtimeWsEnvelope,
  type WsConnectionState,
} from "../wsClient";
import { setApiClientDependencies } from "../client";

describe("wsClient", () => {
  afterEach(() => {
    setApiClientDependencies(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("buildRealtimeWsUrl converts https API base to wss", () => {
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => undefined,
      apiBase: "https://api.example.com/api/v1",
    });

    expect(buildRealtimeWsUrl("/ws")).toBe("wss://api.example.com/ws");
  });

  it("buildRealtimeWsUrl appends token in query string", () => {
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => undefined,
      apiBase: "http://localhost:8000/api/v1",
    });

    expect(buildRealtimeWsUrl("/ws", "abc123")).toBe("ws://localhost:8000/ws?token=abc123");
  });

  it("connectRealtimeWs emits state transitions and parses messages", () => {
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => undefined,
      apiBase: "http://localhost:8000/api/v1",
    });

    const states: WsConnectionState[] = [];
    const messages: RealtimeWsEnvelope[] = [];

    const fakeSocket = {
      onopen: null as (() => void) | null,
      onclose: null as (() => void) | null,
      onerror: null as (() => void) | null,
      onmessage: null as ((event: { data: string }) => void) | null,
    };

    const wsCtor = vi.fn(() => fakeSocket);
    vi.stubGlobal("WebSocket", wsCtor as unknown as typeof WebSocket);

    connectRealtimeWs({
      onStateChange: (state) => states.push(state),
      onMessage: (event) => messages.push(event),
    });

    expect(states).toEqual(["connecting"]);
    expect(wsCtor).toHaveBeenCalledWith("ws://localhost:8000/ws");

    fakeSocket.onopen?.();
    fakeSocket.onmessage?.({ data: '{"version":"1","type":"pong"}' });
    fakeSocket.onclose?.();

    expect(states).toEqual(["connecting", "open", "closed"]);
    expect(messages).toEqual([{ version: "1", type: "pong" }]);
  });

  it("connectRealtimeWs emits error state for invalid JSON message", () => {
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => undefined,
      apiBase: "http://localhost:8000/api/v1",
    });

    const states: WsConnectionState[] = [];
    const fakeSocket = {
      onopen: null as (() => void) | null,
      onclose: null as (() => void) | null,
      onerror: null as (() => void) | null,
      onmessage: null as ((event: { data: string }) => void) | null,
    };

    vi.stubGlobal("WebSocket", vi.fn(() => fakeSocket) as unknown as typeof WebSocket);

    connectRealtimeWs({
      onStateChange: (state) => states.push(state),
    });
    fakeSocket.onmessage?.({ data: "not-json" });

    expect(states).toEqual(["connecting", "error"]);
  });
});
