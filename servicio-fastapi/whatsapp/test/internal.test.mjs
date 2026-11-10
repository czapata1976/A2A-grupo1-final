import test from 'node:test';
import assert from 'node:assert/strict';
import { createInternalServer } from '../src/server.mjs';
import { eligibleText, stableIds } from '../src/guard.mjs';

const SECRETO = 'secreto-de-prueba-1234567890';

function crearGatewayFalso({ enabled = false, status = 'disabled' } = {}) {
  return {
    status,
    closed: false,
    qr: null,
    enabled: () => enabled,
    async connect() {
      this.status = 'preparing';
    },
    async close() {},
    requestCode(telefono) {
      return telefono === '56911112222';
    },
    pairing: {
      mode: 'code',
      publicState: () => ({
        mode: 'code',
        code_ready: true,
        code_state: 'ready',
        code_expires_at: Date.now() + 60000,
        can_switch: true,
      }),
      codeResult: () => ({ code: 'ABCD1234', expires_at: Date.now() + 60000 }),
      selectMode: (modo) => ['code', 'qr'].includes(modo),
    },
  };
}

async function conServidor(opciones, ejecutar) {
  const { server, close } = createInternalServer({
    createGateway: () => crearGatewayFalso(opciones),
    secret: SECRETO,
    encodeQr: async () => 'data:image/png;base64,AA==',
  });
  await new Promise((resolver) => server.listen(0, '127.0.0.1', resolver));
  const { port } = server.address();
  try {
    await ejecutar(port);
  } finally {
    await new Promise((resolver) => server.close(resolver));
    await close();
  }
}

const pedir = (port, ruta, { metodo = 'GET', secreto = SECRETO, cuerpo } = {}) => {
  const cabeceras = {};
  if (secreto !== null) cabeceras['X-WhatsApp-Secret'] = secreto;
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';
  return fetch(`http://127.0.0.1:${port}${ruta}`, {
    method: metodo,
    headers: cabeceras,
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
};

test('el puente exige el secreto compartido', async () => {
  await conServidor({}, async (port) => {
    assert.equal((await pedir(port, '/internal/estado', { secreto: null })).status, 401);
    assert.equal((await pedir(port, '/internal/estado', { secreto: 'otro' })).status, 401);
    assert.equal((await pedir(port, '/internal/estado')).status, 200);
  });
});

test('estado traduce el pairing a nombres estables', async () => {
  await conServidor({ status: 'connecting' }, async (port) => {
    const datos = await (await pedir(port, '/internal/estado')).json();
    assert.equal(datos.estado, 'connecting');
    assert.equal(datos.modo, 'code');
    assert.equal(datos.codigo_listo, true);
    assert.ok(datos.codigo_expira_en_ms > 0);
  });
});

test('conectar exige autorización explícita', async () => {
  await conServidor({ enabled: false }, async (port) => {
    const respuesta = await pedir(port, '/internal/conectar', { metodo: 'POST' });
    assert.equal(respuesta.status, 403);
    assert.equal((await respuesta.json()).error, 'connection_not_authorized');
  });
});

test('conectar y desconectar cambian el ciclo de vida', async () => {
  await conServidor({ enabled: true }, async (port) => {
    const conectado = await pedir(port, '/internal/conectar', { metodo: 'POST' });
    assert.equal(conectado.status, 202);
    const desconectado = await pedir(port, '/internal/desconectar', { metodo: 'POST' });
    assert.equal(desconectado.status, 202);
    const estado = await (await pedir(port, '/internal/estado')).json();
    assert.equal(estado.estado, 'stopped');
  });
});

test('modo y teléfono validan la entrada', async () => {
  await conServidor({}, async (port) => {
    assert.equal(
      (await pedir(port, '/internal/modo', { metodo: 'POST', cuerpo: { modo: 'sms' } })).status,
      400
    );
    assert.equal(
      (await pedir(port, '/internal/modo', { metodo: 'POST', cuerpo: { modo: 'qr' } })).status,
      200
    );
    assert.equal(
      (await pedir(port, '/internal/codigo', { metodo: 'POST', cuerpo: { telefono: '+569' } })).status,
      400
    );
    assert.equal(
      (
        await pedir(port, '/internal/codigo', {
          metodo: 'POST',
          cuerpo: { telefono: '56911112222' },
        })
      ).status,
      202
    );
  });
});

test('el código y el QR se sirven solo con la sesión activa', async () => {
  await conServidor({}, async (port) => {
    const codigo = await (await pedir(port, '/internal/codigo')).json();
    assert.equal(codigo.codigo, 'ABCD1234');
    assert.ok(codigo.expira_en_ms > 0);
    const qr = await (await pedir(port, '/internal/qr')).json();
    assert.equal(qr.imagen, null);
  });
});

test('guard solo acepta mensajes propios en texto plano', () => {
  const identidad = '56911112222@s.whatsapp.net';
  const base = {
    key: { fromMe: true, remoteJid: identidad, id: 'ABC123' },
    message: { conversation: '  hola  ' },
  };
  assert.equal(eligibleText(base, [identidad]), 'hola');
  assert.equal(eligibleText(base, ['56999999999@s.whatsapp.net']), null);
  assert.equal(
    eligibleText({ ...base, message: { imageMessage: {} } }, [identidad]),
    null
  );
  assert.equal(
    eligibleText({ ...base, key: { ...base.key, remoteJid: '1203630@g.us' } }, [identidad]),
    null
  );
});

test('stableIds deriva sesión y solicitud del identificador propio', () => {
  const ids = stableIds('56911112222@s.whatsapp.net', 'ABC123');
  assert.match(ids.conversation_id, /^wa_[a-f0-9]{48}$/);
  assert.match(ids.request_id, /^wa_[a-f0-9]{48}$/);
  assert.notEqual(ids.conversation_id, ids.request_id);
});
