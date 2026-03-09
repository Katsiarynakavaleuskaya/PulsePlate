// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest';

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

type StorageModule = typeof import('../storage');

async function loadStorageModule(): Promise<StorageModule> {
  vi.resetModules();
  return import('../storage');
}

describe('auth storage migration contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    localStorageMock.getItem.mockReturnValue(null);
    sessionStorageMock.getItem.mockReturnValue(null);
    localStorageMock.removeItem.mockImplementation(() => undefined);
    sessionStorageMock.removeItem.mockImplementation(() => undefined);
  });

  it('consumes and clears a legacy key from localStorage', async () => {
    const { getStoredApiKey } = await loadStorageModule();
    localStorageMock.getItem.mockReturnValue('legacy-local-key');

    expect(getStoredApiKey()).toBe('legacy-local-key');
    expect(localStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('consumes and clears a legacy key from sessionStorage', async () => {
    const { getStoredApiKey } = await loadStorageModule();
    sessionStorageMock.getItem.mockReturnValue('legacy-session-key');

    expect(getStoredApiKey()).toBe('legacy-session-key');
    expect(localStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('does not persist new secrets through setStoredApiKey', async () => {
    const { setStoredApiKey } = await loadStorageModule();
    setStoredApiKey('new-secret-key', true);

    expect(localStorageMock.setItem).not.toHaveBeenCalled();
    expect(sessionStorageMock.setItem).not.toHaveBeenCalled();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('fails closed when storage removal throws', async () => {
    const { clearStoredApiKey } = await loadStorageModule();
    localStorageMock.removeItem.mockImplementation(() => {
      throw new Error('local unavailable');
    });
    sessionStorageMock.removeItem.mockImplementation(() => {
      throw new Error('session unavailable');
    });

    expect(() => clearStoredApiKey()).not.toThrow();
  });

  it('does not return a legacy key when cleanup fails after a successful read', async () => {
    const { getStoredApiKey } = await loadStorageModule();
    localStorageMock.getItem.mockReturnValue('legacy-local-key');
    localStorageMock.removeItem.mockImplementation(() => {
      throw new Error('local unavailable');
    });

    expect(getStoredApiKey()).toBeNull();
    expect(localStorageMock.getItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(LEGACY_STORAGE_KEY);
  });

  it('consumes the legacy key only once when cleanup fails', async () => {
    const { getStoredApiKey } = await loadStorageModule();
    localStorageMock.getItem.mockReturnValue('legacy-local-key');
    localStorageMock.removeItem.mockImplementation(() => {
      throw new Error('local unavailable');
    });

    expect(getStoredApiKey()).toBeNull();
    expect(getStoredApiKey()).toBeNull();
    expect(localStorageMock.getItem).toHaveBeenCalledTimes(1);
  });

  it('falls back when localStorage property access throws', async () => {
    const { getStoredApiKey } = await loadStorageModule();
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

  it('fails closed when storage property access throws', async () => {
    const { clearStoredApiKey } = await loadStorageModule();
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
