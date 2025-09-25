import { Capacitor } from "@capacitor/core";
import { Share } from "@capacitor/share";
import { Filesystem, Directory } from "@capacitor/filesystem";

// RU: Шэрим файл нативно на iOS (или просто скачиваем в вебе).
// EN: Native share on iOS, fallback to browser download.
export async function shareFile(url: string, filename: string, title = "PulsePlate export") {
  if (!Capacitor.isNativePlatform()) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    return;
  }

  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  const buf = await res.arrayBuffer();

  // Robust base64 encoding for binary data
  function base64ArrayBuffer(arrayBuffer: ArrayBuffer): string {
    const base64Chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const bytes = new Uint8Array(arrayBuffer);
    let result = "";
    let i;
    const len = bytes.length;
    for (i = 0; i < len; i += 3) {
      const a = bytes[i];
      const b = i + 1 < len ? bytes[i + 1] : 0;
      const c = i + 2 < len ? bytes[i + 2] : 0;
      result += base64Chars[a >> 2];
      result += base64Chars[((a & 3) << 4) | (b >> 4)];
      result += i + 1 < len ? base64Chars[((b & 15) << 2) | (c >> 6)] : "=";
      result += i + 2 < len ? base64Chars[c & 63] : "=";
    }
    return result;
  }

  const b64 = base64ArrayBuffer(buf);

  const { uri } = await Filesystem.writeFile({
    path: `pulseplate/${filename}`,
    data: b64,
    directory: Directory.Cache,
    recursive: true,
  });

  await Share.share({ title, url: uri, dialogTitle: "Share" });
}
