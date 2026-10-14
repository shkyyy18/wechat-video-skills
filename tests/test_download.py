import contextlib
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from download import Client, WorkflowError, local_endpoint, share_url, unwrap, task_files, number

@contextlib.contextmanager
def server(reply):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.path, None)); self.respond()
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.command, self.path, body)); self.respond()
        def respond(self):
            status, payload, headers = reply(requests[-1])
            self.send_response(status)
            for key, value in headers.items(): self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        def log_message(self, *_): pass
    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    try: yield Client('http://127.0.0.1:'+str(http.server_port)), requests
    finally: http.shutdown(); http.server_close(); thread.join()

class ContractTests(unittest.TestCase):
    def test_loopback_only(self):
        for url in ['https://127.0.0.1:2022', 'http://localhost:2022', 'http://example.com:2022',
                    'http://127.0.0.1:2022/api', 'http://user:pass@127.0.0.1:2022',
                    'http://127.0.0.1:2022?token=x', 'http://127.0.0.1:0', 'http://127.0.0.1:bad']:
            with self.subTest(url=url), self.assertRaises(WorkflowError): local_endpoint(url)
        self.assertEqual(local_endpoint('http://[::1]:2022/'), 'http://[::1]:2022')

    def test_share_url_validation(self):
        for url in ['https://example.com/video.mp4', 'https://weixin.qq.com.evil.test/sph/a',
                    'http://weixin.qq.com/sph/a', 'https://user:pass@weixin.qq.com/sph/a']:
            with self.subTest(url=url), self.assertRaises(WorkflowError): share_url(url)
        self.assertEqual(share_url('https://weixin.qq.com/sph/synthetic'), 'https://weixin.qq.com/sph/synthetic')

    def test_business_errors(self):
        for payload in [{}, [], {'code': True, 'data': {}}, {'code': 500, 'data': {}},
                        {'code': 0, 'data': None}, {'code': 0, 'data': {'errCode': 7}},
                        {'code': 0, 'data': {'data': {'err_code': 1}}}]:
            with self.subTest(payload=payload), self.assertRaises(WorkflowError): unwrap(payload)

    def test_success_unwrap_preserves_fetch_shape(self):
        data = {'errCode': 0, 'data': {'object': {'id': 'synthetic'}}}
        self.assertIs(unwrap({'code': 0, 'data': data}), data)

    def test_real_http_contract_and_single_create(self):
        def reply(req):
            method, path, body = req
            if path.startswith('/api/channels/parse_sph?'):
                return 200, {'code': 0, 'data': {'object': {'id': 'synthetic'}}}, {}
            if path == '/api/v1/download_task/create':
                obj = body['objects'][0]
                self.assertEqual(obj['platform'], 'wxchannels')
                self.assertTrue(obj['build_from_fetch']); self.assertTrue(obj['auto_start'])
                self.assertEqual(obj['config'], {'existing_action': 'skip'})
                return 200, {'code': 0, 'data': {'tasks': [{'code': 0, 'data': {'id': 42}}]}}, {}
            return 200, {'code': 0, 'data': {'status': 5, 'files': []}}, {}
        with server(reply) as (client, requests):
            task_id = client.create('https://weixin.qq.com/sph/synthetic', Path.cwd())
            self.assertEqual(task_id, 42); self.assertEqual(client.wait(task_id)['status'], 5)
            self.assertEqual(sum(r[0] == 'POST' for r in requests), 1)
            self.assertIn('/api/v1/download_task/detail?id=42', [r[1] for r in requests])

    def test_redirect_not_followed(self):
        with server(lambda _: (302, b'', {'Location': 'http://example.invalid/private'})) as (c, requests):
            with self.assertRaises(WorkflowError): c.call('/api/status')
            self.assertEqual(len(requests), 1)

    def test_invalid_json(self):
        with server(lambda _: (200, b'not json', {})) as (c, _):
            with self.assertRaises(WorkflowError): c.call('/api/status')

    def test_http_200_failure(self):
        with server(lambda _: (200, {'code': 500, 'msg': 'private detail'}, {})) as (c, _):
            with self.assertRaisesRegex(WorkflowError, 'business error'): c.call('/api/status')

    def test_per_item_failure(self):
        c = Client(); c.call = Mock(side_effect=[{}, {'tasks': [{'code': 400, 'data': {}}]}])
        with self.assertRaisesRegex(WorkflowError, 'rejected'): c.create('https://weixin.qq.com/sph/synthetic', Path.cwd())
        self.assertEqual(c.call.call_count, 2)

    def test_lost_create_response_not_retried(self):
        c = Client(); c.call = Mock(side_effect=[{}, WorkflowError('disconnected')])
        with self.assertRaisesRegex(WorkflowError, 'may exist'): c.create('https://weixin.qq.com/sph/synthetic', Path.cwd())
        self.assertEqual(c.call.call_count, 2)

    def test_missing_task_id(self):
        c = Client(); c.call = Mock(side_effect=[{}, {'tasks': [{'code': 0, 'data': None}]}])
        with self.assertRaises(WorkflowError): c.create('https://weixin.qq.com/sph/synthetic', Path.cwd())

    def test_failure_and_unknown_states(self):
        for status in [3, 6, 7, 8, None, True]:
            c = Client(); c.call = Mock(return_value={'status': status})
            with self.subTest(status=status), self.assertRaises(WorkflowError): c.wait(42)
            self.assertEqual(c.call.call_count, 1)

    def test_pending_timeout_no_create(self):
        c = Client(); c.call = Mock(return_value={'status': 2})
        with self.assertRaisesRegex(WorkflowError, '--resume-id 42'): c.wait(42, .01, .01)
        self.assertTrue(all(x.args[0].endswith('/detail') for x in c.call.call_args_list))

    def test_poll_progress(self):
        c = Client(); c.call = Mock(side_effect=[{'status': 1}, {'status': 4}, {'status': 5}])
        with patch('download.time.sleep'): self.assertEqual(c.wait(42)['status'], 5)

    def test_file_containment_and_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); out = base/'out'; out.mkdir(); good = out/'video.mp4'; good.write_bytes(b'synthetic')
            def task(path): return {'files': [{'file_type': 'video', 'local_path': str(path)}]}
            self.assertEqual(task_files(task(good), out), [good.resolve()])
            outside = base/'outside.mp4'; outside.write_bytes(b'not allowed')
            empty = out/'empty.mp4'; empty.touch()
            for p in [outside, out/'missing.mp4', empty, Path('relative.mp4')]:
                with self.subTest(path=p), self.assertRaises(WorkflowError): task_files(task(p), out)

    def test_no_video(self):
        with tempfile.TemporaryDirectory() as temp:
            for files in [[], None, ['bad'], [{'file_type': 'audio'}]]:
                with self.subTest(files=files), self.assertRaises(WorkflowError): task_files({'files': files}, temp)

    def test_numeric_bounds(self):
        for value in ['nan', 'inf', '0', '86401']:
            with self.subTest(value=value), self.assertRaises(Exception): number(value, 1, 86400)
        self.assertEqual(number('600', 1, 86400), 600)

if __name__ == '__main__': unittest.main()
