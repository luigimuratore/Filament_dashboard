"""Git synchronization with guarded fast-forward updates and explicit push."""
from datetime import datetime
from pathlib import Path
from filament_lock import file_lock
import os
import subprocess
import sys

BASE = Path(__file__).resolve().parent
PROJECT_FILES = [
    '.gitignore', '.streamlit/config.toml', 'Avvia_Dashboard.command',
    'README.md', 'requirements.txt', 'filament_dashboard.py',
    'filament_store.py', 'filament_sync.py', 'Tracker_Filament_Dashboard.xlsx',
    'tests/test_dashboard.py', 'tests/test_sync.py', 'tests/test_startup.py',
    'filament_lock.py', 'avvia_dashboard.py', 'Avvia_Dashboard.bat',
    'Avvia_Dashboard.ps1', '.gitattributes', '.github/workflows/tests.yml',
]


class SyncError(Exception):
    pass


def git(root, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='echo',
               SSH_ASKPASS='echo', GCM_INTERACTIVE='never',
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
        if 'not a git repository' in details:
            raise SyncError(
                'Questa cartella non è una copia Git della dashboard. Scarica il progetto con '
                '“git clone https://github.com/luigimuratore/Filament_dashboard.git” e avvia '
                'la dashboard dalla nuova cartella.'
            )
        if 'no such remote' in details or "'origin' does not appear to be a git repository" in details:
            raise SyncError(
                'Manca il collegamento “origin” a GitHub. Nella cartella del progetto esegui: '
                'git remote add origin https://github.com/luigimuratore/Filament_dashboard.git'
            )
        if 'non-fast-forward' in details or 'fetch first' in details or 'rejected' in details:
            raise SyncError('GitHub contiene modifiche da integrare. Il commit resta locale: esegui pull dal terminale e risolvi eventuali conflitti, poi riprova. Nessun file remoto è stato sovrascritto.')
        if 'identity unknown' in details or 'unable to auto-detect email' in details:
            raise SyncError('Configura nome ed email Git sul computer prima di creare un commit (git config user.name e git config user.email).')
        if any(x in details for x in ('authentication', 'could not read username', 'permission denied', 'repository not found', '403', '401')):
            raise SyncError('Accesso a GitHub non disponibile. Usa “Accedi a GitHub” nella barra laterale e riprova; eventuali commit restano locali.')
        if any(x in details for x in ('resolve host', 'could not resolve', 'failed to connect', 'network')):
            raise SyncError('Connessione a GitHub non riuscita. I dati e gli eventuali commit restano locali: riprova quando sei online.')
        raise SyncError(f'Operazione Git «{args[0]}» non riuscita. Controlla lo stato della repository dal terminale; eventuali commit locali restano salvati.')
    return result.stdout.strip()


def authenticate_github(root=BASE, system=None):
    """Open Git Credential Manager's browser login and verify the saved credential."""
    root = Path(root)
    current_system = 'windows' if os.name == 'nt' else ('macos' if sys.platform == 'darwin' else 'other')
    requested_system = system or current_system
    if requested_system not in ('windows', 'macos'):
        raise SyncError('Il login guidato è disponibile su Windows e macOS.')
    if requested_system != current_system:
        label = 'Windows' if current_system == 'windows' else 'macOS'
        raise SyncError(f'Questo computer usa {label}: scegli il relativo pulsante di accesso.')
    if not (root / '.git').is_dir():
        raise SyncError(
            'Questa cartella non contiene la repository Git. Probabilmente è stata scaricata come ZIP: '
            'clona la repository da Terminale e avvia la dashboard dalla nuova cartella.'
        )
    remote = git(root, 'remote', 'get-url', 'origin')
    if not remote.lower().startswith('https://github.com/'):
        raise SyncError('Il login guidato è disponibile per repository GitHub collegate tramite HTTPS.')

    env = dict(os.environ, GIT_TERMINAL_PROMPT='1', GCM_INTERACTIVE='always')
    try:
        available = subprocess.run(
            ['git', 'credential-manager', '--version'], cwd=root, env=env,
            capture_output=True, text=True, timeout=15,
        )
        if available.returncode:
            if current_system == 'windows':
                raise SyncError(
                    'Git Credential Manager non è disponibile. Installa o aggiorna Git for Windows, '
                    'riapri la dashboard e riprova.'
                )
            raise SyncError(
                'Git Credential Manager non è disponibile. Da Terminale esegui '
                '“brew install --cask git-credential-manager”, riapri la dashboard e riprova.'
            )
        subprocess.run(
            ['git', 'credential-manager', 'configure'], cwd=root, env=env,
            capture_output=True, text=True, timeout=30, check=True,
        )
        login = subprocess.run(
            ['git', 'credential-manager', 'github', 'login', '--browser', '--force'],
            cwd=root, env=env, capture_output=True, text=True, timeout=300,
        )
    except FileNotFoundError:
        raise SyncError('Git non è installato o non è disponibile.')
    except subprocess.TimeoutExpired:
        raise SyncError('Accesso non completato in tempo. Riapri “Accedi a GitHub” e completa il login nel browser.')
    except subprocess.CalledProcessError:
        raise SyncError('Impossibile configurare Git Credential Manager. Aggiorna Git for Windows e riprova.')
    if login.returncode:
        raise SyncError('Accesso a GitHub non completato. Riprova e termina la procedura nel browser.')

    # This remains non-interactive: it confirms that the credential has really been stored.
    git(root, 'ls-remote', 'origin')
    return 'Accesso a GitHub configurato su questo computer. Ora puoi sincronizzare.'


def sync_project(root=BASE):
    root = Path(root)
    # Use the workbook lock to keep dashboard writes out of the commit snapshot.
    with file_lock(root / 'Tracker_Filament_Dashboard.lock', blocking=False):
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


def pull_project(root=BASE):
    """Fetch and fast-forward only; never stash, reset or merge local Excel edits."""
    root = Path(root)
    with file_lock(root / 'Tracker_Filament_Dashboard.lock', blocking=False):
        branch = git(root, 'symbolic-ref', '--short', 'HEAD')
        if git(root, 'status', '--porcelain', '--untracked-files=no'):
            raise SyncError('Aggiornamento sospeso: ci sono modifiche locali da salvare e inviare con “Sincronizza con GitHub”. I tuoi dati sono conservati.')
        git(root, 'fetch', 'origin', branch)
        ahead, behind = map(int, git(root, 'rev-list', '--left-right', '--count', 'HEAD...FETCH_HEAD').split())
        if ahead and behind:
            raise SyncError('Questo computer e GitHub hanno aggiornamenti diversi. Integra i commit dal terminale prima di continuare: nessun dato locale è stato sostituito.')
        if not behind:
            return False, 'Nessun aggiornamento da scaricare.' + (' Ci sono commit locali da inviare.' if ahead else '')
        # Recheck after the network request (external editors do not use our lock).
        if git(root, 'status', '--porcelain', '--untracked-files=no'):
            raise SyncError('I file locali sono cambiati durante il controllo. Pull annullato: riprova dopo aver sincronizzato le modifiche.')
        changed = git(root, 'diff', '--name-only', 'HEAD', 'FETCH_HEAD').splitlines()
        archive = root / 'Tracker_Filament_Dashboard.xlsx'
        if archive.exists() and archive.name in changed:
            import shutil
            shutil.copy2(archive, archive.with_suffix('.backup.xlsx'))
        git(root, 'merge', '--ff-only', 'FETCH_HEAD')
        code_changed = any(p.endswith(('.py', '.toml', '.command', '.bat', '.ps1')) or p == 'requirements.txt' for p in changed)
        message = 'Aggiornamenti scaricati da GitHub. Dati locali aggiornati.'
        if code_changed:
            message += ' È cambiato anche il programma: chiudi e riapri il launcher per caricare codice e requisiti aggiornati.'
        return True, message
