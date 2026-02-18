import { api } from "../api/client";
import { Events, log } from "./analytics";

type PurchaseRequest = {
  source: string;
  via: string;
};

type PurchaseResponse = {
  status: "ok" | string;
  entitlement?: string;
};

/**
 * RU: Единая purchase-точка для web paywall CTA.
 * EN: Single purchase entrypoint for web paywall CTA.
 */
export async function purchasePremium(request: PurchaseRequest): Promise<PurchaseResponse> {
  const response = await api<PurchaseResponse>("/api/purchase", {
    method: "POST",
    body: {
      source: request.source,
      via: request.via,
    },
  });

  if (response.status !== "ok") {
    try {
      log(Events.PURCHASE_FAILURE, {
        source: request.source,
        via: request.via,
        status: response.status,
      });
    } catch {
      // Ignore analytics transport failures in purchase flow.
    }
    throw new Error("Purchase failed");
  }

  // RU: После успешной покупки синхронизируем premium-статус в клиенте.
  // EN: Keep local premium state in sync after successful purchase.
  if (typeof window !== "undefined") {
    localStorage.setItem("pp_premium", "true");
    window.dispatchEvent(new Event("pp-premium-change"));
  }

  try {
    log(Events.PURCHASE_SUCCESS, {
      source: request.source,
      via: request.via,
      entitlement: response.entitlement ?? "premium",
    });
  } catch {
    // Ignore analytics transport failures in purchase flow.
  }

  return response;
}
