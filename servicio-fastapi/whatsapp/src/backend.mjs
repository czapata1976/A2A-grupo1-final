// One request; never repeat an uncertain response or effect automatically.
export async function ask(
  payload,
  {
    fetch = globalThis.fetch,
    secret = process.env.WHATSAPP_SECRET,
    base = process.env.WHATSAPP_BACKEND_URL,
    timeoutMs = Number(process.env.WHATSAPP_TIMEOUT_MS ?? 180000),
  } = {}
) {
  if (typeof secret !== 'string' || !secret || typeof base !== 'string' || !base) {
    throw Error('backend_not_configured');
  }
  const reply = await fetch(base, {
    method: 'POST',
    redirect: 'error',
    headers: { 'X-WhatsApp-Secret': secret, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (reply.status !== 200) throw Error('agent_failed_no_automatic_retry');
  const result = await reply.json();
  if (typeof result.respuesta !== 'string' || !result.respuesta.trim()) {
    throw Error('invalid_agent_response');
  }
  return result;
}
