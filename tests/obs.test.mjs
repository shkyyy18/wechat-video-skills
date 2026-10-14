import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { ObsClient, recordFor } from '../src/obs.mjs';

class FakeSocket extends EventTarget {
  readyState = 1; sent = [];
  constructor(url) { super(); this.url = url; }
  send(text) { this.sent.push(JSON.parse(text)); }
  message(value) { this.dispatchEvent(new MessageEvent('message', { data: typeof value === 'string' ? value : JSON.stringify(value) })); }
  close() { this.readyState = 3; this.dispatchEvent(new Event('close')); }
}
class HandshakeSocket extends FakeSocket {
  static last;
  constructor(url) { super(url); HandshakeSocket.last = this; queueMicrotask(() => this.message({ op: 0, d: { authentication: { salt: 's', challenge: 'c' } } })); }
  send(text) { super.send(text); queueMicrotask(() => this.message({ op: 2, d: { negotiatedRpcVersion: 1 } })); }
}
function recorder(overrides = {}) {
  const calls = [];
  const responses = { GetCurrentProgramScene: { currentProgramSceneName: 'scene' }, GetProfileList: { currentProfileName: 'profile' },
    GetRecordStatus: { outputActive: false }, StartRecord: {}, StopRecord: { outputPath: '/synthetic/video.mkv' }, ...overrides };
  return { calls, async request(type) { calls.push(type); const r = responses[type]; if (r instanceof Error) throw r; return r; } };
}
const options = { seconds: 1, scene: 'scene', profile: 'profile', wait: async () => {} };

test('authenticated loopback handshake computes the protocol hash', async () => {
  const client = await ObsClient.connect({ server_port: 4455, server_password: 'synthetic-password' }, { WebSocketImpl: HandshakeSocket });
  const hash = s => createHash('sha256').update(s).digest('base64');
  assert.equal(HandshakeSocket.last.url, 'ws://127.0.0.1:4455');
  assert.equal(HandshakeSocket.last.sent[0].d.authentication, hash(hash('synthetic-password'+'s')+'c'));
  client.close();
});
test('empty password and invalid port fail before connection', async () => {
  await assert.rejects(ObsClient.connect({ server_port: 4455, server_password: '' }));
  await assert.rejects(ObsClient.connect({ server_port: -1, server_password: 'synthetic' }));
});
test('handshake timeout closes socket', async () => {
  class Silent extends FakeSocket { static last; constructor(url) { super(url); Silent.last = this; } }
  await assert.rejects(ObsClient.connect({ server_port: 4455, server_password: 'synthetic' }, { WebSocketImpl: Silent, timeoutMs: 5 }), /timeout/);
  assert.equal(Silent.last.readyState, 3);
});
test('unauthenticated OBS is rejected', async () => {
  class Unauthenticated extends FakeSocket { constructor(url) { super(url); queueMicrotask(() => this.message({ op: 0, d: {} })); } }
  await assert.rejects(ObsClient.connect({ server_port: 4455, server_password: 'synthetic' }, { WebSocketImpl: Unauthenticated }), /authentication/);
});
test('responses matched by request ID', async () => {
  const ws = new FakeSocket(); const client = new ObsClient(ws); const p = client.request('GetVersion');
  ws.message({ op: 7, d: { requestId: ws.sent[0].d.requestId, requestStatus: { result: true }, responseData: { version: 'synthetic' } } });
  assert.deepEqual(await p, { version: 'synthetic' }); client.close();
});
test('malformed JSON rejects pending operations', async () => {
  const ws = new FakeSocket(); const client = new ObsClient(ws); const p = client.request('GetVersion');
  ws.message('{invalid'); await assert.rejects(p, /Invalid OBS JSON/); assert.equal(client.pending.size, 0);
});
test('disconnect and send failure clear pending requests', async () => {
  const ws = new FakeSocket(); const client = new ObsClient(ws); const p = client.request('GetVersion');
  ws.close(); await assert.rejects(p, /closed/);
  const ws2 = new FakeSocket(); ws2.send = () => { throw new Error('failure'); }; const c2 = new ObsClient(ws2);
  await assert.rejects(c2.request('GetVersion'), /send failed/); assert.equal(c2.pending.size, 0); c2.close();
});
test('bounded request timeout', async () => {
  const client = new ObsClient(new FakeSocket(), 5); await assert.rejects(client.request('GetVersion'), /timeout/); client.close();
});
test('existing recording is never stopped', async () => {
  const client = recorder({ GetRecordStatus: { outputActive: true } });
  await assert.rejects(recordFor(client, options), /already recording/);
  assert(!client.calls.includes('StartRecord')); assert(!client.calls.includes('StopRecord'));
});
test('wrong scene/profile refuse starting', async () => {
  for (const overrides of [{ GetCurrentProgramScene: { currentProgramSceneName: 'other' } }, { GetProfileList: { currentProfileName: 'other' } }]) {
    const client = recorder(overrides); await assert.rejects(recordFor(client, options), /Dedicated/); assert(!client.calls.includes('StartRecord'));
  }
});
test('successful timer stops and returns recording-copy', async () => {
  const client = recorder(); const result = await recordFor(client, options);
  assert.equal(result.mode, 'recording-copy'); assert.equal(result.verification, 'pending');
  assert.deepEqual(client.calls.slice(-2), ['StartRecord', 'StopRecord']);
});
test('timer error still stops recording', async () => {
  const client = recorder(); await assert.rejects(recordFor(client, { ...options, wait: async () => { throw new Error('interrupted'); } }), /interrupted/);
  assert.equal(client.calls.at(-1), 'StopRecord');
});
test('lost start reply triggers cleanup', async () => {
  const client = recorder({ StartRecord: new Error('lost reply') });
  await assert.rejects(recordFor(client, options), /lost reply/); assert.equal(client.calls.at(-1), 'StopRecord');
});
test('unconfirmed stop tells user to stop OBS', async () => {
  const client = recorder({ StopRecord: new Error('disconnected') });
  await assert.rejects(recordFor(client, options), /Stop it in OBS now/);
});
test('abort before start never records', async () => {
  const controller = new AbortController(); controller.abort(); const client = recorder();
  await assert.rejects(recordFor(client, { ...options, signal: controller.signal }), /before start/); assert.equal(client.calls.length, 0);
});
test('invalid duration rejected', async () => {
  for (const seconds of [0, -1, Infinity, NaN, 14401]) await assert.rejects(recordFor(recorder(), { ...options, seconds }));
});
