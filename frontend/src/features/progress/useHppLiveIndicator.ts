import { useEffect, useMemo, useState } from 'react';

export type HppLiveStatus = 'live' | 'static';

interface UseHppLiveIndicatorResult {
  status: HppLiveStatus;
  lastEventAt: number | null;
}

const getConfiguredWsUrl = (): string | null => {
  const value = ((import.meta as { env?: Record<string, string | undefined> }).env?.VITE_HPP_LIVE_WS_URL ?? '').trim();
  return value.length > 0 ? value : null;
};

export function useHppLiveIndicator(overrideWsUrl?: string | null): UseHppLiveIndicatorResult {
  const [status, setStatus] = useState<HppLiveStatus>('static');
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);

  const wsUrl = useMemo(() => {
    if (typeof overrideWsUrl === 'string') {
      return overrideWsUrl.trim().length > 0 ? overrideWsUrl.trim() : null;
    }
    return overrideWsUrl === null ? null : getConfiguredWsUrl();
  }, [overrideWsUrl]);

  useEffect(() => {
    if (!wsUrl || typeof WebSocket === 'undefined') {
      setStatus('static');
      setLastEventAt(null);
      return;
    }

    const socket = new WebSocket(wsUrl);

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

  return { status, lastEventAt };
}
