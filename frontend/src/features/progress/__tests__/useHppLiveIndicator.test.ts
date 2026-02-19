import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useHppLiveIndicator } from '../useHppLiveIndicator';

type Listener = (event?: Event) => void;

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  private listeners = new Map<string, Set<Listener>>();

  constructor(public readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  addEventListener(type: string, callback: Listener): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)?.add(callback);
  }

  removeEventListener(type: string, callback: Listener): void {
    this.listeners.get(type)?.delete(callback);
  }

  close(): void {
    this.emit('close');
  }

  emit(type: string): void {
    this.listeners.get(type)?.forEach((listener) => listener(new Event(type)));
  }
}

describe('useHppLiveIndicator', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    MockWebSocket.instances = [];
  });

  it('uses static status when ws url is missing', () => {
    const { result } = renderHook(() => useHppLiveIndicator(null));

    expect(result.current.status).toBe('static');
    expect(result.current.lastEventAt).toBeNull();
  });

  it('switches to live status on open and message', () => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);

    const { result } = renderHook(() => useHppLiveIndicator('ws://localhost/live'));
    const instance = MockWebSocket.instances[0];

    expect(instance).toBeDefined();
    expect(result.current.status).toBe('static');

    act(() => {
      instance.emit('open');
    });

    expect(result.current.status).toBe('live');
    expect(result.current.lastEventAt).toBeTypeOf('number');

    const firstTimestamp = result.current.lastEventAt;

    act(() => {
      instance.emit('message');
    });

    expect(result.current.status).toBe('live');
    expect(result.current.lastEventAt).not.toBeNull();
    expect(result.current.lastEventAt).toBeGreaterThanOrEqual(firstTimestamp ?? 0);
  });

  it('returns to static status after close', () => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);

    const { result } = renderHook(() => useHppLiveIndicator('ws://localhost/live'));
    const instance = MockWebSocket.instances[0];

    act(() => {
      instance.emit('open');
    });

    expect(result.current.status).toBe('live');

    act(() => {
      instance.emit('close');
    });

    expect(result.current.status).toBe('static');
  });
});
