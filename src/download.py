#!/usr/bin/env python3
"""Local wx_channels_download v260907 adapter; Python 3.10+, standard library."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from media import verify_media, require_tools

class WorkflowError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise WorkflowError('Local API redirected; refusing to follow it')

def local_endpoint(value):
    try:
        p = urllib.parse.urlsplit(value)
        port = p.port
    except ValueError as exc:
        raise WorkflowError('Invalid API address') from exc
    if (p.scheme != 'http' or p.hostname not in ('127.0.0.1', '::1')
            or p.username or p.password or p.path not in ('', '/') or p.query or p.fragment
            or port is None or not 1 <= port <= 65535):
        raise WorkflowError('API must be http://127.0.0.1:PORT or http://[::1]:PORT')
    return value.rstrip('/')

def share_url(value):
    try:
        p = urllib.parse.urlsplit(value)
        port = p.port
    except ValueError as exc:
        raise WorkflowError('Invalid share URL') from exc
    if (p.scheme != 'https' or p.hostname not in ('weixin.qq.com', 'channels.weixin.qq.com')
            or p.username or p.password or port not in (None, 443) or p.path in ('', '/')):
        raise WorkflowError('Expected a HTTPS WeChat Channels share URL')
    return value

def unwrap(payload):
    if not isinstance(payload, dict) or type(payload.get('code')) is not int or payload['code'] != 0:
        raise WorkflowError('Local API business error or incompatible response')
    data = payload.get('data')
    if not isinstance(data, dict):
        raise WorkflowError('Missing API data object')
    cursor = data
    for _ in range(4):
        if not isinstance(cursor, dict):
            break
        for key in ('errCode', 'err_code', 'code'):
            if key in cursor and cursor[key] != 0:
                raise WorkflowError('WeChat fetch returned a business error')
        cursor = cursor.get('data')
    return data

class Client:
    def __init__(self, endpoint='http://127.0.0.1:2022', request_timeout=20):
        self.endpoint = local_endpoint(endpoint)
        self.request_timeout = request_timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, path, body=None, query=None, timeout=None):
        url = self.endpoint + path
        if query:
            url += '?' + urllib.parse.urlencode(query)
        data = None if body is None else json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(req, timeout=timeout or self.request_timeout) as response:
                raw = response.read(8*1024*1024+1)
                if len(raw) > 8*1024*1024:
                    raise WorkflowError('API response exceeds 8 MiB')
                return unwrap(json.loads(raw))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise WorkflowError('Local API unavailable or invalid JSON; inspect runtime locally') from exc

    def create(self, url, directory):
        content = self.call('/api/channels/parse_sph', query={'url': share_url(url)})
        # Never retry creation: a lost response may still have created a task.
        try:
            result = self.call('/api/v1/download_task/create', {'objects': [{
                'platform': 'wxchannels', 'content': content, 'build_from_fetch': True,
                'download_dir': str(directory), 'config': {'existing_action': 'skip'},
                'auto_start': True}]})
        except WorkflowError as exc:
            raise WorkflowError('Create response unavailable. Inspect runtime task list before retrying; a task may exist') from exc
        tasks = result.get('tasks')
        if not isinstance(tasks, list) or len(tasks) != 1:
            raise WorkflowError('Unexpected create result; inspect task list before retrying')
        task = tasks[0]
        if not isinstance(task, dict) or type(task.get('code')) is not int or task['code'] != 0:
            raise WorkflowError('Download task rejected; no automatic retry')
        data = task.get('data')
        task_id = data.get('id') if isinstance(data, dict) else None
        if type(task_id) is not int or task_id <= 0:
            raise WorkflowError('Missing task ID; inspect task list before retrying')
        return task_id

    def wait(self, task_id, timeout=600, poll=2):
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise WorkflowError(f'Task {task_id} pending; use --resume-id {task_id}. Runtime task was not cancelled')
            task = self.call('/api/v1/download_task/detail', query={'id': task_id},
                             timeout=min(self.request_timeout, remaining))
            status = task.get('status')
            if type(status) is not int or status not in range(8):
                raise WorkflowError(f'Task {task_id}: unsupported status')
            if status == 5:
                return task
            if status in (3, 6, 7):
                label = {3: 'paused', 6: 'failed', 7: 'cancelled'}[status]
                raise WorkflowError(f'Task {task_id} {label}; inspect runtime locally')
            time.sleep(min(poll, max(0, deadline-time.monotonic())))

def task_files(task, directory):
    root = Path(directory).resolve(strict=True)
    entries = task.get('files')
    if not isinstance(entries, list):
        raise WorkflowError('Missing task files')
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkflowError('Invalid task file record')
        if entry.get('file_type') != 'video':
            continue
        value = entry.get('local_path') or entry.get('file_path')
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise WorkflowError('Invalid video path')
        try:
            path = Path(value).resolve(strict=True)
        except OSError as exc:
            raise WorkflowError('Runtime reported completion but file is missing') from exc
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size == 0:
            raise WorkflowError('Video empty or outside authorized output directory')
        if path.suffix.lower() not in ('.mp4', '.mkv', '.mov', '.webm', '.m4v'):
            raise WorkflowError('Unsupported media container')
        if path not in result:
            result.append(path)
    if not result:
        raise WorkflowError('No local video files in completed task')
    return result

def number(value, lower, upper):
    result = float(value)
    if not math.isfinite(result) or not lower <= result <= upper:
        raise argparse.ArgumentTypeError(f'Expected {lower} to {upper}')
    return result

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--url', help='Authorized HTTPS WeChat Channels share URL')
    g.add_argument('--resume-id', type=int, help='Poll existing task; no new download')
    p.add_argument('--out-dir', required=True, help='Absolute local directory')
    p.add_argument('--api', default='http://127.0.0.1:2022')
    p.add_argument('--timeout', type=lambda s: number(s, 1, 86400), default=600,
                   help='Polling seconds, default 600; creation/media validation have separate limits')
    p.add_argument('--poll', type=lambda s: number(s, .1, 60), default=2)
    p.add_argument('--ffprobe', default='ffprobe')
    p.add_argument('--ffmpeg', default='ffmpeg')
    a = p.parse_args(argv)
    try:
        directory = Path(a.out_dir).expanduser()
        if not directory.is_absolute():
            raise WorkflowError('--out-dir must be absolute')
        if a.resume_id is not None and a.resume_id <= 0:
            raise WorkflowError('--resume-id must be positive')
        client = Client(a.api)
        if a.url:
            share_url(a.url)
        require_tools(a.ffprobe, a.ffmpeg)
        directory.mkdir(parents=True, exist_ok=True)
        directory = directory.resolve()
        task_id = a.resume_id or client.create(a.url, directory)
        print(json.dumps({'task_id': task_id, 'state': 'polling'}), flush=True)
        task = client.wait(task_id, a.timeout, a.poll)
        outputs = [verify_media(path, a.ffprobe, a.ffmpeg) for path in task_files(task, directory)]
        print(json.dumps({'state': 'verified', 'mode': 'download', 'task_id': task_id,
                          'files': outputs, 'subjective_playback_review': 'pending'}, ensure_ascii=False))
        return 0
    except (WorkflowError, ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({'state': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted. Upstream task may continue; inspect it before retrying.', file=sys.stderr)
        return 130

if __name__ == '__main__':
    sys.exit(main())
