import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from filament_sync import sync_project, authenticate_github, SyncError


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

    def test_github_browser_login_and_verification(self):
        completed = subprocess.CompletedProcess([], 0, stdout='ok', stderr='')
        with patch('filament_sync.git', side_effect=[
                'https://github.com/example/dashboard.git', 'verified']) as git_call, \
             patch('filament_sync.subprocess.run', return_value=completed) as run:
            message = authenticate_github(self.root)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(['git', 'credential-manager', 'github', 'login', '--browser', '--force'], commands)
        git_call.assert_any_call(self.root, 'ls-remote', 'origin')
        self.assertIn('configurato', message)

    def test_github_login_requires_credential_manager(self):
        missing = subprocess.CompletedProcess([], 1, stdout='', stderr='missing')
        with patch('filament_sync.git', return_value='https://github.com/example/dashboard.git'), \
             patch('filament_sync.subprocess.run', return_value=missing):
            with self.assertRaisesRegex(SyncError, 'Credential Manager'):
                authenticate_github(self.root)

    def test_github_login_rejects_wrong_platform_button(self):
        wrong_system = 'windows' if sys.platform == 'darwin' else 'macos'
        with self.assertRaisesRegex(SyncError, 'relativo pulsante'):
            authenticate_github(self.root, system=wrong_system)

    def remote_update(self):
        other = self.base / 'other'
        self.run_git(self.base, 'clone', '-b', 'main', str(self.remote), str(other))
        self.run_git(other, 'config', 'user.name', 'Test')
        self.run_git(other, 'config', 'user.email', 'test@example.com')
        (other / 'Tracker_Filament_Dashboard.xlsx').write_bytes(b'updated workbook')
        self.run_git(other, 'commit', '-am', 'Update archive')
        self.run_git(other, 'push', 'origin', 'main')

    def test_pull_updates_archive_and_keeps_backup(self):
        from filament_sync import pull_project
        sync_project(self.root)
        self.remote_update()
        changed, message = pull_project(self.root)
        self.assertTrue(changed)
        self.assertEqual((self.root / 'Tracker_Filament_Dashboard.xlsx').read_bytes(), b'updated workbook')
        self.assertEqual((self.root / 'Tracker_Filament_Dashboard.backup.xlsx').read_bytes(), b'test workbook')
        self.assertFalse(pull_project(self.root)[0])

    def test_pull_preserves_local_edits_and_divergent_commits(self):
        from filament_sync import pull_project
        sync_project(self.root)
        self.remote_update()
        archive = self.root / 'Tracker_Filament_Dashboard.xlsx'
        archive.write_bytes(b'local work')
        with self.assertRaisesRegex(SyncError, 'modifiche locali'):
            pull_project(self.root)
        self.assertEqual(archive.read_bytes(), b'local work')
        self.run_git(self.root, 'commit', '-am', 'Local work')
        with self.assertRaisesRegex(SyncError, 'aggiornamenti diversi'):
            pull_project(self.root)
        self.assertEqual(archive.read_bytes(), b'local work')
