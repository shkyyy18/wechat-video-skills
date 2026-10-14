import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from media import finalize, verify_media, run
FFMPEG = os.environ.get('FFMPEG_PATH', 'ffmpeg')
FFPROBE = os.environ.get('FFPROBE_PATH', 'ffprobe')

class MediaGuards(unittest.TestCase):
    def test_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source.mkv'; source.write_bytes(b'original')
            target = Path(temp)/'output.mp4'; target.write_bytes(b'keep')
            with self.assertRaises(ValueError): finalize(source, target)
            self.assertEqual(target.read_bytes(), b'keep'); self.assertEqual(source.read_bytes(), b'original')

    def test_bad_ranges_and_crop(self):
        with tempfile.TemporaryDirectory() as temp, patch('media.require_tools'), patch('media.probe', return_value=({}, 10, [{'width': 100, 'height': 100}], [{}])):
            source = Path(temp)/'source.mkv'; source.write_bytes(b'original'); target = Path(temp)/'output.mp4'
            for options in [{'start': -1}, {'start': float('nan')}, {'duration': 11}, {'crop': '101:20:0:0'}, {'crop': '20:20:90:0'}, {'crop': '20:20:0;bad:0'}]:
                with self.subTest(options=options), self.assertRaises(ValueError): finalize(source, target, **options)
            self.assertFalse(target.exists())

    def test_missing_audio(self):
        with tempfile.TemporaryDirectory() as temp, patch('media.require_tools'), patch('media.probe', return_value=({}, 10, [{}], [])):
            source = Path(temp)/'source.mkv'; source.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError, 'audio'): finalize(source, Path(temp)/'out.mp4')

@unittest.skipUnless(shutil.which(FFMPEG) and shutil.which(FFPROBE), 'FFmpeg/ffprobe unavailable; live synthetic media gate pending')
class SyntheticMedia(unittest.TestCase):
    def test_real_encode_crop_decode_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'synthetic.mkv'; output = Path(temp)/'copy.mp4'
            run([FFMPEG, '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=25',
                 '-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=48000', '-t', '2',
                 '-c:v', 'libx264', '-c:a', 'aac', str(source)])
            before = verify_media(source, FFPROBE, FFMPEG)
            after = finalize(source, output, .2, 1, '160:120:0:0', FFPROBE, FFMPEG)
            self.assertEqual((after['width'], after['height']), (160, 120))
            self.assertEqual(after['audio_tracks'], 1); self.assertAlmostEqual(after['duration_seconds'], 1, delta=.15)
            self.assertEqual(before['sha256'], verify_media(source, FFPROBE, FFMPEG)['sha256'])
            self.assertEqual(after['mode'], 'recording-copy')

    def test_corrupt_file_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'bad.mp4'; path.write_bytes(b'not a video')
            with self.assertRaises(RuntimeError): verify_media(path, FFPROBE, FFMPEG)

if __name__ == '__main__': unittest.main()
