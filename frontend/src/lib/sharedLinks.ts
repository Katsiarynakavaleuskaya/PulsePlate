export type SignedLink = {
  relative: string;
  absolute: string;
  ttl?: number;
  exp?: number;
};

export type SignedLinkOptions = {
  ttlSeconds?: number;
};

export async function requestSignedLink(
  path: string,
  options: SignedLinkOptions = {}
): Promise<SignedLink> {
  const body: Record<string, unknown> = { path };
  if (typeof options.ttlSeconds === "number") {
    body.ttl_seconds = options.ttlSeconds;
  }

  const response = await fetch("/api/v1/export/sign", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const data = await response.json();
  const relative = data.url as string;
  let absolute: string | undefined;

  if (relative) {
    const base =
      typeof response?.url === "string" && response.url.length > 0
        ? response.url
        : window.location.origin;
    try {
      absolute = new URL(relative, base).toString();
    } catch {
      absolute = undefined;
    }
  }

  return {
    relative,
    absolute: absolute ?? relative,
    ttl: data.ttl ?? options.ttlSeconds,
    exp: data.exp,
  };
}
