import { makeWASocket, generateMessageIDV2, Browsers } from '@whiskeysockets/baileys';
import pino from 'pino';
import { createHash } from 'node:crypto';
import { Store } from './store.mjs';
import { normalizeJid, stableIds } from './guard.mjs';
import { ask } from './backend.mjs';
import { PhoneLink } from './pairing.mjs';

const logger = pino({ level: process.env.WHATSAPP_LOG_LEVEL || 'silent' });

export class Gateway {
    constructor({
        parse,
        audio = false,
        createSocket = makeWASocket,
        openStore = () => Store.open(),
        maxReconnects = 3,
        reconnectMs = 1000,
    }) {
        Object.assign(this, { parse, audio, createSocket, openStore, maxReconnects, reconnectMs });
        this.status = 'disabled';
        this.socket = this.store = this.qr = null;
        this.busy = false;
        this.ready = null;
        this.queue = [];
        this.authWrites = Promise.resolve();
        this.closed = false;
        this.generation = 0;
        this.reconnects = 0;
        this.everConnected = false;
        this.pairingRestarts = 0;
        this.pairing = new PhoneLink({ onUncertain: () => this.halt() });
    }

    enabled() {
        return process.env.WHATSAPP_ENABLE_CONNECTION === 'true';
    }

    requestCode(phone) {
        return !this.closed && this.pairing.request(phone);
    }

    halt() {
        if (this.closed) return;
        this.status = 'review_required';
        this.closed = true;
        this.ready = null;
        this.qr = null;
        this.generation++;
        clearTimeout(this.reconnectTimer);
        this.pairing.stop();
        this.queue.length = 0;
        try {
            this.socket?.end(Error('transport_stopped'));
        } catch { }
        this.pipelineClosed = Promise.resolve();
    }

    async connect() {
        if (!this.enabled() || this.status !== 'disabled' || this.closed) throw Error('connection_not_authorized');
        this.status = 'preparing';
        this.opening = Promise.resolve().then(() => (this.closed ? null : this.openStore()));
        this.store = await this.opening;
        if (this.closed) {
            if (this.store) await this.store.close();
            return;
        }
        this.store.onLost = () => this.halt();
        this.openSocket(true);
    }

    openSocket(newAttempt = false) {
        if (this.closed) return;
        const generation = ++this.generation;
        const socket = this.createSocket({
            auth: this.store.auth,
            logger,
            browser: Browsers.ubuntu('Chrome'),
            printQRInTerminal: false,
            syncFullHistory: false,
            markOnlineOnConnect: false,
            // No desactivar shouldSyncHistoryMessage: sin la sincronización inicial Baileys no recibe
            // los LID mappings y la vinculación termina en error de sesión (aviso DANGER de Baileys).
            // La sesión de vinculación dura 5 min: el QR puede rotar sin cortar el intento.
            qrTimeout: Number(process.env.WHATSAPP_QR_TIMEOUT_MS ?? 300000),
        });
        this.socket = socket;
        this.status = 'connecting';
        this.pairing.begin(socket, this.store.auth.creds, { newAttempt });
        const current = () => !this.closed && generation === this.generation && socket === this.socket;

        socket.ev.on('creds.update', () => {
            if (!current()) return;
            this.authWrites = this.authWrites.then(() => this.store.saveCreds()).catch(() => this.halt());
        });

        socket.ev.on('connection.update', (value) => {
            if (!current()) return;
            if (Object.hasOwn(value, 'qr')) {
                this.qr = typeof value.qr === 'string' ? value.qr : null;
                this.pairing.observeQr(socket, value.qr);
            }
            if (value.connection === 'open') {
                const identities = [socket.user?.id, socket.user?.lid].map(normalizeJid).filter(Boolean);
                if (this.store.auth.creds.registered !== true || !identities.length) {
                    this.halt();
                    return;
                }
                this.pairing.stop();
                this.qr = null;
                this.ready = Date.now() / 1000;
                this.status = 'connected';
                this.everConnected = true;
                this.pairingRestarts = 0;
                logger.info({ registered: this.store.auth.creds.registered === true }, 'conexión abierta');
            }
            if (value.connection === 'close') {
                const code = value.lastDisconnect?.error?.output?.statusCode;
                const detalle = value.lastDisconnect?.error?.message ?? value.lastDisconnect?.error?.output?.payload?.message;
                logger.warn({ code, detalle, reconnects: this.reconnects, restarts: this.pairingRestarts }, 'conexión cerrada');
                // 515 = "restart required": WhatsApp lo envía justo después de escanear el QR o de
                // registrar el dispositivo. Hay que reconectar aunque `registered` aún no se haya
                // persistido; de lo contrario la vinculación se pierde y el teléfono muestra error.
                // WhatsApp puede pedir más de un reinicio seguido, por eso se cuentan hasta 3.
                const safe =
                    code === 515
                        ? this.pairingRestarts < 3
                        : [405, 408].includes(code) && (!this.pairing.attempted || this.everConnected);
                this.ready = null;
                this.qr = null;
                this.pairing.stop();
                if (!safe || this.reconnects >= this.maxReconnects) {
                    this.halt();
                    return;
                }
                if (code === 515) this.pairingRestarts++;
                this.reconnects++;
                this.socket = null;
                this.status = 'restarting';
                const revision = ++this.generation;
                this.reconnectTimer = setTimeout(() => {
                    void this.authWrites
                        .then(() => {
                            if (!this.closed && revision === this.generation) this.openSocket();
                        })
                        .catch(() => this.halt());
                }, this.reconnectMs);
                this.reconnectTimer.unref?.();
            }
        });

        socket.ev.on('messages.upsert', (value) => {
            logger.info({ tipo: value.type, cantidad: value.messages?.length }, 'upsert');
            if (!current()) return;
            // Un error al procesar o enviar un mensaje no debe tumbar la sesión vinculada:
            // se registra y se descarta ese mensaje. El cierre de conexión se maneja aparte.
            this.serial = (this.serial ?? Promise.resolve())
                .then(() => this.accept(value))
                .catch((error) => logger.warn({ detalle: error?.message }, 'mensaje descartado'));
        });
    }

