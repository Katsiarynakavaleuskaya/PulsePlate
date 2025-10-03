import { Capacitor } from "@capacitor/core";
import { Share } from "@capacitor/share";
import { Filesystem, Directory } from "@capacitor/filesystem";
import type { SignedLink, SignedLinkOptions } from "./sharedLinks";
import { requestSignedLink } from "./sharedLinks";

const TECH_ERROR_PATTERN = /network|failed|exception|stack|error|undefined|not found|timeout|internal/i;

function downloadInBrowser(url: string, filename: string) {
  if (typeof document === "undefined") {
    return;
  }

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";

  const container = document.body ?? document.documentElement ?? null;
  if (container && typeof container.appendChild === "function") {
    container.appendChild(anchor);
  }

  anchor.click();

  if (typeof anchor.remove === "function") {
    anchor.remove();
  } else if (container && typeof container.removeChild === "function") {
    try {
      container.removeChild(anchor);
    } catch {
      // ignore DOM cleanup failures in non-browser environments
    }
  }
}

async function arrayBufferToBase64(buffer: ArrayBuffer): Promise<string> {
  if (typeof Blob !== "undefined" && typeof FileReader !== "undefined") {
    const blob = new Blob([buffer]);
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = typeof reader.result === "string" ? reader.result : "";
        const base64 = result.startsWith("data:") ? result.split(",", 2)[1] ?? "" : result;
        resolve(base64);
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(blob);
    });
  }

  // Fallback chunked encoding when FileReader isn't available
  const base64Chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const bytes = new Uint8Array(buffer);
  let result = "";

  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i];
    const b = i + 1 < bytes.length ? bytes[i + 1] : 0;
    const c = i + 2 < bytes.length ? bytes[i + 2] : 0;

    result += base64Chars[a >> 2];
    result += base64Chars[((a & 3) << 4) | (b >> 4)];
    result += i + 1 < bytes.length ? base64Chars[((b & 15) << 2) | (c >> 6)] : "=";
    result += i + 2 < bytes.length ? base64Chars[c & 63] : "=";
  }

  return result;
}

function isAbortError(error: unknown): boolean {
  return typeof DOMException !== "undefined" && error instanceof DOMException && error.name === "AbortError";
}

// RU: Шэрим файл нативно на iOS (или используем Web Share/скачивание в браузере).
// EN: Native share on iOS; on web prefer Web Share API then fall back to download.
export async function shareFile(url: string, filename: string, title = "PulsePlate export") {
  if (!Capacitor.isNativePlatform()) {
    if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
      try {
        await navigator.share({ title, url });
        return;
      } catch (error) {
        if (isAbortError(error)) {
          return;
        }
        // fall back to download if share was rejected for other reasons
      }
    }
    downloadInBrowser(url, filename);
    return;
  }

  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  const buf = await res.arrayBuffer();
  const base64Data = await arrayBufferToBase64(buf);
  const safeFilename =
    filename
      .split(/[\\/]/)
      .filter(Boolean)
      .pop()
      ?.replace(/\.+/g, ".")
      .replace(/[<>:"|?*]/g, "_") || "export.dat";
  const cachePath = `pulseplate/${Date.now()}-${safeFilename}`;

  try {
    const writeResult = await Filesystem.writeFile({
      path: cachePath,
      data: base64Data,
      directory: Directory.Cache,
      recursive: true,
    });
    const uriResult =
      typeof Filesystem.getUri === "function"
        ? await Filesystem.getUri({ directory: Directory.Cache, path: cachePath }).catch(() => null)
        : null;
    const candidateUri = uriResult?.uri ?? writeResult.uri;
    const resolvedUri = typeof candidateUri === "string" ? candidateUri.trim() : "";

    if (!resolvedUri) {
      throw new Error("Share unavailable: unable to resolve file URI");
    }

    const files = [resolvedUri];
    await Share.share({ title, files, dialogTitle: "Share" });
  } finally {
    try {
      await Filesystem.deleteFile({ path: cachePath, directory: Directory.Cache });
    } catch {
      // ignore cleanup failures
    }
  }
}

export async function shareSignedExport(
  path: string,
  filename: string,
  title = "PulsePlate export",
  options: SignedLinkOptions = {}
): Promise<SignedLink> {
  const link = await requestSignedLink(path, options);
  await shareFile(link.absolute, filename, title);
  return link;
}

export function formatShareErrorMessage(
  error: unknown,
  fallback = "Не удалось поделиться файлом. Попробуйте ещё раз."
): string {
  if (typeof error === "string" && error.trim().length > 0) {
    return error;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return TECH_ERROR_PATTERN.test(error.message) ? fallback : error.message;
  }

  if (typeof error === "object" && error !== null) {
    const maybeMessage = (error as Record<string, unknown>).message;
    if (typeof maybeMessage === "string" && maybeMessage.trim().length > 0) {
      return TECH_ERROR_PATTERN.test(maybeMessage) ? fallback : maybeMessage;
    }
  }

  return fallback;
}
