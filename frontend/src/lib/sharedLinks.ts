// RU: Запрос подписанных ссылок через thin HTTP adapter
// EN: Request signed links through thin HTTP adapter

import { api, getApiBase } from "../api/client";

export type SignedLink = {
  relative: string;
  absolute: string;
  ttl?: number;
  exp?: number;
};

export type SignedLinkOptions = {
  ttlSeconds?: number;
};

type SignedLinkResponse = {
  url: string;
  ttl?: number;
  exp?: number;
};
// RU: `/api/v1/export/sign` намеренно скрыт из public OpenAPI, поэтому web держит
// локальный внутренний контракт вместо generated public-schema type.
// EN: `/api/v1/export/sign` is intentionally hidden from public OpenAPI, so the
// web client keeps a local internal contract instead of a generated public-schema type.

export async function requestSignedLink(
  path: string,
  options: SignedLinkOptions = {}
): Promise<SignedLink> {
  const body: Record<string, unknown> = { path };
  if (typeof options.ttlSeconds === "number") {
    body.ttl_seconds = options.ttlSeconds;
  }

  const data = await api<SignedLinkResponse>("/api/v1/export/sign", {
    method: "POST",
    body,
  });

  const relative = data.url;
  let absolute: string | undefined;

  if (relative) {
    try {
      const baseUrl = getApiBase() || window?.location?.origin;
      absolute = new URL(relative, baseUrl).toString();
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
