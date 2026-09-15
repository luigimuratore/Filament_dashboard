#!/bin/bash
cd "$(dirname "$0")" || exit 1
find_python() {
  for candidate in python3.12 python3.13 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$candidate")"
      return 0
    fi
  done
  return 1
}
if ! find_python; then
  if command -v brew >/dev/null 2>&1; then
    brew install python@3.12 || exit 1
    export PATH="$(brew --prefix python@3.12)/bin:$PATH"
    find_python || exit 1
  else
    echo "Serve Python 3.11 o successivo. Installa Python da https://www.python.org/downloads/macos/ e riapri questo file."
    read -r -p "Premi Invio per chiudere..."
    exit 1
  fi
fi
if ! git --version >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install git || echo "Git non installato: puoi usare la dashboard senza sincronizzazione."
  else
    echo "Git non disponibile. Per la sincronizzazione installa Git o gli strumenti Xcode."
  fi
fi
"$PYTHON_BIN" avvia_dashboard.py
result=$?
if [ "$result" -ne 0 ]; then
  read -r -p "Avvio non riuscito. Premi Invio per chiudere..."
fi
exit "$result"
