import { readFile } from 'node:fs/promises';
import { ObsClient, recordFor } from './obs.mjs';
const [configPath, secondsText, scene, profile, ...extra] = process.argv.slice(2);
let client;
const controller = new AbortController();
const interrupt = () => controller.abort();
try {
  if (!configPath || !scene || !profile || extra.length || !Number.isFinite(Number(secondsText)) ||
      Number(secondsText) < 1 || Number(secondsText) > 14400) {
    throw new Error('Usage: node record.mjs CONFIG_JSON SECONDS SCENE PROFILE (1..14400 seconds)');
  }
  const config = JSON.parse((await readFile(configPath, 'utf8')).replace(/^\uFEFF/, ''));
  process.once('SIGINT', interrupt); process.once('SIGTERM', interrupt);
  client = await ObsClient.connect(config);
  const result = await recordFor(client, { seconds: Number(secondsText), scene, profile, signal: controller.signal });
  console.log(JSON.stringify(result));
} catch (e) {
  console.error(JSON.stringify({ state: 'error', message: e.message }));
  process.exitCode = controller.signal.aborted ? 130 : 1;
} finally {
  process.removeListener('SIGINT', interrupt); process.removeListener('SIGTERM', interrupt);
  client?.close();
}
