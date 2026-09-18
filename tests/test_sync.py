import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from filament_sync import (
    sync_project, authenticate_github, github_owner, git,
    SyncError, GitHubAPIError, cloud_data_config, ensure_cloud_data_branch,
    pull_cloud_archive, push_cloud_archive,
)


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
        with self.assertRaisesRegex(SyncError, 'stessi file'):
            sync_project(self.root)
        self.assertEqual(remote_head, self.run_git(self.base, '--git-dir', str(self.remote), 'rev-parse', 'main'))

    def test_unrelated_staged_files_blocked(self):
        self.run_git(self.root, 'add', 'private.txt')
        with self.assertRaisesRegex(SyncError, 'file estranei'):
            sync_project(self.root)

    def test_github_browser_login_and_verification(self):
        completed = subprocess.CompletedProcess([], 0, stdout='ok', stderr='')
        with patch('filament_sync.git', side_effect=[
                'https://github.com/example/dashboard.git', 'main', 'verified']) as git_call, \
             patch('filament_sync.subprocess.run', return_value=completed) as run:
            message = authenticate_github(self.root)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(['git', 'credential-manager', 'github', 'login', '--browser', '--force'], commands)
        self.assertIn(
            ['git', 'config', '--local', '--unset-all',
             'credential.https://github.com.username'],
            commands,
        )
        git_call.assert_any_call(self.root, 'push', '--dry-run', '--set-upstream', 'origin', 'main')
        self.assertIn('può scrivere', message)

    def test_github_login_requires_credential_manager(self):
        missing = subprocess.CompletedProcess([], 1, stdout='', stderr='missing')
        with patch('filament_sync.git', return_value='https://github.com/example/dashboard.git'), \
             patch('filament_sync.subprocess.run', return_value=missing):
            with self.assertRaisesRegex(SyncError, 'Credential Manager'):
                authenticate_github(self.root)

    def test_github_owner_from_remote(self):
        self.assertEqual(
            github_owner('https://github.com/luigimuratore/Filament_dashboard.git'),
            'luigimuratore',
        )
        with self.assertRaises(SyncError):
            github_owner('git@github.com:luigimuratore/Filament_dashboard.git')

    def test_commit_uses_automatic_identity(self):
        self.run_git(self.root, 'config', '--unset-all', 'user.name')
        self.run_git(self.root, 'config', '--unset-all', 'user.email')
        sync_project(self.root)
        author = self.run_git(self.root, 'show', '-s', '--format=%an|%ae')
        self.assertEqual(
            author,
            'Filament Dashboard|filament-dashboard@users.noreply.github.com',
        )

    def test_sync_removes_stale_github_account_pin(self):
        key = 'credential.https://github.com.username'
        self.run_git(self.root, 'config', '--local', key, 'wrong-account')
        sync_project(self.root)
        result = subprocess.run(
            ['git', 'config', '--local', '--get-all', key], cwd=self.root,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')

    def test_push_permission_error_is_distinct_from_missing_login(self):
        denied = subprocess.CompletedProcess(
            [], 128, stdout='',
            stderr='remote: Permission to luigimuratore/Filament_dashboard.git denied to other-user.',
        )
        with patch('filament_sync.subprocess.run', return_value=denied):
            with self.assertRaisesRegex(SyncError, 'non ha permesso di scrittura'):
                git(self.root, 'push', 'origin', 'main')

    def test_github_login_rejects_wrong_platform_button(self):
        wrong_system = 'windows' if sys.platform == 'darwin' else 'macos'
        with self.assertRaisesRegex(SyncError, 'relativo pulsante'):
            authenticate_github(self.root, system=wrong_system)

    def test_github_login_explains_non_git_folder(self):
        plain_folder = self.base / 'plain-folder'
        plain_folder.mkdir()
        with self.assertRaisesRegex(SyncError, 'scaricata come ZIP'):
            authenticate_github(plain_folder)

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
        with self.assertRaisesRegex(SyncError, 'stessi file'):
            pull_project(self.root)
        self.assertEqual(archive.read_bytes(), b'local work')

    def test_sync_auto_merges_disjoint_changes(self):
        sync_project(self.root)
        self.remote_update()
        (self.root / 'README.md').write_text('Local documentation')
        message = sync_project(self.root)
        self.assertIn('inviato', message)
        self.assertEqual(
            (self.root / 'Tracker_Filament_Dashboard.xlsx').read_bytes(),
            b'updated workbook',
        )
        verify = self.base / 'verify'
        self.run_git(self.base, 'clone', '-b', 'main', str(self.remote), str(verify))
        self.assertEqual((verify / 'README.md').read_text(), 'Local documentation')
        self.assertEqual(
            (verify / 'Tracker_Filament_Dashboard.xlsx').read_bytes(),
            b'updated workbook',
        )

    def test_cloud_config_is_opt_in_and_restricted_to_the_archive(self):
        self.assertIsNone(cloud_data_config({}))
        config = cloud_data_config({'GITHUB_DATA_TOKEN': 'secret'})
        self.assertEqual((config['owner'], config['repo'], config['branch']), (
            'luigimuratore', 'Filament_dashboard', 'dashboard-data',
        ))
        with self.assertRaisesRegex(SyncError, 'solo l’archivio Excel'):
            cloud_data_config({
                'GITHUB_DATA_TOKEN': 'secret',
                'GITHUB_DATA_PATH': 'filament_dashboard.py',
            })

    def test_cloud_data_branch_is_created_from_main_once(self):
        config = cloud_data_config({'GITHUB_DATA_TOKEN': 'secret'})
        with patch('filament_sync._github_api', side_effect=[
                GitHubAPIError(404, 'missing'),
                {'object': {'sha': 'main-sha'}},
                {'ref': 'refs/heads/dashboard-data'},
        ]) as api:
            self.assertTrue(ensure_cloud_data_branch(config))
        self.assertEqual(api.call_args_list[2].args[1], 'POST')
        self.assertEqual(api.call_args_list[2].args[3], {
            'ref': 'refs/heads/dashboard-data', 'sha': 'main-sha',
        })

    def test_cloud_archive_pull_and_push_use_only_the_data_branch(self):
        config = cloud_data_config({'GITHUB_DATA_TOKEN': 'secret'})
        archive = self.root / 'Tracker_Filament_Dashboard.xlsx'
        archive.write_bytes(b'PK-local-workbook')
        with patch('filament_sync.ensure_cloud_data_branch'), \
             patch('filament_sync._cloud_archive', return_value=(b'PK-remote-workbook', 'old-sha')):
            changed, _ = pull_cloud_archive(config, archive)
        self.assertTrue(changed)
        self.assertEqual(archive.read_bytes(), b'PK-remote-workbook')
        self.assertEqual(archive.with_suffix('.backup.xlsx').read_bytes(), b'PK-local-workbook')

        archive.write_bytes(b'PK-new-local-workbook')
        with patch('filament_sync.ensure_cloud_data_branch'), \
             patch('filament_sync._cloud_archive', return_value=(b'PK-remote-workbook', 'old-sha')), \
             patch('filament_sync._github_api', return_value={}) as api:
            changed, _ = push_cloud_archive(config, archive)
        self.assertTrue(changed)
        method, endpoint, payload = api.call_args.args[1:]
        self.assertEqual(method, 'PUT')
        self.assertEqual(payload['branch'], 'dashboard-data')
        self.assertEqual(payload['sha'], 'old-sha')
        self.assertIn('/contents/Tracker_Filament_Dashboard.xlsx', endpoint)
