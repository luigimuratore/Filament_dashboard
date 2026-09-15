"""Manual Git synchronization. Never pulls, merges or overwrites remote history."""
from datetime import datetime
from pathlib import Path
import fcntl
import os
import subprocess

BASE = Path(__file__).resolve().parent
PROJECT_FILES = [
    '.gitignore', '.streamlit/config.toml', 'Avvia_Dashboard.command',
    'README.md', 'requirements.txt', 'filament_dashboard.py',
    'filament_store.py', 'filament_sync.py', 'Tracker_Filament_Dashboard.xlsx',
    'tests/test_dashboard.py', 'tests/test_sync.py',
]


class SyncError(Exception):
    pass


def git(root, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/usr/bin/false',
               SSH_ASKPASS='/usr/bin/false', GCM_INTERACTIVE='never',
               GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=10')
    try:
        result = subprocess.run(['git', *args], cwd=root, env=env, capture_output=True,
                                text=True, timeout=45)
    except FileNotFoundError:
        raise SyncError('Git non è installato o non è disponibile.')
    except subprocess.TimeoutExpired:
        raise SyncError('Operazione scaduta. Controlla la connessione e riprova; eventuali commit locali restano salvati.')
    if result.returncode:
        details = (result.stderr + result.stdout).lower()
        if 'non-fast-forward' in details or 'fetch first' in details or 'rejected' in details:
            raise SyncError('GitHub contiene modifiche da integrare. Il commit resta locale: esegui pull dal terminale e risolvi eventuali conflitti, poi riprova. Nessun file remoto è stato sovrascritto.')
        if 'identity unknown' in details or 'unable to auto-detect email' in details:
            raise SyncError('Configura nome ed email Git sul computer prima di creare un commit (git config user.name e git config user.email).')
        if any(x in details for x in ('authentication', 'could not read username', 'permission denied', 'repository not found', '403', '401')):
            raise SyncError('Accesso a GitHub non disponibile. Configura l’autenticazione Git sul computer e riprova; eventuali commit restano locali.')
        if any(x in details for x in ('resolve host', 'could not resolve', 'failed to connect', 'network')):
            raise SyncError('Connessione a GitHub non riuscita. I dati e gli eventuali commit restano locali: riprova quando sei online.')
        raise SyncError(f'Operazione Git «{args[0]}» non riuscita. Controlla lo stato della repository dal terminale; eventuali commit locali restano salvati.')
    return result.stdout.strip()


def sync_project(root=BASE):
    root = Path(root)
    # Use the workbook lock to keep dashboard writes out of the commit snapshot.
    with (root / 'Tracker_Filament_Dashboard.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SyncError('È già in corso un salvataggio o una sincronizzazione. Riprova tra poco.')
        branch = git(root, 'symbolic-ref', '--short', 'HEAD')
        git(root, 'remote', 'get-url', 'origin')
        if git(root, 'diff', '--name-only', '--diff-filter=U'):
            raise SyncError('Ci sono conflitti Git da risolvere prima di sincronizzare.')
        staged = git(root, 'diff', '--cached', '--name-only').splitlines()
        if set(staged) - set(PROJECT_FILES):
            raise SyncError('Ci sono file estranei alla dashboard già preparati per un commit. Gestiscili dal terminale prima di sincronizzare.')
        tracked = set(git(root, 'ls-files').splitlines())
        paths = [p for p in PROJECT_FILES if (root / p).exists() or p in tracked]
        if paths:
            git(root, 'add', '--', *paths)
        changed = bool(git(root, 'diff', '--cached', '--name-only'))
        if changed:
            git(root, 'commit', '-m', f'Aggiorna dashboard e dati · {datetime.now():%Y-%m-%d %H:%M:%S}')
        # Push even without new changes: a previous attempt may have committed offline.
        git(root, 'push', '--set-upstream', 'origin', branch)
        return ('Commit creato e inviato a GitHub.' if changed else 'GitHub aggiornato. Nessuna nuova modifica da registrare.')
