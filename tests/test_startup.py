import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import avvia_dashboard as startup
from filament_lock import file_lock


class StartupTests(unittest.TestCase):
    def test_lock_blocks_other_process_then_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'archive.lock'
            code = '''
import sys
from filament_lock import file_lock
try:
    with file_lock(sys.argv[1], blocking=False): pass
except BlockingIOError:
    sys.exit(7)
'''
            with file_lock(path):
                result = subprocess.run([sys.executable, '-c', code, str(path)], cwd=startup.BASE)
                self.assertEqual(result.returncode, 7)
            result = subprocess.run([sys.executable, '-c', code, str(path)], cwd=startup.BASE)
            self.assertEqual(result.returncode, 0)

    def test_healthy_environment_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            with patch.object(startup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                self.assertEqual(startup.prepare_environment(base), startup.venv_python(base))
                self.assertEqual(run.call_count, 1)

    def test_incompatible_environment_is_preserved_and_recreated(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / '.venv').mkdir()
            (base / '.venv' / 'old-file').write_text('keep me')
            with patch.object(startup.subprocess, 'run', side_effect=[FileNotFoundError(), subprocess.CompletedProcess([], 0)]) as run:
                startup.prepare_environment(base)
                self.assertEqual(run.call_count, 2)
            copies = list(base.glob('.venv.previous-*'))
            self.assertEqual(len(copies), 1)
            self.assertEqual((copies[0] / 'old-file').read_text(), 'keep me')

    def test_missing_requirements_trigger_install_then_check(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'Tracker_Filament_Dashboard.xlsx').touch()
            with patch.object(startup, 'BASE', base), patch.object(startup.os, 'chdir'), \
                 patch.object(startup, 'prepare_environment', return_value=Path('test-python')), \
                 patch.object(startup, 'requirements_ok', side_effect=[False, True]), \
                 patch.object(startup.subprocess, 'run') as run:
                self.assertEqual(startup.main(check_only=True), 0)
                commands = [x.args[0] for x in run.call_args_list]
                self.assertTrue(any('ensurepip' in c for c in commands))
                self.assertTrue(any('pip' in c and 'install' in c for c in commands))

    def test_failed_dependency_install_stops_launch(self):
        with patch.object(startup.os, 'chdir'), \
             patch.object(startup, 'prepare_environment', return_value=Path('test-python')), \
             patch.object(startup, 'requirements_ok', return_value=False), \
             patch.object(startup.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'pip')), \
             patch.object(startup.subprocess, 'call') as launch:
            with self.assertRaises(subprocess.CalledProcessError): startup.main()
            launch.assert_not_called()
