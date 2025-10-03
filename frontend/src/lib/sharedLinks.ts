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
    const errorBody = await response.json().catch(() => ({}));
    const message =
      typeof errorBody.error === "string"
        ? errorBody.error
        : typeof errorBody.message === "string"
          ? errorBody.message
          : `HTTP ${response.status}`;
    throw new Error(message);
  }

  const data = await response.json();

  if (typeof data.url !== "string" || data.url.length === 0) {
    throw new Error("Invalid response: missing or invalid 'url' field");
  }

  const relative = data.url;
  let absolute: string | undefined;

  if (relative) {
    try {
      absolute = new URL(relative, response?.url ?? window?.location?.origin ?? undefined).toString();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.warn("Failed to construct absolute URL from relative:", relative, error);
      }
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
