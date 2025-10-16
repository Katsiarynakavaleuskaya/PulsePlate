/**
 * Session Manager for Telemetry
 *
 * Provides stable session tracking with secure storage and TTL management.
 * Sessions are regenerated on expiry, sign-out, or app restart.
 */

import { isAnalyticsEnabled } from '../config/features';

const SESSION_KEY = 'pp_telemetry_session';
const SESSION_TTL = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
const SESSION_ID_LENGTH = 16;

interface SessionData {
  sessionId: string;
  createdAt: number;
  expiresAt: number;
}

/**
 * Generate a cryptographically secure session ID
 */
function generateSessionId(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';

  // Use crypto.getRandomValues for secure random generation
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const array = new Uint8Array(SESSION_ID_LENGTH);
    crypto.getRandomValues(array);
    result = Array.from(array, byte => chars[byte % chars.length]).join('');
  } else {
    // Fallback for environments without crypto.getRandomValues
    for (let i = 0; i < SESSION_ID_LENGTH; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
  }

  return result;
}

/**
 * Get current session ID, creating a new one if needed or expired
 */
export function getSessionId(): string {
  if (!isAnalyticsEnabled()) {
    return 'disabled';
  }

  try {
    const stored = localStorage.getItem(SESSION_KEY);
    if (!stored) {
      return createNewSession();
    }

    const sessionData: SessionData = JSON.parse(stored);
    const now = Date.now();

    // Check if session has expired
    if (now > sessionData.expiresAt) {
      return createNewSession();
    }

    return sessionData.sessionId;
  } catch (error) {
    // If there's any error reading/parsing, create a new session
    console.warn('[Telemetry] Failed to read session data, creating new session:', error);
    return createNewSession();
  }
}

/**
 * Create a new session and store it
 */
function createNewSession(): string {
  const now = Date.now();
  const sessionId = generateSessionId();

  const sessionData: SessionData = {
    sessionId,
    createdAt: now,
    expiresAt: now + SESSION_TTL,
  };

  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));
  } catch (error) {
    console.warn('[Telemetry] Failed to store session data:', error);
  }

  return sessionId;
}

/**
 * Refresh the current session (extend TTL)
 */
export function refreshSession(): string {
  if (!isAnalyticsEnabled()) {
    return 'disabled';
  }

  try {
    const stored = localStorage.getItem(SESSION_KEY);
    if (!stored) {
      return createNewSession();
    }

    const sessionData: SessionData = JSON.parse(stored);
    const now = Date.now();

    // Only refresh if session is still valid
    if (now <= sessionData.expiresAt) {
      sessionData.expiresAt = now + SESSION_TTL;
      localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));
      return sessionData.sessionId;
    } else {
      return createNewSession();
    }
  } catch (error) {
    console.warn('[Telemetry] Failed to refresh session:', error);
    return createNewSession();
  }
}

/**
 * Clear the current session (on sign-out or privacy request)
 */
export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch (error) {
    console.warn('[Telemetry] Failed to clear session:', error);
  }
}

/**
 * Get session metadata for debugging
 */
export function getSessionInfo(): { sessionId: string; isExpired: boolean; timeRemaining: number } {
  if (!isAnalyticsEnabled()) {
    return { sessionId: 'disabled', isExpired: false, timeRemaining: 0 };
  }

  try {
    const stored = localStorage.getItem(SESSION_KEY);
    if (!stored) {
      return { sessionId: 'none', isExpired: true, timeRemaining: 0 };
    }

    const sessionData: SessionData = JSON.parse(stored);
    const now = Date.now();
    const isExpired = now > sessionData.expiresAt;
    const timeRemaining = Math.max(0, sessionData.expiresAt - now);

    return {
      sessionId: sessionData.sessionId,
      isExpired,
      timeRemaining,
    };
  } catch (error) {
    console.warn('[Telemetry] Failed to get session info:', error);
    return { sessionId: 'error', isExpired: true, timeRemaining: 0 };
  }
}
