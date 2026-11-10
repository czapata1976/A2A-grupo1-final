const $ = (id) => document.getElementById(id);

const ETIQUETAS = {
  disabled: 'Canal preparado, sin vincular',
  preparing: 'Preparando conexión',
  connecting: 'Esperando a WhatsApp',
  restarting: 'Finalizando vinculación',
  connected: 'Conectado',
  review_required: 'Revisión necesaria',
  stopping: 'Desconectando',
  stopped: 'Desconectado',
};

const DETALLES = {
  connected: 'Vinculación confirmada. Envía un mensaje nuevo en el chat «Mensaje para ti».',
  review_required:
    'Resultado no confirmado. Revisa Dispositivos vinculados en tu celular, pulsa Desconectar y luego Iniciar nuevo intento. No se solicitó otro código automáticamente.',
  stopping: 'Esperando a que terminen las operaciones anteriores. No se borran tus credenciales.',
  stopped: 'Puedes iniciar un nuevo intento cuando quieras.',
};

let clave = '';
let temporizador = null;
let revision = 0;

function mostrarError(texto, destino = 'error-acceso') {
  const nodo = $(destino);
  nodo.textContent = texto;
  nodo.hidden = false;
  clearTimeout(nodo._ocultar);
  nodo._ocultar = setTimeout(() => {
    nodo.hidden = true;
  }, 12000);
}

async function api(ruta, { metodo = 'GET', cuerpo } = {}) {
  const cabeceras = { 'X-API-Key': clave };
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';
  const respuesta = await fetch(ruta, {
    method: metodo,
    headers: cabeceras,
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    cache: 'no-store',
    credentials: 'omit',
  });
  let datos = {};
  try {
    datos = await respuesta.json();
  } catch {
    datos = {};
  }
  if (!respuesta.ok) {
    const mensaje =
      datos?.error?.mensaje ||
      (typeof datos?.detail === 'string' ? datos.detail : null) ||
      `Error ${respuesta.status}`;
    throw new Error(mensaje);
  }
  return datos;
}

function fijarEstado(texto, tono) {
  $('estado-texto').textContent = texto;
  $('indicador').className = `punto ${tono}`;
}

function limpiarCodigo() {
  $('codigo-valor').textContent = '';
  $('caja-codigo').hidden = true;
}

function limpiarQr() {
  const imagen = $('qr-imagen');
  imagen.hidden = true;
  imagen.removeAttribute('src');
  $('caja-qr').hidden = true;
}

async function refrescar() {
  const actual = ++revision;
  let estado;
  try {
    estado = await api('/whatsapp/estado');
  } catch (error) {
    fijarEstado('Acceso no disponible', 'punto-error');
    $('wa-detalle').textContent = error.message;
    $('wa-vinculo').hidden = true;
    return;
  }
  if (actual !== revision) return;

  const valor = estado.estado || 'disabled';
  fijarEstado(ETIQUETAS[valor] ?? 'Estado no disponible', valor === 'connected' ? 'punto-ok' : 'punto-espera');
  $('wa-detalle').textContent = DETALLES[valor] ?? 'Mantén un solo conector activo por celular.';
  $('wa-aviso').textContent =
    estado.codigo_estado === 'pending'
      ? 'Solicitando el código una sola vez. Espera sin reenviar el formulario.'
      : 'El código se borra al vencer o desconectar. No es un SMS y no confirma por sí solo la vinculación.';

  $('btn-conectar').disabled = !['disabled', 'stopped'].includes(valor);
  $('btn-conectar').textContent = valor === 'stopped' ? 'Iniciar nuevo intento' : 'Iniciar vinculación';
  $('btn-desconectar').disabled = ['disabled', 'stopped', 'stopping'].includes(valor);

  const activo = !['stopping', 'stopped', 'review_required', 'connected'].includes(valor);
  $('wa-vinculo').hidden = !activo;
  $('btn-codigo').disabled = !estado.codigo_listo;
  $('btn-modo-codigo').dataset.activo = String(estado.modo === 'code');
  $('btn-modo-qr').dataset.activo = String(estado.modo === 'qr');
  $('btn-modo-codigo').disabled = !estado.puede_cambiar;
  $('btn-modo-qr').disabled = !estado.puede_cambiar;
  $('form-telefono').hidden = estado.modo !== 'code';
  limpiarCodigo();
  limpiarQr();

  if (!activo) return;

  if (estado.modo === 'code') {
    try {
      const resultado = await api('/whatsapp/codigo');
      if (actual !== revision) return;
      const codigo = resultado.codigo;
      const restante = Number(resultado.expira_en_ms);
      if (typeof codigo === 'string' && /^[A-Z0-9]{8}$/.test(codigo) && restante > 0) {
        $('codigo-valor').textContent = `${codigo.slice(0, 4)}-${codigo.slice(4)}`;
        $('caja-codigo').hidden = false;
      }
    } catch {
      limpiarCodigo();
    }
  } else {
    try {
      const resultado = await api('/whatsapp/qr');
      if (actual !== revision) return;
      if (typeof resultado.imagen === 'string' && resultado.imagen.startsWith('data:image/')) {
        $('qr-imagen').src = resultado.imagen;
        $('qr-imagen').hidden = false;
        $('caja-qr').hidden = false;
      }
    } catch {
      limpiarQr();
    }
  }
}

function iniciarSondeo() {
  clearInterval(temporizador);
  temporizador = setInterval(refrescar, 3000);
}

$('form-acceso').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  clave = $('clave').value;
  $('clave').value = '';
  $('error-acceso').hidden = true;
  try {
    await api('/whatsapp/estado');
  } catch (error) {
    clave = '';
    mostrarError(error.message);
    return;
  }
  $('panel-acceso').hidden = true;
  $('panel-wa').hidden = false;
  await refrescar();
  iniciarSondeo();
});

$('btn-ver').addEventListener('click', () => {
  const campo = $('clave');
  campo.type = campo.type === 'password' ? 'text' : 'password';
  $('btn-ver').textContent = campo.type === 'password' ? 'Ver' : 'Ocultar';
});

$('btn-conectar').addEventListener('click', async () => {
  $('btn-conectar').disabled = true;
  try {
    await api('/whatsapp/conectar', { metodo: 'POST' });
  } catch (error) {
    mostrarError(error.message, 'wa-aviso');
  }
  await refrescar();
});

$('btn-desconectar').addEventListener('click', async () => {
  $('btn-desconectar').disabled = true;
  try {
    await api('/whatsapp/desconectar', { metodo: 'POST' });
  } catch (error) {
    mostrarError('No se confirmó la desconexión: ' + error.message, 'wa-aviso');
  }
  await refrescar();
});

$('form-telefono').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const telefono = $('telefono').value.trim();
  $('telefono').value = '';
  $('btn-codigo').disabled = true;
  try {
    await api('/whatsapp/codigo', { metodo: 'POST', cuerpo: { telefono } });
  } catch (error) {
    mostrarError(
      'No se confirmó la solicitud: ' + error.message + ' No se generará otro código automáticamente.',
      'wa-aviso'
    );
  }
  await refrescar();
});

for (const [id, modo] of [
  ['btn-modo-codigo', 'code'],
  ['btn-modo-qr', 'qr'],
]) {
  $(id).addEventListener('click', async () => {
    limpiarCodigo();
    limpiarQr();
    try {
      await api('/whatsapp/modo', { metodo: 'POST', cuerpo: { modo } });
    } catch (error) {
      mostrarError(
        'No se pudo cambiar el modo: ' + error.message + ' Desconecta antes de otro intento.',
        'wa-aviso'
      );
    }
    await refrescar();
  });
}
