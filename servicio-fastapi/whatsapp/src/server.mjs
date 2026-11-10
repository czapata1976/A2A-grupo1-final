import http from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import QRCode from 'qrcode';
import { validPhone } from './pairing.mjs';

const equal = (a, b) =>
  typeof a === 'string' && Buffer.byteLength(a) === Buffer.byteLength(b) && timingSafeEqual(Buffer.from(a), Buffer.from(b));

const json = (res, status, value) => {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
  });
  res.end(JSON.stringify(value));
};

async function body(req, key) {
  if (!/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers['content-type'] ?? '')) throw Error('invalid_input');
  let bytes = 0;
  const chunks = [];
  for await (const chunk of req) {
    bytes += chunk.length;
    if (bytes > 256) throw Error('invalid_input');
    chunks.push(chunk);
  }
  const value = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== 1 || !Object.hasOwn(value, key)) {
    throw Error('invalid_input');
  }
  return value[key];
}

/**
 * API interna del puente. Escucha solo en loopback y exige WHATSAPP_SECRET.
 * La superficie pública (panel, API clave) vive en el servicio FastAPI.
 */
export function createInternalServer({ createGateway, secret, encodeQr = (value) => QRCode.toDataURL(value) }) {
  if (typeof secret !== 'string' || secret.length < 16) throw Error('bridge_configuration_required');
  let gateway = createGateway();
  let lifecycle = 'idle';
  let stopping = null;
  let revision = 0;

  const estado = () => {
    const base = gateway.pairing.publicState();
    return {
      estado: lifecycle === 'idle' ? gateway.status : lifecycle,
      modo: base.mode,
      codigo_listo: base.code_ready,
      codigo_estado: base.code_state,
      codigo_expira_en_ms: Number.isFinite(base.code_expires_at)
        ? Math.max(0, base.code_expires_at - Date.now())
        : null,
      puede_cambiar: base.can_switch,
    };
  };

  const stop = () => {
    if (stopping) return stopping;
    if (lifecycle === 'stopped') return Promise.resolve();
    lifecycle = 'stopping';
    revision++;
    const previous = gateway;
    stopping = Promise.resolve()
      .then(() => previous.close())
      .then(() => {
        if (gateway === previous) lifecycle = 'stopped';
      })
      .catch(() => {
        if (gateway === previous) lifecycle = 'review_required';
      })
      .finally(() => {
        stopping = null;
      });
    return stopping;
  };

  const server = http.createServer(async (req, res) => {
    try {
      if (!equal(req.headers['x-whatsapp-secret'], secret)) {
        return json(res, 401, { error: 'operator_authentication_required' });
      }

      if (req.method === 'GET' && req.url === '/internal/salud') {
        return json(res, 200, { estado: 'ok' });
      }

      if (req.method === 'GET' && req.url === '/internal/estado') {
        return json(res, 200, estado());
      }

      if (req.method === 'GET' && req.url === '/internal/codigo') {
        const resultado =
          lifecycle === 'idle' && !gateway.closed ? gateway.pairing.codeResult() : { code: null, expires_at: null };
        return json(res, 200, {
          codigo: resultado.code ?? null,
          expira_en_ms: Number.isFinite(resultado.expires_at)
            ? Math.max(0, resultado.expires_at - Date.now())
            : null,
        });
      }

      if (req.method === 'GET' && req.url === '/internal/qr') {
        const imagen =
          lifecycle === 'idle' && !gateway.closed && gateway.pairing.mode === 'qr' && gateway.qr
            ? await encodeQr(gateway.qr)
            : null;
        return json(res, 200, { imagen });
      }

      if (req.method === 'POST' && req.url === '/internal/conectar') {
        if (lifecycle === 'stopping' || stopping || (lifecycle !== 'stopped' && gateway.status !== 'disabled')) {
          return json(res, 409, { error: 'disconnect_before_new_attempt' });
        }
        if (!gateway.enabled()) return json(res, 403, { error: 'connection_not_authorized' });
        if (lifecycle === 'stopped') {
          gateway = createGateway();
          lifecycle = 'idle';
        }
        revision++;
        const starting = gateway;
        void starting.connect().catch(() => starting.halt());
        return json(res, 202, { estado: 'preparing' });
      }

      if (req.method === 'POST' && req.url === '/internal/desconectar') {
        void stop();
        return json(res, 202, { estado: lifecycle });
      }

      if (req.method === 'POST' && req.url === '/internal/modo') {
        const target = gateway;
        const revisionActual = revision;
        let modo;
        try {
          modo = await body(req, 'modo');
        } catch {
          return json(res, 400, { error: 'invalid_link_mode' });
        }
        if (!['code', 'qr'].includes(modo)) return json(res, 400, { error: 'invalid_link_mode' });
        if (
          target !== gateway ||
          revisionActual !== revision ||
          lifecycle !== 'idle' ||
          !target.pairing.selectMode(modo)
        ) {
          return json(res, 409, { error: 'link_mode_unavailable' });
        }
        return json(res, 200, { modo });
      }

      if (req.method === 'POST' && req.url === '/internal/codigo') {
        const target = gateway;
        const revisionActual = revision;
        let telefono;
        try {
          telefono = await body(req, 'telefono');
        } catch {
          return json(res, 400, { error: 'invalid_phone' });
        }
        if (!validPhone(telefono)) return json(res, 400, { error: 'invalid_phone' });
        if (
          target !== gateway ||
          revisionActual !== revision ||
          lifecycle !== 'idle' ||
          !target.requestCode(telefono)
        ) {
          return json(res, 409, { error: 'pairing_not_ready' });
        }
        return json(res, 202, { estado: 'pending' });
      }

      return json(res, 404, { error: 'not_found' });
    } catch {
      return json(res, 503, { error: 'operation_unavailable_no_automatic_retry' });
    }
  });

  server.requestTimeout = 10000;
  server.headersTimeout = 10000;
  return { server, close: stop };
}
