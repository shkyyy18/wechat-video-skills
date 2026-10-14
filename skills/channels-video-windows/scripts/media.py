#!/usr/bin/env python3
"""Verify local media or create a trimmed/cropped MP4 copy without overwriting sources."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

def require_tools(ffprobe='ffprobe', ffmpeg='ffmpeg'):
    for name in (ffprobe, ffmpeg):
        if not shutil.which(name):
            raise RuntimeError(f'Required executable unavailable: {Path(name).name}')

def run(command, timeout=600):
    try:
        r = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Media operation exceeded its time limit') from exc
    if r.returncode:
        raise RuntimeError('Media tool failed; inspect file, codecs, dimensions and tools locally')
    return r.stdout

def probe(path, ffprobe='ffprobe'):
    result = json.loads(run([ffprobe, '-v', 'error', '-protocol_whitelist', 'file,pipe',
                            '-show_streams', '-show_format', '-of', 'json', str(path)], 30))
    duration = float(result.get('format', {}).get('duration', 0))
    video = [s for s in result.get('streams', []) if s.get('codec_type') == 'video']
    audio = [s for s in result.get('streams', []) if s.get('codec_type') == 'audio']
    if not math.isfinite(duration) or duration <= 0 or not video:
        raise RuntimeError('Missing video or positive finite duration')
    return result, duration, video, audio

def verify_media(path, ffprobe='ffprobe', ffmpeg='ffmpeg'):
    path = Path(path).resolve(strict=True)
    require_tools(ffprobe, ffmpeg)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError('Empty media file')
    _, duration, video, audio = probe(path, ffprobe)
    run([ffmpeg, '-nostdin', '-v', 'error', '-xerror', '-protocol_whitelist', 'file,pipe',
         '-i', str(path), '-map', '0:v:0', '-map', '0:a?', '-f', 'null', '-'])
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            digest.update(block)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest(),
            'duration_seconds': duration, 'width': video[0].get('width'), 'height': video[0].get('height'),
            'audio_tracks': len(audio), 'decode': 'passed',
            'audio_notice': 'Track presence does not prove audible sound or synchronization'}

def finalize(source, destination, start=0, duration=None, crop=None, ffprobe='ffprobe', ffmpeg='ffmpeg'):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).expanduser().absolute()
    if not destination.parent.is_dir() or destination.suffix.lower() != '.mp4':
        raise ValueError('Output must be an MP4 in an existing directory')
    if destination.exists() or destination.resolve() == source:
        raise ValueError('Output already exists; choose a new filename')
    require_tools(ffprobe, ffmpeg)
    _, total, video, audio = probe(source, ffprobe)
    if not audio:
        raise ValueError('Recording has no audio track; fix application audio before delivery')
    if not math.isfinite(start) or start < 0 or start >= total:
        raise ValueError('Start is outside media duration')
    if duration is not None and (not math.isfinite(duration) or duration <= 0 or start+duration > total+.05):
        raise ValueError('Requested duration is outside source bounds')
    if crop:
        values = crop.split(':')
        if len(values) != 4 or not all(x.isdecimal() for x in values):
            raise ValueError('Crop must be width:height:x:y in integer pixels')
        w, h, x, y = map(int, values)
        if w <= 0 or h <= 0 or w%2 or h%2 or x+w > video[0]['width'] or y+h > video[0]['height']:
            raise ValueError('Crop must fit source and use even positive width/height')
        video_filter = 'crop='+crop
    else:
        video_filter = 'pad=ceil(iw/2)*2:ceil(ih/2)*2'
    command = [ffmpeg, '-nostdin', '-v', 'error', '-n', '-protocol_whitelist', 'file,pipe',
               '-ss', str(start), '-i', str(source)]
    if duration is not None:
        command += ['-t', str(duration)]
    command += ['-map', '0:v:0', '-map', '0:a', '-vf', video_filter,
                '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                '-movflags', '+faststart', str(destination)]
    run(command)
    result = verify_media(destination, ffprobe, ffmpeg)
    expected = duration if duration is not None else total-start
    if abs(result['duration_seconds']-expected) > .5:
        raise RuntimeError('Output duration differs from requested range; retain source and inspect output')
    result.update(mode='recording-copy', source_preserved=True)
    return result

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('--output', help='New MP4 path; omitted means read-only verification')
    p.add_argument('--start', type=float, default=0)
    p.add_argument('--duration', type=float)
    p.add_argument('--crop', help='width:height:x:y; even width/height, inside source')
    p.add_argument('--ffprobe', default='ffprobe')
    p.add_argument('--ffmpeg', default='ffmpeg')
    a = p.parse_args(argv)
    try:
        if a.output:
            result = finalize(a.source, a.output, a.start, a.duration, a.crop, a.ffprobe, a.ffmpeg)
        else:
            if a.start or a.duration is not None or a.crop:
                raise ValueError('Trim/crop options require --output')
            result = verify_media(a.source, a.ffprobe, a.ffmpeg)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (RuntimeError, ValueError, OSError) as exc:
        print(json.dumps({'state': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
