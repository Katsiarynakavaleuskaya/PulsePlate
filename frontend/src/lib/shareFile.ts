import { Capacitor } from "@capacitor/core";
import { Share } from "@capacitor/share";
import { Filesystem, Directory } from "@capacitor/filesystem";
import { fetchBlob } from "../api/client";
import type { SignedLink, SignedLinkOptions } from "./sharedLinks";
import { requestSignedLink } from "./sharedLinks";

const TECH_ERROR_PATTERN = /network|failed|exception|stack|error|undefined|not found|timeout|internal/i;

/**
 * Downloads a file in the browser by creating a temporary anchor element.
 *
 * @param url - The URL to download
 * @param filename - The filename for the download
 */
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

/**
 * Shares a file using native platform capabilities or web APIs.
 *
 * On native platforms (iOS/Android), uses Capacitor Share plugin.
 * On web, attempts Web Share API first, then falls back to download.
 *
 * @param url - The URL of the file to share
 * @param filename - The filename for the shared file
 * @param title - The title for the share dialog (default: "PulsePlate export")
 */
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

  // Use fetchBlob for thin-client compliance (no direct fetch outside client.ts)
  const blob = await fetchBlob(url);
  const buf = await blob.arrayBuffer();
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
    } catch (error) {
      // Log cleanup failures for diagnostics, particularly important for mobile storage management
      console.warn("[shareFile] Failed to cleanup cache file:", error);
    }
  }
}

/**
 * Shares a file using a signed link for secure access.
 *
 * @param path - The file path to share
 * @param filename - The filename for the shared file
 * @param title - The title for the share dialog (default: "PulsePlate export")
 * @param options - Options for generating the signed link
 * @returns Promise resolving to the signed link
 */
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

/**
 * Formats error messages for file sharing operations.
 * Filters out technical error details and provides user-friendly messages.
 *
 * @param error - The error to format
 * @param fallback - Fallback message if error cannot be formatted (default: Russian error message)
 * @returns User-friendly error message
 */
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

  const rawMessage =
    typeof error === "object" && error && "message" in error
      ? String((error as Record<string, unknown>).message)
      : "";
  if (!rawMessage) {
    return fallback;
  }

  return TECH_ERROR_PATTERN.test(rawMessage) ? fallback : rawMessage;
}
