import { useEffect, useMemo, useState } from 'react';
import { createWebSocketConnection } from '../../api/wsClient';

export type HppLiveStatus = 'live' | 'static';
export type HppLiveVariant = 'compact' | 'emphasized';

interface UseHppLiveIndicatorResult {
  status: HppLiveStatus;
  lastEventAt: number | null;
  variant: HppLiveVariant;
}

const getConfiguredWsUrl = (): string | null => {
  const value = ((import.meta as { env?: Record<string, string | undefined> }).env?.VITE_HPP_LIVE_WS_URL ?? '').trim();
  return value.length > 0 ? value : null;
};

const HPP_USER_ID_STORAGE_KEY = 'pp_user_id';

const getStoredUserId = (): string | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return localStorage.getItem(HPP_USER_ID_STORAGE_KEY) || sessionStorage.getItem(HPP_USER_ID_STORAGE_KEY);
  } catch {
    return null;
  }
};

export function assignHppLiveVariant(userId: string | null | undefined): HppLiveVariant {
  if (!userId) {
    return 'compact';
  }

  // Deterministic hash for stable user-to-variant assignment.
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = (hash * 31 + userId.charCodeAt(i)) >>> 0;
  }

  return hash % 2 === 0 ? 'compact' : 'emphasized';
}

export function useHppLiveIndicator(
  overrideWsUrl?: string | null,
  overrideUserId?: string | null
): UseHppLiveIndicatorResult {
  const [status, setStatus] = useState<HppLiveStatus>('static');
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);

  const wsUrl = useMemo(() => {
    if (typeof overrideWsUrl === 'string') {
      return overrideWsUrl.trim().length > 0 ? overrideWsUrl.trim() : null;
    }
    return overrideWsUrl === null ? null : getConfiguredWsUrl();
  }, [overrideWsUrl]);

  const variant = useMemo((): HppLiveVariant => {
    const userId = overrideUserId !== undefined ? overrideUserId : getStoredUserId();
    return assignHppLiveVariant(userId);
  }, [overrideUserId]);

  useEffect(() => {
    if (!wsUrl || typeof WebSocket === 'undefined') {
      setStatus('static');
      setLastEventAt(null);
      return;
    }

    const socket = createWebSocketConnection(wsUrl);

    const markLive = () => {
      setStatus('live');
      setLastEventAt(Date.now());
    };

    const markStatic = () => {
      setStatus('static');
    };

    socket.addEventListener('open', markLive);
    socket.addEventListener('message', markLive);
    socket.addEventListener('error', markStatic);
    socket.addEventListener('close', markStatic);

    return () => {
      socket.removeEventListener('open', markLive);
      socket.removeEventListener('message', markLive);
      socket.removeEventListener('error', markStatic);
      socket.removeEventListener('close', markStatic);
      socket.close();
    };
  }, [wsUrl]);

  return { status, lastEventAt, variant };
}
