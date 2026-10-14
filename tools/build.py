"""Build reproducible self-contained Skill ZIPs from an explicit allowlist."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-preview.1'
COMMON = ['download.py', 'media.py']
EXTRA = ['obs.mjs', 'record.mjs']

def build():
    dist = ROOT/'dist'
    dist.mkdir(exist_ok=True)
    hashes = []
    for system in ('macos', 'windows'):
        name = 'channels-video-'+system
        skill = ROOT/'skills'/name
        scripts = COMMON + (EXTRA if system == 'windows' else [])
        for script in scripts:
            (skill/'scripts'/script).write_bytes((ROOT/'src'/script).read_bytes())
        allowed = ['SKILL.md', 'LICENSE', 'references/setup.md', 'references/dependencies.md',
                   'references/api-contract.md'] + ['scripts/'+s for s in scripts]
        if system == 'windows':
            allowed.append('references/recording.md')
        manifest = {'version': VERSION, 'system': system, 'files': {
            p: hashlib.sha256((skill/p).read_bytes()).hexdigest() for p in sorted(allowed)}}
        (skill/'manifest.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))
        allowed.append('manifest.json')
        target = dist/(name+'-'+VERSION+'.zip')
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(allowed):
                info = zipfile.ZipInfo(name+'/'+p, (2026, 10, 14, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, (skill/p).read_bytes())
        hashes.append(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name)
    (dist/'SHA256SUMS').write_bytes(('\n'.join(hashes)+'\n').encode('ascii'))
    print('\n'.join(hashes))

if __name__ == '__main__':
    build()
