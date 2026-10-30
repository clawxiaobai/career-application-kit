#!/usr/bin/env python3
"""Portable, local-only job application workspace tools.

Standard library only (Python 3.10+). Commands:
  init      scaffold data/ from assets/scaffold and fill personal placeholders
  doctor    check Python and LaTeX/Poppler toolchain
  validate  check manifest, ledger references, placeholders, forbidden files
  status    de-duplicated application statistics
  prepare   copy a template into output/jobs/<slug> and fill header placeholders
  build     compile with XeLaTeX twice, check pages/warnings, render previews
  record    append one application event to data/ledger.jsonl
  seal      rebuild manifest.json (integrity hashes)
  pack      zip the workspace outside itself after validation
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_FIELDS = ('resumePath', 'coverLetterPath', 'proof', 'applicationProof',
               'backupPath', 'initialProof')
STATUSES = {'success', 'pending', 'uncertain', 'failed', 'delivery_failed'}
ACTION_TYPES = {'new_application', 'supplement', 'status_update'}
PLACEHOLDER = re.compile(r'\{\{([A-Z0-9_]+)\}\}')
DEMO_MARKER = 'DEMO-CONTENT'
TEXT_SUFFIXES = {'.md', '.json', '.tex', '.txt', '.yml', '.yaml'}


def digest(path):
    with Path(path).open('rb') as stream:
        if hasattr(hashlib, 'file_digest'):
            return hashlib.file_digest(stream, 'sha256').hexdigest()
        return _hash(stream)


def _hash(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(chunk)
    return result.hexdigest()


def inside(value, root=None):
    root = Path(root or ROOT)
    text = str(value)
    if Path(text).is_absolute() or re.match(r'^[A-Za-z]:', text) or '\\' in text:
        raise ValueError(f'Expected portable relative path: {text}')
    resolved = (root / text).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes package: {text}')
    return resolved


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def records(root=None):
    root = Path(root or ROOT)
    ledger = root / 'data/ledger.jsonl'
    if not ledger.is_file():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def snapshot_files(root=None):
    root = Path(root or ROOT)
    excluded = {'__pycache__', '.git', '.profile', 'node_modules', '.venv', '.github'}
    return sorted(p for p in root.rglob('*') if p.is_file() and p.name != 'manifest.json'
                  and not excluded.intersection(p.relative_to(root).parts)
                  and p.suffix not in {'.pyc', '.zip'})


def preferences(root=None):
    path = Path(root or ROOT) / 'data/preferences.json'
    if not path.is_file():
        return {}
    return read_json(path)


def fill(text, values):
    def replace(match):
        key = match.group(1)
        return str(values.get(key, match.group(0)))
    return PLACEHOLDER.sub(replace, text)


def header_values(root=None, extra=None):
    """Build the placeholder map from data/preferences.json."""
    prefs = preferences(root)
    candidate = prefs.get('candidate', {})
    target = prefs.get('target', {})
    locations = target.get('locations') or []
    values = {
        'NAME': candidate.get('name', ''),
        'PHONE': candidate.get('phone', ''),
        'EMAIL': candidate.get('email', ''),
        'WECHAT': candidate.get('wechat', ''),
        'GITHUB': candidate.get('github', ''),
        'HOMEPAGE': candidate.get('homepage', ''),
        'ROLE': target.get('role', ''),
        'CITY': '／'.join(locations) if isinstance(locations, list) else str(locations),
        'DEGREE': target.get('degree', ''),
        'EXTRA': target.get('extra', ''),
        'DATE': date.today().strftime('%d %B %Y'),
    }
    values.update(extra or {})
    return values


def unfilled_placeholders(path):
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []
    return sorted(set(PLACEHOLDER.findall(text)))


def init(name, phone='', email='', city='', role='', degree='', extra='', force=False, root=None):
    root = Path(root or ROOT)
    scaffold = root / 'assets/scaffold'
    if not scaffold.is_dir():
        raise ValueError('assets/scaffold missing; cannot initialise')
    if (root / 'data/profile.md').exists() and not force:
        raise ValueError('data/profile.md exists; use --force to overwrite the scaffold')
    values = {'NAME': name, 'PHONE': phone, 'EMAIL': email, 'CITY': city,
              'ROLE': role, 'DEGREE': degree, 'EXTRA': extra,
              'DATE': date.today().isoformat()}
    (root / 'data').mkdir(parents=True, exist_ok=True)
    for source in sorted(scaffold.iterdir()):
        if not source.is_file():
            continue
        target = root / 'data' / source.name
        if source.suffix == '.json':
            write_json(target, json.loads(fill(source.read_text(encoding='utf-8'), values)))
        else:
            target.write_text(fill(source.read_text(encoding='utf-8'), values), encoding='utf-8')
    for folder in ('data/history/attachments', 'data/history/proofs',
                   'data/source-materials', 'output/jobs'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    ledger = root / 'data/ledger.jsonl'
    if not ledger.exists():
        ledger.write_text('', encoding='utf-8')
    print(f'Initialised workspace at {root}')
    print('Next: fill data/profile.md with verified facts, then run validate.')


def seal(root=None):
    root = Path(root or ROOT)
    entries = []
    for path in snapshot_files(root):
        if path.is_symlink():
            raise ValueError(f'Symlinks not packaged: {path}')
        entries.append({'path': path.relative_to(root).as_posix(),
                        'bytes': path.stat().st_size, 'sha256': digest(path)})
    write_json(root / 'manifest.json', {'schemaVersion': 1,
                                       'createdAt': datetime.now(timezone.utc).isoformat(),
                                       'files': entries})
    return len(entries)


def validate(root=None):
    root = Path(root or ROOT)
    errors = []
    manifest_path = root / 'manifest.json'
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        expected = set()
        for item in manifest.get('files', []):
            try:
                path = inside(item['path'], root)
                expected.add(item['path'])
                if not path.is_file() or path.is_symlink():
                    errors.append(f"Missing/unsafe: {item['path']}")
                elif path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
                    errors.append(f"Changed: {item['path']}")
            except ValueError as error:
                errors.append(str(error))
        actual = {p.relative_to(root).as_posix() for p in snapshot_files(root)}
        errors += [f'Unmanifested: {p}' for p in sorted(actual - expected)]
    forbidden = {'.profile', 'node_modules', 'Cookies', 'Login Data', '.env'}
    errors += [f'Forbidden session/cache file: {p.relative_to(root)}' for p in root.rglob('*')
               if forbidden.intersection(p.relative_to(root).parts)]
    scan_roots = [root / 'data', root / 'output/jobs']
    for base in scan_roots:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if 'history' in path.relative_to(base).parts:
                continue
            for key in unfilled_placeholders(path):
                errors.append(f'Unfilled placeholder {{{{{key}}}}} in {path.relative_to(root).as_posix()}')
    try:
        for index, item in enumerate(records(root), 1):
            for field in PATH_FIELDS:
                if item.get(field) and not inside(item[field], root).is_file():
                    errors.append(f'Ledger row {index}: missing {field}')
            if item.get('status') == 'success':
                if not item.get('proof'):
                    errors.append(f'Ledger row {index}: success needs proof')
                if item.get('resumePath') and item.get('resumeHash'):
                    if digest(inside(item['resumePath'], root)) != item['resumeHash'].lower():
                        errors.append(f'Ledger row {index}: resume hash mismatch')
    except (ValueError, OSError, KeyError) as error:
        errors.append(str(error))
    return errors


def status(root=None):
    latest = {}
    for item in records(root):
        if item.get('key') and item.get('status') in STATUSES and item.get('actionType') != 'supplement':
            latest[item['key']] = item
    counts = {}
    for item in latest.values():
        counts[item['status']] = counts.get(item['status'], 0) + 1
    return {'uniqueSuccess': counts.get('success', 0), 'latestStates': counts,
            'events': len(records(root)), 'uniqueJobs': len(latest)}


def run(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, text=True, encoding='utf-8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {command[0]}\n{result.stdout[-5000:]}')
    return result.stdout


def prepare(template, job, extra=None, root=None):
    root = Path(root or ROOT)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,90}', job):
        raise ValueError('Use a short lowercase ASCII job slug, e.g. acme-structural')
    source = inside('assets/templates/' + template, root)
    if source.parent != root / 'assets/templates' or not source.is_dir():
        raise ValueError('Unknown template; see assets/templates')
    target = inside('output/jobs/' + job, root)
    if target.exists():
        raise ValueError('Job folder exists; edit existing files or choose a new slug')
    shutil.copytree(source, target)
    values = header_values(root, extra)
    for path in sorted(target.rglob('*')):
        if path.is_file() and path.suffix.lower() in {'.tex', '.md', '.txt'}:
            path.write_text(fill(path.read_text(encoding='utf-8'), values), encoding='utf-8')
    print(f'{target}')
    print('Tailor the copied sources to the verified JD before building.')
    return target


def build(job, allow_demo=False, root=None):
    root = Path(root or ROOT)
    folder = inside('output/jobs/' + job, root)
    sources = sorted(folder.glob('*.tex'))
    if not sources:
        raise ValueError('No top-level .tex files in selected job folder')
    for source in sources:
        keys = unfilled_placeholders(source)
        if keys:
            raise ValueError(f'Unfilled placeholders in {source.name}: ' + ', '.join(keys))
        if not allow_demo and DEMO_MARKER in source.read_text(encoding='utf-8', errors='replace'):
            raise ValueError(f'{source.name} still contains the {DEMO_MARKER} marker; '
                             'replace the demo entries, delete that comment line, then build')
    missing = [tool for tool in ('xelatex', 'pdfinfo', 'pdftotext', 'pdftoppm') if not shutil.which(tool)]
    if missing:
        raise RuntimeError('Missing PATH tools: ' + ', '.join(missing))
    results = []
    for source in sources:
        for _ in range(2):
            run(['xelatex', '-no-shell-escape', '-interaction=nonstopmode',
                 '-halt-on-error', source.name], folder)
        pdf = source.with_suffix('.pdf')
        info = run(['pdfinfo', str(pdf)])
        match = re.search(r'^Pages:\s+(\d+)', info, re.MULTILINE)
        pages = int(match.group(1)) if match else None
        run(['pdftotext', '-layout', str(pdf), str(source.with_suffix('.txt'))])
        preview = folder / 'previews'
        preview.mkdir(exist_ok=True)
        run(['pdftoppm', '-scale-to', '1600', '-png', str(pdf), str(preview / source.stem)])
        log = source.with_suffix('.log').read_text(encoding='utf-8', errors='replace')
        warnings = [line for line in log.splitlines()
                    if 'Overfull' in line or 'Missing character:' in line]
        results.append({'pdf': pdf.relative_to(root).as_posix(), 'pages': pages,
                        'sha256': digest(pdf), 'warnings': warnings,
                        'requiresVisualInspection': True})
    write_json(folder / 'build-report.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(item['pages'] != 1 or item['warnings'] for item in results):
        raise ValueError('Not approved: page count or overflow/glyph warnings; '
                         'inspect and repair before upload')
    return results


def record(path, root=None):
    root = Path(root or ROOT)
    item = read_json(path)
    required = ('key', 'at', 'company', 'title', 'location', 'salary',
                'source', 'channel', 'actionType', 'status')
    for field in required:
        if not item.get(field):
            raise ValueError(f'Missing {field}')
    if item['status'] not in STATUSES:
        raise ValueError('Unknown application status')
    if item['actionType'] not in ACTION_TYPES:
        raise ValueError('Invalid actionType')
    datetime.fromisoformat(item['at'].replace('Z', '+00:00'))
    if re.search(r'[?&](sid|token|access_token|authorization|password)=', item['source'], re.I):
        raise ValueError('Do not store session/credential URLs')
    for field in PATH_FIELDS:
        if item.get(field) and not inside(item[field], root).is_file():
            raise ValueError(f'Missing local file: {field}')
    if item['status'] == 'success':
        if not item.get('proof') or not item.get('resumePath'):
            raise ValueError('Success needs actual proof and resumePath')
        previous = [r for r in records(root) if r.get('key') == item['key']]
        if any(r.get('status') == 'success' for r in previous) and item['actionType'] == 'new_application':
            raise ValueError('Previously successful key: do not duplicate application')
        item['resumeHash'] = digest(inside(item['resumePath'], root))
    ledger = root / 'data/ledger.jsonl'
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + '\n')
    print('Recorded locally; inspect changes, then seal before packaging.')
    return item


def pack(out, root=None):
    root = Path(root or ROOT)
    target = Path(out).resolve()
    if target.is_relative_to(root):
        raise ValueError('Archive must be outside the workspace root')
    if target.exists():
        raise ValueError('Refusing to overwrite existing archive')
    errors = validate(root)
    if errors:
        raise ValueError('Validation failed:\n' + '\n'.join(errors))
    if not (root / 'manifest.json').exists():
        raise ValueError('No manifest.json; run seal first')
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in snapshot_files(root) + [root / 'manifest.json']:
            archive.write(path, root.name + '/' + path.relative_to(root).as_posix())
    print(f'{target}\nSHA256 {digest(target)}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('doctor', 'validate', 'status', 'seal'):
        subs.add_parser(command)
    init_parser = subs.add_parser('init')
    init_parser.add_argument('--name', required=True)
    init_parser.add_argument('--phone', default='')
    init_parser.add_argument('--email', default='')
    init_parser.add_argument('--city', default='')
    init_parser.add_argument('--role', default='')
    init_parser.add_argument('--degree', default='')
    init_parser.add_argument('--extra', default='')
    init_parser.add_argument('--force', action='store_true')
    prepare_parser = subs.add_parser('prepare')
    prepare_parser.add_argument('--template', required=True)
    prepare_parser.add_argument('--job', required=True)
    prepare_parser.add_argument('--company', default='')
    prepare_parser.add_argument('--title', default='')
    prepare_parser.add_argument('--req', default='')
    build_parser = subs.add_parser('build')
    build_parser.add_argument('--job', required=True)
    build_parser.add_argument('--allow-demo', action='store_true')
    record_parser = subs.add_parser('record')
    record_parser.add_argument('--file', required=True)
    pack_parser = subs.add_parser('pack')
    pack_parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)

    if args.command == 'init':
        init(args.name, args.phone, args.email, args.city, args.role,
             args.degree, args.extra, args.force)
    elif args.command == 'doctor':
        print(json.dumps({'python': sys.version.split()[0], 'root': str(ROOT),
                          'tools': {name: shutil.which(name) for name in
                                    ('xelatex', 'pdfinfo', 'pdftotext', 'pdftoppm')},
                          'initialised': (ROOT / 'data/profile.md').exists()},
                         ensure_ascii=False, indent=2))
    elif args.command == 'validate':
        errors = validate()
        print('\n'.join(errors) if errors else
              'VALID: manifest, ledger references, placeholders and forbidden files')
        return 1 if errors else 0
    elif args.command == 'status':
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    elif args.command == 'seal':
        print(f'Sealed {seal()} files. This is an integrity manifest, not a digital signature.')
    elif args.command == 'prepare':
        prepare(args.template, args.job,
                {'COMPANY': args.company, 'TITLE': args.title, 'REQ': args.req})
    elif args.command == 'build':
        build(args.job, args.allow_demo)
    elif args.command == 'record':
        record(args.file)
    elif args.command == 'pack':
        pack(args.out)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