    async accept(event) {
        // WhatsApp entrega los mensajes escritos desde el propio teléfono como `append`; los que
        // llegan en vivo desde el servidor como `notify`. Se aceptan ambos y el filtro de tiempo
        // descarta el historial antiguo.
        if (this.closed || this.ready === null || event.requestId) return;
        if (!['notify', 'append'].includes(event.type)) return;
        for (const item of event.messages ?? []) {
            logger.info(
                {
                    deMi: item.key?.fromMe,
                    jid: item.key?.remoteJid,
                    participant: item.key?.participant,
                    claves: item.message ? Object.keys(item.message) : null,
                    ts: item.messageTimestamp,
                    listo: this.ready,
                },
                'mensaje recibido',
            );
            if (item.key?.fromMe !== true) continue;
            if (this.queue.length + (this.busy ? 1 : 0) >= 8) break;
            const timestamp = Number(item.messageTimestamp);
            if (!Number.isFinite(timestamp) || timestamp < this.ready - 2 || timestamp > Date.now() / 1000 + 30) continue;
            const identities = [this.socket.user?.id, this.socket.user?.lid].map(normalizeJid).filter(Boolean);
            const input = this.parse(item, identities, this.audio);
            if (!input || (await this.store.known('out:' + item.key.id))) continue;
            const messageId = createHash('sha256').update(item.key.id).digest('hex');
            if (!(await this.store.claim('in:' + messageId))) continue;
            const identity = identities.find((value) => value.endsWith('@s.whatsapp.net')) ?? identities[0];
            this.queue.push({ ...input, id: messageId, jid: item.key.remoteJid, ids: stableIds(identity, item.key.id) });
        }
        if (!this.busy) {
            this.busy = true;
            this.drainPromise = this.drain()
                .catch((error) => logger.warn({ detalle: error?.message }, 'envío fallido'))
                .finally(() => {
                    this.busy = false;
                });
        }
    }

    async drain() {
        while (!this.closed && this.queue.length) {
            const item = this.queue.shift();
            const result = await ask({
                mensaje: item.text,
                session_id: item.ids.conversation_id,
                request_id: item.id,
            });
            if (this.closed) throw Error('transport_stopped');
            await this.store.alive();
            const id = generateMessageIDV2(this.socket.user?.id);
            if (!(await this.store.claim('out:' + id))) throw Error('outgoing_id_collision');
            await this.socket.sendMessage(item.jid, { text: result.respuesta }, { messageId: id });
            await this.store.done('out:' + id);
            await this.store.done('in:' + item.id);
        }
    }

    close() {
        if (this.closePromise) return this.closePromise;
        this.halt();
        this.closePromise = (async () => {
            const results = await Promise.allSettled([this.opening, this.serial, this.drainPromise, this.authWrites]);
            if (this.store) await this.store.close();
            if (results.some((result) => result.status === 'rejected')) throw Error('transport_close_incomplete');
        })();
        return this.closePromise;
    }
}
