from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
ROOT = Path(__file__).resolve().parents[1]
class Packages(unittest.TestCase):
    def test_archives_are_independent_and_cli_loads(self):
        for system in ('macos','windows'):
            name = 'channels-video-'+system
            version = json.loads((ROOT/'skills'/name/'manifest.json').read_text())['version']
            archive = ROOT/'dist'/(name+'-'+version+'.zip')
            with self.subTest(system=system), tempfile.TemporaryDirectory() as temp:
                with zipfile.ZipFile(archive) as z: z.extractall(temp)
                skill = Path(temp)/name
                self.assertTrue((skill/'SKILL.md').exists())
                self.assertEqual((skill/'scripts/record.mjs').exists(), system=='windows')
                for script in ['download.py','media.py','douyin.py']:
                    result = subprocess.run([sys.executable, str(skill/'scripts'/script), '--help'], capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
    def test_manifest_hashes(self):
        for system in ('macos','windows'):
            folder = ROOT/'skills'/('channels-video-'+system)
            manifest = json.loads((folder/'manifest.json').read_text())
            for name,digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(), digest)
    def test_packaging_reproducible(self):
        before = (ROOT/'dist/SHA256SUMS').read_bytes()
        result = subprocess.run([sys.executable,str(ROOT/'tools/build.py')],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,(ROOT/'dist/SHA256SUMS').read_bytes())
    def test_publication_static_audit(self):
        result = subprocess.run([sys.executable,str(ROOT/'tools/audit.py')],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
if __name__ == '__main__': unittest.main()
