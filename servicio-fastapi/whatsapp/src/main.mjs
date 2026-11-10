import { Gateway } from './gateway.mjs';
import { eligibleText } from './guard.mjs';
import { createInternalServer } from './server.mjs';

const secret = process.env.WHATSAPP_SECRET ?? '';
const port = Number(process.env.WHATSAPP_INTERNAL_PORT ?? 18081);

const createGateway = () =>
  new Gateway({
    parse: (item, identities) => {
      const text = eligibleText(item, identities);
      return text ? { kind: 'text', text } : null;
    },
  });

const { server, close } = createInternalServer({ createGateway, secret });
server.listen(port, '127.0.0.1', () => {
  // Sin contenido, credenciales ni códigos en registros.
  process.stdout.write(`whatsapp bridge listening on 127.0.0.1:${port}\n`);
});

for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => {
    server.close();
    void close().finally(() => process.exit(0));
    setTimeout(() => process.exit(1), 20000).unref();
  });
}
