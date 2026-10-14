import { createHash, randomUUID } from 'node:crypto';

export class ObsClient {
  constructor(ws, timeoutMs = 20000) {
    this.ws = ws; this.timeoutMs = timeoutMs; this.pending = new Map();
    ws.addEventListener('message', event => {
      let message;
      try { message = JSON.parse(event.data); }
      catch { this.fail(new Error('Invalid OBS JSON')); ws.close(); return; }
      if (message?.op !== 7) return;
      const d = message.d;
      const item = this.pending.get(d?.requestId);
      if (!item) return;
      this.pending.delete(d.requestId); clearTimeout(item.timer);
      if (d.requestStatus?.result === true) item.resolve(d.responseData ?? {});
      else item.reject(new Error('OBS request rejected: ' + item.type));
    });
    ws.addEventListener('close', () => this.fail(new Error('OBS connection closed')));
    ws.addEventListener('error', () => this.fail(new Error('OBS connection error')));
  }
  fail(error) {
    for (const item of this.pending.values()) { clearTimeout(item.timer); item.reject(error); }
    this.pending.clear();
  }
  static async connect(config, { WebSocketImpl = WebSocket, timeoutMs = 12000 } = {}) {
    if (!Number.isInteger(config.server_port) || config.server_port < 1 || config.server_port > 65535 ||
        typeof config.server_password !== 'string' || !config.server_password.length) {
      throw new Error('OBS config requires server_port and nonempty server_password');
    }
    const ws = new WebSocketImpl('ws://127.0.0.1:' + config.server_port);
    const client = new ObsClient(ws);
    try {
      await new Promise((resolve, reject) => {
        const finish = error => {
          clearTimeout(timer);
          ws.removeEventListener('message', receive);
          ws.removeEventListener('error', fail);
          ws.removeEventListener('close', fail);
          error ? reject(error) : resolve();
        };
        const fail = () => finish(new Error('OBS handshake failed'));
        const receive = event => {
          try {
            const m = JSON.parse(event.data);
            if (m?.op === 0) {
              const auth = m.d?.authentication;
              if (typeof auth?.salt !== 'string' || typeof auth?.challenge !== 'string') {
                throw new Error('OBS authentication must be enabled');
              }
              const hash = s => createHash('sha256').update(s).digest('base64');
              const authentication = hash(hash(config.server_password + auth.salt) + auth.challenge);
              ws.send(JSON.stringify({ op: 1, d: { rpcVersion: 1, eventSubscriptions: 0, authentication } }));
            } else if (m?.op === 2) finish();
          } catch (e) { finish(e); }
        };
        const timer = setTimeout(() => finish(new Error('OBS handshake timeout')), timeoutMs);
        ws.addEventListener('message', receive);
        ws.addEventListener('error', fail);
        ws.addEventListener('close', fail);
      });
      return client;
    } catch (e) { ws.close(); throw e; }
  }
  request(type, requestData = {}) {
    const id = randomUUID();
    return new Promise((resolve, reject) => {
      if (this.ws.readyState !== 1) { reject(new Error('OBS socket is not open')); return; }
      const timer = setTimeout(() => {
        this.pending.delete(id); reject(new Error('OBS request timeout: ' + type));
      }, this.timeoutMs);
      this.pending.set(id, { resolve, reject, timer, type });
      try { this.ws.send(JSON.stringify({ op: 6, d: { requestType: type, requestId: id, requestData } })); }
      catch { clearTimeout(timer); this.pending.delete(id); reject(new Error('OBS send failed')); }
    });
  }
  close() { this.fail(new Error('OBS client closed')); this.ws.close(); }
}

export async function recordFor(client, { seconds, scene, profile, signal, wait } = {}) {
  if (!Number.isFinite(seconds) || seconds < 1 || seconds > 14400 || !scene || !profile) {
    throw new Error('Recording requires seconds 1..14400 and dedicated scene/profile names');
  }
  if (signal?.aborted) throw new Error('Recording cancelled before start');
  const current = await client.request('GetCurrentProgramScene');
  const profiles = await client.request('GetProfileList');
  if (current.currentProgramSceneName !== scene || profiles.currentProfileName !== profile) {
    throw new Error('Dedicated OBS scene/profile must be selected before recording');
  }
  if ((await client.request('GetRecordStatus')).outputActive) throw new Error('OBS already recording');
  if (signal?.aborted) throw new Error('Recording cancelled before start');
  let mayHaveStarted = false;
  let output;
  try {
    mayHaveStarted = true; // A lost start reply is ambiguous; stop in finally.
    await client.request('StartRecord');
    if (signal?.aborted) throw new Error('Recording interrupted');
    const waitForTimer = wait ?? ((ms, abortSignal) => new Promise((resolve, reject) => {
      const onAbort = () => { cleanup(); reject(new Error('Recording interrupted')); };
      const timer = setTimeout(() => { cleanup(); resolve(); }, ms);
      const cleanup = () => { clearTimeout(timer); abortSignal?.removeEventListener('abort', onAbort); };
      abortSignal?.addEventListener('abort', onAbort, { once: true });
      if (abortSignal?.aborted) onAbort();
    }));
    await waitForTimer(seconds * 1000, signal);
  } finally {
    if (mayHaveStarted) {
      try { output = await client.request('StopRecord'); }
      catch { throw new Error('Cannot confirm recording stopped. Stop it in OBS now and preserve the MKV'); }
    }
  }
  if (!output?.outputPath) throw new Error('OBS stopped but returned no output path; inspect recordings folder');
  return { mode: 'recording-copy', path: output.outputPath, verification: 'pending' };
}
