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
  const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));

  const { uri } = await Filesystem.writeFile({
    path: `pulseplate/${filename}`,
    data: b64,
    directory: Directory.Cache,
    recursive: true,
  });

  await Share.share({ title, url: uri, dialogTitle: "Share" });
}
