import { applyPaidInvoice, verifyCryptoWebhook } from "@/lib/payments";

export const dynamic = "force-dynamic";

/** Crypto Pay webhook: https://help.crypt.bot/crypto-pay-api#webhooks */
export async function POST(req: Request) {
  const raw = await req.text();
  if (!verifyCryptoWebhook(raw, req.headers.get("crypto-pay-api-signature"))) {
    return new Response("invalid signature", { status: 403 });
  }
  try {
    const body = JSON.parse(raw) as { update_type: string; payload: { invoice_id: number; status: string } };
    if (body.update_type === "invoice_paid" && body.payload?.status === "paid") {
      await applyPaidInvoice(String(body.payload.invoice_id));
    }
  } catch (e) {
    console.error("[cryptobot webhook]", e);
  }
  return Response.json({ ok: true });
}
