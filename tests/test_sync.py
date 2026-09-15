import subprocess
import tempfile
import unittest
from pathlib import Path
from filament_sync import sync_project, SyncError


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'project'
        self.remote = self.base / 'remote.git'
        self.root.mkdir()
        self.run_git(self.base, 'init', '--bare', str(self.remote))
        self.run_git(self.root, 'init', '-b', 'main')
        self.run_git(self.root, 'config', 'user.name', 'Test')
        self.run_git(self.root, 'config', 'user.email', 'test@example.com')
        self.run_git(self.root, 'remote', 'add', 'origin', str(self.remote))
        (self.root / 'README.md').write_text('Dashboard')
        (self.root / 'Tracker_Filament_Dashboard.xlsx').write_bytes(b'test workbook')
        (self.root / 'private.txt').write_text('not for GitHub')

    def tearDown(self):
        self.tmp.cleanup()

    def run_git(self, root, *args):
        return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

    def test_commit_push_and_no_changes(self):
        self.assertIn('Commit creato', sync_project(self.root))
        head = self.run_git(self.root, 'rev-parse', 'HEAD')
        self.assertEqual(head, self.run_git(self.base, '--git-dir', str(self.remote), 'rev-parse', 'main'))
        self.assertNotIn('private.txt', self.run_git(self.root, 'ls-files'))
        self.assertNotIn('.lock', self.run_git(self.root, 'ls-files'))
        self.assertIn('Nessuna nuova modifica', sync_project(self.root))
        self.assertEqual(head, self.run_git(self.root, 'rev-parse', 'HEAD'))

    def test_retry_push_after_failure(self):
        self.run_git(self.root, 'remote', 'set-url', 'origin', str(self.base / 'missing.git'))
        with self.assertRaises(SyncError): sync_project(self.root)
        head = self.run_git(self.root, 'rev-parse', 'HEAD')
        self.run_git(self.root, 'remote', 'set-url', 'origin', str(self.remote))
        sync_project(self.root)
        self.assertEqual(head, self.run_git(self.base, '--git-dir', str(self.remote), 'rev-parse', 'main'))

    def test_remote_changes_not_overwritten(self):
        sync_project(self.root)
        other = self.base / 'other'
        self.run_git(self.base, 'clone', '-b', 'main', str(self.remote), str(other))
        self.run_git(other, 'config', 'user.name', 'Test')
        self.run_git(other, 'config', 'user.email', 'test@example.com')
        (other / 'README.md').write_text('Remote change')
        self.run_git(other, 'commit', '-am', 'Remote update')
        self.run_git(other, 'push', 'origin', 'main')
        remote_head = self.run_git(other, 'rev-parse', 'HEAD')
        (self.root / 'README.md').write_text('Local change')
        with self.assertRaisesRegex(SyncError, 'modifiche da integrare'):
            sync_project(self.root)
        self.assertEqual(remote_head, self.run_git(self.base, '--git-dir', str(self.remote), 'rev-parse', 'main'))

    def test_unrelated_staged_files_blocked(self):
        self.run_git(self.root, 'add', 'private.txt')
        with self.assertRaisesRegex(SyncError, 'file estranei'):
            sync_project(self.root)
