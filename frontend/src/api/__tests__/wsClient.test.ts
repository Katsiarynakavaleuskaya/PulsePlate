import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildRealtimeWsUrl,
  connectRealtimeWs,
  type RealtimeWsEnvelope,
  type WsConnectionState,
} from "../wsClient";
import { setApiClientDependencies, type ApiClientDependencies } from "../client";

type MockWebSocketHandlers = {
  onopen: (() => void) | null;
  onclose: (() => void) | null;
  onerror: ((event: Event) => void) | null;
  onmessage: ((event: { data: string }) => void) | null;
};

describe("wsClient", (): void => {
  afterEach((): void => {
    setApiClientDependencies(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("buildRealtimeWsUrl converts https API base to wss", (): void => {
    const deps: ApiClientDependencies = {
      getStoredApiKey: (): string | null => null,
      clearStoredApiKey: (): void => undefined,
      apiBase: "https://api.example.com/api/v1",
    };
    setApiClientDependencies(deps);

    expect(buildRealtimeWsUrl("/api/v1/pro/ws")).toBe("wss://api.example.com/api/v1/pro/ws");
  });

  it("buildRealtimeWsUrl appends token in query string", (): void => {
    const deps: ApiClientDependencies = {
      getStoredApiKey: (): string | null => null,
      clearStoredApiKey: (): void => undefined,
      apiBase: "http://localhost:8000/api/v1",
    };
    setApiClientDependencies(deps);

    expect(buildRealtimeWsUrl("/api/v1/pro/ws", "abc123")).toBe("ws://localhost:8000/api/v1/pro/ws?token=abc123");
  });

  it("connectRealtimeWs emits state transitions and parses messages", (): void => {
    const deps: ApiClientDependencies = {
      getStoredApiKey: (): string | null => null,
      clearStoredApiKey: (): void => undefined,
      apiBase: "http://localhost:8000/api/v1",
    };
    setApiClientDependencies(deps);

    const states: WsConnectionState[] = [];
    const messages: RealtimeWsEnvelope[] = [];

    const fakeSocket: MockWebSocketHandlers = {
      onopen: null as (() => void) | null,
      onclose: null as (() => void) | null,
      onerror: null as ((event: Event) => void) | null,
      onmessage: null as ((event: { data: string }) => void) | null,
    };

    const wsCtor = vi.fn((_: string): MockWebSocketHandlers => fakeSocket);
    vi.stubGlobal("WebSocket", wsCtor as unknown as typeof WebSocket);

    connectRealtimeWs({
      onStateChange: (state: WsConnectionState): void => states.push(state),
      onMessage: (event: RealtimeWsEnvelope): void => messages.push(event),
    });

    expect(states).toEqual(["connecting"]);
    expect(wsCtor).toHaveBeenCalledWith("ws://localhost:8000/api/v1/pro/ws");

    fakeSocket.onopen?.();
    fakeSocket.onmessage?.({ data: '{"version":"1","type":"pong"}' });
    fakeSocket.onclose?.();

    expect(states).toEqual(["connecting", "open", "closed"]);
    expect(messages).toEqual([{ version: "1", type: "pong" }]);
  });

  it("connectRealtimeWs emits error state for invalid JSON message", (): void => {
    const deps: ApiClientDependencies = {
      getStoredApiKey: (): string | null => null,
      clearStoredApiKey: (): void => undefined,
      apiBase: "http://localhost:8000/api/v1",
    };
    setApiClientDependencies(deps);

    const states: WsConnectionState[] = [];
    const fakeSocket: MockWebSocketHandlers = {
      onopen: null as (() => void) | null,
      onclose: null as (() => void) | null,
      onerror: null as ((event: Event) => void) | null,
      onmessage: null as ((event: { data: string }) => void) | null,
    };

    vi.stubGlobal(
      "WebSocket",
      vi.fn((_: string): MockWebSocketHandlers => fakeSocket) as unknown as typeof WebSocket,
    );

    connectRealtimeWs({
      onStateChange: (state: WsConnectionState): void => states.push(state),
    });
    fakeSocket.onmessage?.({ data: "not-json" });

    expect(states).toEqual(["connecting", "error"]);
  });

  it("connectRealtimeWs emits error state for invalid envelope shape", (): void => {
    const deps: ApiClientDependencies = {
      getStoredApiKey: (): string | null => null,
      clearStoredApiKey: (): void => undefined,
      apiBase: "http://localhost:8000/api/v1",
    };
    setApiClientDependencies(deps);

    const states: WsConnectionState[] = [];
    const fakeSocket: MockWebSocketHandlers = {
      onopen: null as (() => void) | null,
      onclose: null as (() => void) | null,
      onerror: null as ((event: Event) => void) | null,
      onmessage: null as ((event: { data: string }) => void) | null,
    };

    vi.stubGlobal(
      "WebSocket",
      vi.fn((_: string): MockWebSocketHandlers => fakeSocket) as unknown as typeof WebSocket,
    );

    connectRealtimeWs({
      onStateChange: (state: WsConnectionState): void => states.push(state),
    });
    fakeSocket.onmessage?.({ data: '{"type":"pong"}' });

    expect(states).toEqual(["connecting", "error"]);
  });
});
