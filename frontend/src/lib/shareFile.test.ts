// Tests use the Vitest framework.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@capacitor/core", () => ({
  Capacitor: {
    isNativePlatform: vi.fn(() => false),
  },
}));

vi.mock("@capacitor/share", () => ({
  Share: {
    share: vi.fn(() => Promise.resolve()),
  },
}));

vi.mock("@capacitor/filesystem", () => ({
  Filesystem: {
    writeFile: vi.fn(() => Promise.resolve({ uri: "file://cache/pulseplate/test" })),
    getUri: vi.fn(() => Promise.resolve({ uri: "file://cache/pulseplate/test" })),
    deleteFile: vi.fn(() => Promise.resolve()),
  },
  Directory: {
    Cache: "cache",
  },
}));

import { shareFile } from "./shareFile";
import { Capacitor } from "@capacitor/core";
import { Share } from "@capacitor/share";
import { Filesystem, Directory } from "@capacitor/filesystem";

const originalFetch = global.fetch;
const originalDocument = globalThis.document;

const isNativePlatformMock = vi.mocked(Capacitor.isNativePlatform, true);
const writeFileMock = vi.mocked(Filesystem.writeFile, true);
const shareMock = vi.mocked(Share.share, true);

describe("shareFile", () => {
  let anchorMock: HTMLAnchorElement;
  let createElementMock: ReturnType<typeof vi.fn>;
  let nowSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    anchorMock = {
      href: "",
      download: "",
      click: vi.fn(),
      remove: vi.fn(),
    } as unknown as HTMLAnchorElement;

    createElementMock = vi.fn().mockReturnValue(anchorMock);
    globalThis.document = {
      createElement: createElementMock,
      body: {
        appendChild: vi.fn(),
      },
    } as unknown as Document;

    global.fetch = vi.fn();
    nowSpy = vi.spyOn(Date, "now").mockReturnValue(1_758_958_372_976);

    isNativePlatformMock.mockReturnValue(false);
    writeFileMock.mockResolvedValue({ uri: "file://cache/pulseplate/test" });
    // Исправлено: Share.share должен возвращать объект типа ShareResult, а не undefined.
    // Fixed: Share.share should return an object of type ShareResult, not undefined.
    // Share.share должен возвращать объект типа ShareResult.
    // Share.share should return an object of type ShareResult.
    shareMock.mockResolvedValue({
      activityType: undefined
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    global.fetch = originalFetch;
    nowSpy.mockRestore();

    if (originalDocument) {
      globalThis.document = originalDocument;
    } else {
      // @ts-expect-error - cleaning up test document shim
      delete globalThis.document;
    }
  });

  it("falls back to browser download when not on a native platform", async () => {
    await shareFile("https://example.com/file.pdf", "report.pdf", "Download Report");

    expect(createElementMock).toHaveBeenCalledWith("a");
    expect(anchorMock.href).toBe("https://example.com/file.pdf");
    expect(anchorMock.download).toBe("report.pdf");
    expect(anchorMock.click).toHaveBeenCalledTimes(1);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(writeFileMock).not.toHaveBeenCalled();
    expect(shareMock).not.toHaveBeenCalled();
  });

  it("uses default title when sharing natively without an explicit title", async () => {
    isNativePlatformMock.mockReturnValue(true);
    // Мокаем fetch для возврата успешного ответа с blob
    // Mock fetch to return a successful response with blob
    const buffer = new Uint8Array([1, 2, 3]).buffer;
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: vi.fn().mockResolvedValue({
        arrayBuffer: vi.fn().mockResolvedValue(buffer),
      }),
    });

    await shareFile("https://example.com/file.bin", "export.bin");

    expect(shareMock).toHaveBeenCalledWith({
      title: "PulsePlate export",
      files: ["file://cache/pulseplate/test"],
      dialogTitle: "Share",
    });
  });

  it("fetches, stores, and shares the file on native platforms", async () => {
    isNativePlatformMock.mockReturnValue(true);

    const arrayBuffer = new ArrayBuffer(5);
    const uint8 = new Uint8Array(arrayBuffer);
    uint8.set([0xde, 0xad, 0xbe, 0xef, 0x01]);

    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve({
        arrayBuffer: () => Promise.resolve(arrayBuffer),
      }),
    });

    const expectedPath = "pulseplate/1758958372976-export.bin";

    await shareFile("https://example.com/file.bin", "export.bin", "Native Share");

    expect(global.fetch).toHaveBeenCalled();
    expect(writeFileMock).toHaveBeenCalledWith({
      path: expectedPath,
      data: expect.any(String),
      directory: Directory.Cache,
      recursive: true,
    });
    expect(shareMock).toHaveBeenCalledWith({
      title: "Native Share",
      files: ["file://cache/pulseplate/test"],
      dialogTitle: "Share",
    });

    const { data } = writeFileMock.mock.calls[0][0];
    const encodedData = data as string;
    const expectedBase64 = Buffer.from(uint8).toString("base64");
    expect(encodedData).toBe(expectedBase64);
  });

  it("throws an error when the fetch request is unsuccessful", async () => {
    isNativePlatformMock.mockReturnValue(true);

    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
    });

    await expect(shareFile("https://example.com/missing.bin", "missing.bin")).rejects.toThrow(
      /404/,
    );

    expect(writeFileMock).not.toHaveBeenCalled();
    expect(shareMock).not.toHaveBeenCalled();
  });

  it("propagates file system write errors", async () => {
    isNativePlatformMock.mockReturnValue(true);

    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
      }),
    });

    writeFileMock.mockRejectedValue(new Error("disk full"));

    await expect(shareFile("https://example.com/file", "file.bin")).rejects.toThrow("disk full");
    expect(shareMock).not.toHaveBeenCalled();
  });

  it("propagates share API errors", async () => {
    isNativePlatformMock.mockReturnValue(true);

    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
      }),
    });

    shareMock.mockRejectedValue(new Error("share failed"));

    await expect(shareFile("https://example.com/file", "file.bin")).rejects.toThrow("share failed");
  });

  it("encodes buffers of varying lengths to valid base64 strings", async () => {
    isNativePlatformMock.mockReturnValue(true);

    const buffers = [
      new Uint8Array([0]).buffer,
      new Uint8Array([0, 255]).buffer,
      new Uint8Array([0, 255, 16]).buffer,
      new Uint8Array([1, 2, 3, 4, 5]).buffer,
    ];

    for (const buffer of buffers) {
      // Используем vi для моков в Vitest
      // Use vi for mocks in Vitest
      const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        blob: () => Promise.resolve({
          arrayBuffer: () => Promise.resolve(buffer),
        }),
      });

      await shareFile("https://example.com/file", "file.bin");
    }

    expect(writeFileMock).toHaveBeenCalledTimes(buffers.length);

    buffers.forEach((buffer, index) => {
      const call = writeFileMock.mock.calls[index][0];
      // call.data должен быть строкой в нашем тесте, так как мы мокаем arrayBufferToBase64
      // call.data should be a string in our test, since we mock arrayBufferToBase64
      const encodedData = call.data as string;

      expect(encodedData.length % 4).toBe(0);
      expect(/^[A-Za-z0-9+/=]+$/.test(encodedData)).toBe(true);
      const expectedBase64 = Buffer.from(new Uint8Array(buffer)).toString("base64");
      expect(encodedData).toBe(expectedBase64);
    });
  });
});
