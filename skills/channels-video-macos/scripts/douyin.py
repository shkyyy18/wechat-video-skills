#!/usr/bin/env python3
"""Save an observed Douyin player media URL or ingest its browser-downloaded file.

An authorized browser must resolve the page first. This is not a share-link resolver.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from media import require_tools, verify_media

MAX_BYTES = 2 * 1024**3
STATUSES = ('available', 'explicitly_disabled', 'not_observed')

def media_address(value, video_id):
    try:
        parsed = urllib.parse.urlsplit(value)
        host = parsed.hostname or ''
        port = parsed.port
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid observed media address') from exc
    if (parsed.scheme != 'https' or not host.endswith('.douyinvod.com')
            or parsed.username or parsed.password or port not in (None, 443)):
        raise ValueError('Expected an observed HTTPS douyinvod.com media address')
    ids = urllib.parse.parse_qs(parsed.query).get('__vid', [])
    if ids != [video_id]:
        raise ValueError('Player media ID does not match the canonical video page')
    return value

def validate_evidence(data):
    if not isinstance(data, dict):
        raise ValueError('Evidence must be a JSON object')
    url = data.get('source_url', '')
    match = re.fullmatch(r'https://www\.douyin\.com/video/([0-9]{10,24})', url)
    if not match:
        raise ValueError('Provide the canonical HTTPS Douyin video page from the browser')
    if data.get('ui_download_status') not in STATUSES:
        raise ValueError('Invalid UI download status; use not_observed when unknown')
    if not isinstance(data.get('ui_evidence'), str) or not data['ui_evidence'].strip():
        raise ValueError('Describe the observed download control or absence of evidence')
    if not isinstance(data.get('title'), str) or not data['title'].strip():
        raise ValueError('Provide the observed page title')
    duration = data.get('duration_seconds')
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Provide the positive finite player duration in seconds')
    if data.get('access_gate') != 'none':
        raise ValueError('Stop at login, CAPTCHA, paywall or access-denial gates')
    media_address(data.get('media_url', ''), match[1])
    return match[1], duration

class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, video_id):
        self.video_id = video_id
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        media_address(newurl, self.video_id)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def transfer(data, stream, video_id, timeout=120):
    opener = urllib.request.build_opener(CheckedRedirect(video_id))
    request = urllib.request.Request(data['media_url'], headers={
        'Referer': data['source_url'], 'User-Agent': 'Mozilla/5.0'})
    start = time.monotonic()
    with opener.open(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError('Media response was not a complete HTTP 200 file')
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/' in content_type or 'json' in content_type:
            raise RuntimeError('Media endpoint returned a page instead of video')
        length = response.headers.get('Content-Length')
        if length and (not length.isdecimal() or int(length) > MAX_BYTES):
            raise RuntimeError('Media Content-Length is invalid or exceeds 2 GiB')
        total = 0
        while True:
            block = response.read(1024 * 1024)
            if time.monotonic()-start > timeout:
                raise RuntimeError('Media transfer deadline exceeded')
            if not block:
                break
            total += len(block)
            if total > MAX_BYTES:
                raise RuntimeError('Media exceeds 2 GiB')
            stream.write(block)
        if not total or (length and total != int(length)):
            raise RuntimeError('Incomplete media response')

def save(data, output, browser_file=None, ffprobe='ffprobe', ffmpeg='ffmpeg'):
    video_id, duration = validate_evidence(data)
    output = Path(output).expanduser()
    if not output.is_absolute() or output.suffix.lower() != '.mp4':
        raise ValueError('Output must be an absolute new MP4 path')
    if output.exists() or output.is_symlink():
        raise ValueError('Output exists; choose a new filename')
    require_tools(ffprobe, ffmpeg)
    source = None
    if browser_file:
        source = Path(browser_file).resolve(strict=True)
        if not source.is_file() or source.stat().st_size > MAX_BYTES:
            raise ValueError('Browser file invalid or larger than 2 GiB')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.wesave-', suffix='.mp4', dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            if source:
                with source.open('rb') as incoming:
                    shutil.copyfileobj(incoming, stream)
            else:
                transfer(data, stream, video_id)
        result = verify_media(temporary, ffprobe, ffmpeg)
        if result['audio_tracks'] < 1:
            raise RuntimeError('No audio track; do not deliver as a complete audiovisual video')
        if abs(result['duration_seconds']-duration) > max(.5, duration*.01):
            raise RuntimeError('Saved media duration does not match the observed player')
        # Atomic, exclusive publication: a race must never replace an existing file.
        os.link(temporary, output)
        result.update(path=str(output.resolve()), platform='douyin', mode='browser-media-download',
                      source_url=data['source_url'], video_id=video_id,
                      ui_download_status=data['ui_download_status'], ui_evidence=data['ui_evidence'],
                      original_download_preserved=bool(source), listening_review='pending',
                      author_permission_inferred=False)
        return result
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, help='Local browser observation JSON; never commit it')
    parser.add_argument('--browser-file', help='Optional file returned by the browser download tool; source preserved')
    parser.add_argument('--output', required=True, help='Absolute new MP4 path; never overwritten')
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.evidence).read_text(encoding='utf-8-sig'))
        result = save(data, args.output, args.browser_file, args.ffprobe, args.ffmpeg)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        # Network exceptions may contain signed URLs; do not echo them into shared logs.
        text = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else 'File or network operation failed; inspect locally'
        print(json.dumps({'state': 'error', 'message': text}), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted; no verified output was published.', file=sys.stderr)
        return 130

if __name__ == '__main__':
    sys.exit(main())
