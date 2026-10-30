import json
import tempfile
import unittest
from pathlib import Path

import kit


def scaffold(root):
    """Create a minimal but valid workspace layout under root."""
    (root / 'assets/scaffold').mkdir(parents=True)
    (root / 'assets/scaffold/preferences.json').write_text(json.dumps({
        'candidate': {'name': '{{NAME}}', 'phone': '{{PHONE}}', 'email': '{{EMAIL}}'},
        'target': {'role': '{{ROLE}}', 'locations': ['{{CITY}}'], 'degree': '{{DEGREE}}',
                   'extra': '{{EXTRA}}'},
    }, ensure_ascii=False), encoding='utf-8')
    (root / 'assets/scaffold/profile.md').write_text('# {{NAME}}\n\n手机：{{PHONE}}\n',
                                                     encoding='utf-8')
    (root / 'assets/scaffold/current-state.md').write_text('更新：{{DATE}}\n', encoding='utf-8')


def template(root, name='demo', body='{{NAME}}'):
    folder = root / 'assets/templates' / name
    folder.mkdir(parents=True)
    (folder / 'main.tex').write_text(body, encoding='utf-8')
    return folder


class KitTests(unittest.TestCase):
    def test_escape_and_absolute_rejected(self):
        for path in ('../outside.pdf', '/tmp/foo', 'C:/secret', 'data\\file'):
            with self.assertRaises(ValueError):
                kit.inside(path)

    def test_manifest_detects_changed_and_unexpected_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'data/ledger.jsonl').write_text('', encoding='utf-8')
            (root / 'test.txt').write_text('one', encoding='utf-8')
            kit.seal(root)
            self.assertEqual(kit.validate(root), [])
            (root / 'test.txt').write_text('two', encoding='utf-8')
            self.assertTrue(any('Changed' in e for e in kit.validate(root)))
            (root / 'new.txt').write_text('new', encoding='utf-8')
            self.assertTrue(any('Unmanifested' in e for e in kit.validate(root)))

    def test_latest_failure_replaces_success_not_counted_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            rows = [{'key': 'x', 'status': 'attempting'}, {'key': 'x', 'status': 'success'},
                    {'key': 'x', 'status': 'delivery_failed'}, {'key': 'y', 'status': 'success'},
                    {'key': 'y', 'status': 'success', 'actionType': 'supplement'}]
            (root / 'data/ledger.jsonl').write_text('\n'.join(map(json.dumps, rows)), encoding='utf-8')
            self.assertEqual(kit.status(root)['uniqueSuccess'], 1)

    def test_missing_ledger_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            self.assertEqual(kit.records(root), [])
            self.assertEqual(kit.status(root)['events'], 0)

    def test_unfilled_placeholder_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'data/preferences.json').write_text(
                json.dumps({'candidate': {'name': '{{NAME}}'}}, ensure_ascii=False), encoding='utf-8')
            errors = kit.validate(root)
            self.assertTrue(any('Unfilled placeholder {{NAME}}' in e for e in errors), errors)

    def test_init_fills_scaffold_and_prepare_fills_header(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scaffold(root)
            kit.init('张三', '13800000000', 'z@example.com', '上海', '结构设计', '2027届硕士',
                     '', root=root)
            prefs = kit.read_json(root / 'data/preferences.json')
            self.assertEqual(prefs['candidate']['name'], '张三')
            self.assertEqual(prefs['target']['locations'], ['上海'])
            self.assertIn('张三', (root / 'data/profile.md').read_text(encoding='utf-8'))
            self.assertEqual(kit.validate(root), [])
            template(root)
            target = kit.prepare('demo', 'acme-role', root=root)
            self.assertIn('张三', (target / 'main.tex').read_text(encoding='utf-8'))

    def test_init_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scaffold(root)
            kit.init('A', root=root)
            with self.assertRaises(ValueError):
                kit.init('B', root=root)
            kit.init('B', force=True, root=root)
            self.assertIn('B', (root / 'data/profile.md').read_text(encoding='utf-8'))

    def test_build_blocks_demo_content_and_unfilled_placeholders(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            template(root, 'demo', '% DEMO-CONTENT\n张三\n')
            (root / 'output/jobs/demo').mkdir(parents=True)
            (root / 'output/jobs/demo/main.tex').write_text('% DEMO-CONTENT\n张三\n', encoding='utf-8')
            with self.assertRaises(ValueError) as caught:
                kit.build('demo', root=root)
            self.assertIn('DEMO-CONTENT', str(caught.exception))
            (root / 'output/jobs/demo/main.tex').write_text('{{COMPANY}}\n', encoding='utf-8')
            with self.assertRaises(ValueError) as caught:
                kit.build('demo', root=root)
            self.assertIn('Unfilled placeholders', str(caught.exception))

    def test_record_rejects_duplicate_success_and_accepts_supplement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'output/jobs/acme').mkdir(parents=True)
            (root / 'output/jobs/acme/resume.pdf').write_bytes(b'%PDF-1.4 test')
            (root / 'output/jobs/acme/proof.png').write_bytes(b'\x89PNG test')
            (root / 'data').mkdir()
            base = {'key': 'portal:acme:1', 'at': '2026-03-01T00:00:00Z', 'company': 'ACME',
                    'title': 'Engineer', 'location': '上海', 'salary': '面议', 'source': 'https://acme.example/1',
                    'channel': 'official_careers_portal', 'actionType': 'new_application',
                    'status': 'success', 'resumePath': 'output/jobs/acme/resume.pdf',
                    'proof': 'output/jobs/acme/proof.png'}
            record_file = root / 'row.json'
            record_file.write_text(json.dumps(base, ensure_ascii=False), encoding='utf-8')
            kit.record(record_file, root=root)
            with self.assertRaises(ValueError):
                kit.record(record_file, root=root)
            base['actionType'] = 'supplement'
            record_file.write_text(json.dumps(base, ensure_ascii=False), encoding='utf-8')
            kit.record(record_file, root=root)
            self.assertEqual(kit.status(root)['uniqueSuccess'], 1)
            self.assertEqual(kit.status(root)['events'], 2)

    def test_record_rejects_session_url(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            row = {'key': 'k', 'at': '2026-03-01T00:00:00Z', 'company': 'C', 'title': 'T',
                   'location': 'L', 'salary': 'S', 'source': 'https://x.example/j?token=abc',
                   'channel': 'portal', 'actionType': 'status_update', 'status': 'pending'}
            record_file = root / 'row.json'
            record_file.write_text(json.dumps(row), encoding='utf-8')
            with self.assertRaises(ValueError):
                kit.record(record_file, root=root)


if __name__ == '__main__':
    unittest.main()
