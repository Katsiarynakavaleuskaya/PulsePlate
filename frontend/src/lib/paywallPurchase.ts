import { Events, log } from "./analytics";

type PurchaseRequest = {
  source: string;
  via: string;
  triggerReason?: string;
  actionType?: string;
  recommendedSurface?: string;
  recommendedTier?: string;
  whyNow?: string;
};

export const WEB_CHECKOUT_UNAVAILABLE_MESSAGE =
  "Web upgrade checkout is not available yet. Use the iOS App Store flow today.";

/**
 * RU: Единая purchase-точка для web paywall CTA.
 * EN: Single purchase entrypoint for web paywall CTA.
 */
export async function purchasePremium(request: PurchaseRequest): Promise<never> {
  try {
    log(Events.PURCHASE_FAILURE, {
      source: request.source,
      via: request.via,
      status: "web_checkout_unavailable",
      ...(request.triggerReason ? { triggerReason: request.triggerReason } : {}),
      ...(request.actionType ? { actionType: request.actionType } : {}),
      ...(request.recommendedSurface ? { recommendedSurface: request.recommendedSurface } : {}),
      ...(request.recommendedTier ? { recommendedTier: request.recommendedTier } : {}),
      ...(request.whyNow ? { whyNow: request.whyNow } : {}),
    });
  } catch {
    // Ignore analytics transport failures in purchase flow.
  }
  throw new Error(WEB_CHECKOUT_UNAVAILABLE_MESSAGE);
}
