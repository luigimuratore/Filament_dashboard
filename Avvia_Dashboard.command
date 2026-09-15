#!/bin/bash
# Finder can provide a minimal PATH; include common standalone Python installs.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
finish() {
  result=$?
  if [ "$result" -ne 0 ]; then
    echo
    echo "Avvio non riuscito. Il messaggio qui sopra indica il problema."
    read -r -p "Premi Invio per chiudere..."
  fi
}
trap finish EXIT
cd "$(dirname "$0")" || exit 1
find_python() {
  for candidate in python3.12 python3.13 python3.11 python3 python \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3; do
    resolved="$(command -v "$candidate" 2>/dev/null)" || continue
    # Apple's shim can invoke Xcode setup/license prompts instead of running Python.
    case "$resolved" in
      /usr/bin/python*|/Applications/Xcode.app/*|/Library/Developer/*) continue ;;
    esac
    if "$resolved" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' </dev/null >/dev/null 2>&1; then
      PYTHON_BIN="$resolved"
      return 0
    fi
  done
  return 1
}
if ! find_python; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installazione di Python indipendente da Xcode..."
    if ! brew install python@3.12 </dev/null; then
      echo "Homebrew non ha completato l'installazione (potrebbe richiedere la licenza Xcode)."
      echo "In alternativa installa Python da https://www.python.org/downloads/macos/ e riapri questo file."
      exit 1
    fi
    export PATH="$(brew --prefix python@3.12)/bin:$PATH"
    find_python || exit 1
  else
    echo "Serve Python 3.11 o successivo, indipendente da Xcode."
    echo "Installa Python da https://www.python.org/downloads/macos/ e riapri questo file."
    exit 1
  fi
fi
# Git is optional for the dashboard: do not execute Apple's Git shim on startup.
git_path="$(command -v git 2>/dev/null)"
if [ -z "$git_path" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew install git </dev/null || echo "Git non installato: la dashboard funziona comunque senza sincronizzazione."
  else
    echo "Git non disponibile. Puoi usare la dashboard; configura Git per sincronizzare."
  fi
fi
"$PYTHON_BIN" avvia_dashboard.py
exit $?
