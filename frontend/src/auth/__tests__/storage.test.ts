// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { clearStoredApiKey, getStoredApiKey, setStoredApiKey } from '../storage';

const LEGACY_STORAGE_KEY = 'pulseplate_api_key';

type StorageMock = {
  getItem: ReturnType<typeof vi.fn>;
  setItem: ReturnType<typeof vi.fn>;
  removeItem: ReturnType<typeof vi.fn>;
};

const localStorageMock: StorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

const sessionStorageMock: StorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  configurable: true,
});

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
  configurable: true,
});

describe('auth storage migration contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    sessionStorageMock.getItem.mockReturnValue(null);
  });

  it('consumes and clears a legacy key from localStorage', () => {
    localStorageMock.getItem.mockReturnValue('legacy-local-key');

    expect(getStoredApiKey()).toBe('legacy-local-key');
    expect(localStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('consumes and clears a legacy key from sessionStorage', () => {
    sessionStorageMock.getItem.mockReturnValue('legacy-session-key');

    expect(getStoredApiKey()).toBe('legacy-session-key');
    expect(localStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('does not persist new secrets through setStoredApiKey', () => {
    setStoredApiKey('new-secret-key', true);

    expect(localStorageMock.setItem).not.toHaveBeenCalled();
    expect(sessionStorageMock.setItem).not.toHaveBeenCalled();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('fails closed when storage removal throws', () => {
    localStorageMock.removeItem.mockImplementation(() => {
      throw new Error('local unavailable');
    });
    sessionStorageMock.removeItem.mockImplementation(() => {
      throw new Error('session unavailable');
    });

    expect(() => clearStoredApiKey()).not.toThrow();
  });

  it('falls back when localStorage property access throws', () => {
    const originalLocalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage');
    sessionStorageMock.getItem.mockReturnValue('legacy-session-key');

    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() {
        throw new Error('local getter blocked');
      },
    });

    try {
      expect(getStoredApiKey()).toBe('legacy-session-key');
      expect(sessionStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    } finally {
      Object.defineProperty(window, 'localStorage', originalLocalStorage!);
    }
  });

  it('fails closed when storage property access throws', () => {
    const originalLocalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage');
    const originalSessionStorage = Object.getOwnPropertyDescriptor(window, 'sessionStorage');

    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() {
        throw new Error('local getter blocked');
      },
    });
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      get() {
        throw new Error('session getter blocked');
      },
    });

    try {
      expect(() => clearStoredApiKey()).not.toThrow();
    } finally {
      Object.defineProperty(window, 'localStorage', originalLocalStorage!);
      Object.defineProperty(window, 'sessionStorage', originalSessionStorage!);
    }
  });
});
