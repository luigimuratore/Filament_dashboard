"""Create/check the virtual environment, install missing requirements, launch the app."""
from datetime import datetime
from pathlib import Path
import os
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def venv_python(base=BASE):
    return base / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def requirements_ok(python, base=BASE):
    # Run inside the target environment; packaging comes with Streamlit/pip installs.
    code = '''
from importlib.metadata import version
from packaging.requirements import Requirement
from datetime import datetime
from pathlib import Path
for line in Path('requirements.txt').read_text().splitlines():
    line = line.strip()
    if not line or line.startswith('#'): continue
    req = Requirement(line)
    if req.marker and not req.marker.evaluate(): continue
    assert req.specifier.contains(version(req.name)), line
import streamlit, openpyxl
'''
    try:
        return subprocess.run([str(python), '-c', code], cwd=base,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def prepare_environment(base):
    python = venv_python(base)
    try:
        valid = subprocess.run([str(python), '-c',
            'import sys; sys.exit(0 if sys.version_info >= (3,11) and sys.prefix != sys.base_prefix else 1)'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        valid = False
    if not valid:
        environment = base / '.venv'
        if environment.exists():
            backup = base / f'.venv.previous-{datetime.now():%Y%m%d-%H%M%S-%f}'
            environment.rename(backup)
            print('Ambiente Python non compatibile: conservato e ricreato.', flush=True)
        print('Creazione ambiente Python locale...', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(environment)], check=True)
    return python


def main(check_only=False):
    if sys.version_info < (3, 11):
        raise RuntimeError('Serve Python 3.11 o successivo. Usa il launcher del tuo sistema.')
    os.chdir(BASE)
    python = prepare_environment(BASE)
    print('Controllo dipendenze...', flush=True)
    if not requirements_ok(python):
        print('Installazione delle dipendenze mancanti o non compatibili (serve Internet)...', flush=True)
        subprocess.run([str(python), '-m', 'ensurepip', '--upgrade'], check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(BASE / 'requirements.txt')], check=True)
        if not requirements_ok(python):
            raise RuntimeError('Verifica dipendenze non riuscita. Controlla gli errori di installazione.')
    if not (BASE / 'Tracker_Filament_Dashboard.xlsx').exists():
        raise RuntimeError('Archivio Excel mancante: copia anche Tracker_Filament_Dashboard.xlsx nella cartella del progetto.')
    if check_only:
        print('Requisiti verificati. Dashboard pronta.')
        return 0
    print('Avvio dashboard. Lascia aperta questa finestra; premi Ctrl+C per fermarla.', flush=True)
    return subprocess.call([str(python), '-m', 'streamlit', 'run', 'filament_dashboard.py',
                            '--server.address=localhost', '--server.headless=false'])


if __name__ == '__main__':
    try:
        raise SystemExit(main('--check' in sys.argv))
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Avvio non riuscito: {exc}', file=sys.stderr)
        raise SystemExit(1)
