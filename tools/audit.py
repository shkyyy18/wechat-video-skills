"""Static publication/package audit. Does not certify rights, external rating or live compatibility."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {'README.md','README.en.md','LICENSE','THIRD_PARTY_NOTICES.md','SECURITY.md','CONTRIBUTING.md','CHANGELOG.md','.gitignore','.gitattributes'}
TOP_DIRS = {'src','skills','tools','tests','docs','site','.github'}
EXCLUDED = {'.runtime','dist','.git','__pycache__'}

def public_files():
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT)
        if any(x in EXCLUDED for x in rel.parts) or p.suffix == '.pyc': continue
        if p.is_file(): yield p

def audit():
    errors = []; count = 0
    for p in public_files():
        rel = p.relative_to(ROOT); count += 1
        if len(rel.parts) == 1 and rel.name not in TOP_FILES: errors.append(f'Unexpected root file: {rel}')
        if len(rel.parts) > 1 and rel.parts[0] not in TOP_DIRS: errors.append(f'Unexpected directory: {rel}')
        if p.is_symlink(): errors.append(f'Symlink in public tree: {rel}')
        try: text = p.read_text(encoding='utf-8')
        except UnicodeError: errors.append(f'Binary file in public tree: {rel}'); continue
        if '\x00' in text: errors.append(f'NUL byte: {rel}')
        # Runtime credentials/machine artifacts must not enter the clean snapshot.
        for pattern in [r'(?i)[a-z]:[/\\]Users[/\\](?!Public\b)[^\s/\\]+',
                        r'(?i)[a-z]:[/\\]AIWork[/\\]', r'gh[pousr]_[A-Za-z0-9]{30,}',
                        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']:
            if re.search(pattern, text): errors.append(f'Private path or secret marker: {rel}')
    for system in ('macos','windows'):
        name = 'channels-video-'+system; skill = ROOT/'skills'/name
        text = (skill/'SKILL.md').read_text(encoding='utf-8')
        if not text.startswith('---\nname: '+name+'\ndescription: '): errors.append(f'Skill frontmatter: {name}')
        manifest = json.loads((skill/'manifest.json').read_text(encoding='utf-8'))
        expected = set(manifest['files']) | {'manifest.json'}
        actual = {p.relative_to(skill).as_posix() for p in skill.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        if actual != expected: errors.append(f'Unexpected/missing packaged files: {name}')
        for rel, digest in manifest['files'].items():
            if hashlib.sha256((skill/rel).read_bytes()).hexdigest() != digest: errors.append(f'Manifest mismatch: {name}/{rel}')
            if rel.startswith('scripts/') and (skill/rel).read_bytes() != (ROOT/'src'/Path(rel).name).read_bytes(): errors.append(f'Stale packaged script: {name}/{rel}')
        archive = ROOT/'dist'/(name+'-'+manifest['version']+'.zip')
        with zipfile.ZipFile(archive) as z:
            names = set(z.namelist())
            if names != {name+'/'+p for p in expected}: errors.append(f'ZIP allowlist mismatch: {name}')
            for rel in expected:
                if z.read(name+'/'+rel) != (skill/rel).read_bytes(): errors.append(f'ZIP content mismatch: {name}/{rel}')
    for line in (ROOT/'dist/SHA256SUMS').read_text().splitlines():
        digest, filename = line.split('  ')
        if hashlib.sha256((ROOT/'dist'/filename).read_bytes()).hexdigest() != digest: errors.append(f'ZIP checksum mismatch: {filename}')
    if errors: raise RuntimeError('\n'.join(errors))
    print(json.dumps({'public_text_files': count, 'archives_verified': 2, 'static_audit': 'passed'}))

if __name__ == '__main__': audit()
