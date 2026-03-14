import { Events, log } from "./analytics";

type PurchaseRequest = {
  source: string;
  via: string;
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
    });
  } catch {
    // Ignore analytics transport failures in purchase flow.
  }
  throw new Error(WEB_CHECKOUT_UNAVAILABLE_MESSAGE);
}
