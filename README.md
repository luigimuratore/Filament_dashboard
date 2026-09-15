# Filament · MITIC Lab - 3ntr 3D printer

## Avvio su Windows e macOS

Scarica o clona l'intera cartella del progetto, incluso l'archivio Excel.

- **Windows 10/11:** doppio clic su `Avvia_Dashboard.bat`.
- **macOS:** doppio clic su `Avvia_Dashboard.command`.

Il launcher controlla Python (3.11 o successivo), crea l'ambiente virtuale locale, verifica le versioni delle dipendenze e installa quelle mancanti o incompatibili. Poi apre la dashboard nel browser. Ai successivi avvii, se i requisiti sono soddisfatti, non reinstalla le librerie. La finestra del terminale deve restare aperta; Ctrl+C ferma la dashboard.

### Installazione dei prerequisiti

**Windows:** se Python manca, il launcher installa Python 3.12 tramite WinGet; se manca Git, tenta di installarlo allo stesso modo. Occorrono Internet e WinGet (App Installer dal Microsoft Store). Windows puo richiedere autorizzazioni di installazione; eventuali restrizioni aziendali non vengono aggirate. Se WinGet non e disponibile, il messaggio indica come installarlo. Se solo Git non si installa, la dashboard parte comunque e la sincronizzazione richiede di completare la configurazione Git.

**macOS:** Python e Git mancanti vengono installati tramite Homebrew, se gia presente. Se manca anche Homebrew, installa prima Python da https://www.python.org/downloads/macos/ e Git tramite gli strumenti Xcode, poi riapri il launcher. Le librerie Python sono gestite automaticamente su entrambi i sistemi.

Nome ed email Git identificano l'autore dei commit, ma non autorizzano il push. Su un computer nuovo usa **GitHub · Windows** oppure **GitHub · Mac** nella barra laterale. Il pulsante controlla il sistema scelto, apre il login OAuth nel browser e conserva la credenziale nel Gestore credenziali di Windows o nel Portachiavi di macOS. La dashboard non legge né salva password o token. Su Windows, Git Credential Manager viene installato insieme alle versioni recenti di Git for Windows. Su macOS, se manca, installalo con `brew install --cask git-credential-manager` e riapri la dashboard.

Un ambiente `.venv` non eseguibile o non compatibile viene conservato come `.venv.previous-*` e ricreato. Queste copie non vengono inviate a GitHub. Non copiare manualmente `.venv` tra computer: ogni sistema crea il proprio ambiente.

Per controllare i requisiti senza avviare il server, esegui `python avvia_dashboard.py --check` (su macOS `python3`). Il file Excel deve essere chiuso in Excel durante i salvataggi della dashboard, soprattutto su Windows.

Il blocco dell'archivio usa le funzioni native del sistema operativo. Il workflow `.github/workflows/tests.yml` esegue i test su Windows e macOS a ogni push/PR. La verifica locale della migrazione e stata eseguita su macOS; il primo risultato Windows sara disponibile dopo il push.

## Il flusso quotidiano

1. **Panoramica**: controlla le bobine caricate sui tre ugelli. Apri “Cambia bobine” per assegnare, scambiare o scaricare una bobina. Una bobina può occupare un solo ugello.
2. **Nuova stampa**: inserisci nome, data e grammi dello slicer per ogni ugello utilizzato. Includi supporti e spurghi; lascia zero sugli ugelli inutilizzati. Controlla il residuo previsto e registra una volta a stampa conclusa.
3. **Magazzino**: tre colonne ABS, Supporto (anche PVA/BVOH) e Altro, con conteggio e grammi. Cerca per materiale, colore, marca o ID, filtra per posizione e disponibilità e ordina per residuo, grammi, colore o ID. Aggiungi ogni bobina acquistata indicando il peso netto del filamento. Il pulsante “Elimina” dentro ogni scheda permette di rimuovere una bobina non caricata; “Bobine eliminate” permette di ripristinarla. Le bobine eliminate non contribuiscono alle scorte e conservano ID e dettagli nello storico.
4. **Storico**: ogni stampa raggruppa i consumi dei diversi ugelli. Le schede mostrano data e ora, consumi per ugello, bobina, materiale, colore, marca e note; puoi anche esportare i consumi in CSV.

## Indicatori

- Verde: oltre il 40% del peso iniziale.
- Ambra: oltre il 20% e fino al 40%.
- Rosso: fino al 20%; a zero la bobina è esaurita.

La sezione “Da tenere d’occhio” in Panoramica somma tutte le bobine dello stesso materiale e colore, comprese quelle caricate. La soglia è il 20% del peso iniziale della bobina più grande del gruppo. Le marche sono considerate intercambiabili: controllare eventuali requisiti della stampa prima di ordinare. La pagina Riacquisti è temporaneamente rimossa.

I residui sono stime basate sui consumi inseriti, non misure della stampante.

## Dati

L'archivio resta `Tracker_Filament_Dashboard.xlsx`. Ogni salvataggio crea `Tracker_Filament_Dashboard.backup.xlsx` con la versione immediatamente precedente e sostituisce l'archivio solo dopo aver completato la scrittura. La copia di sicurezza viene aggiornata a ogni modifica.

Le nuove stampe hanno un identificativo univoco nella colonna aggiuntiva “ID Stampa”. Le righe storiche senza identificativo sono raggruppate per data/ora esatta, nome e note. I dati precedenti vengono conservati. Evitare di modificare contemporaneamente il file in Excel e nella dashboard.

## Verifica

```sh
.venv/bin/python -m unittest discover -s tests -v
```

I test lavorano su copie temporanee dell'archivio e coprono navigazione, registrazione, scorte, assegnazioni e conflitti di salvataggio.

## Correggere un inserimento

- **Modifica** nella scheda di una bobina apre materiale, marca, colore, peso netto iniziale e consumo totale. L’ID resta stabile. I dettagli corretti compaiono anche nello storico. Il consumo totale non può scendere sotto i grammi già registrati nelle stampe: correggi prima le stampe interessate.
- **Modifica** nelle schede delle stampe permette di correggere nome, data, ora, note e tabella dei consumi (ugello, bobina, grammi). Puoi aggiungere o rimuovere righe. Il salvataggio restituisce i vecchi consumi alle relative bobine e applica quelli corretti, senza cambiare il setup attuale. Vengono bloccate correzioni che superano il filamento disponibile.
- **Annulla** chiude la modifica senza salvare.

## Sincronizzazione manuale con GitHub

Nella barra laterale, **Sincronizza con GitHub** crea un commit e invia a `origin` il branch corrente. Include codice della dashboard, test, configurazione, README e archivio Excel. File privati, ambiente virtuale, lock e backup non vengono aggiunti. Non serve eseguire comandi ogni volta.

Git deve avere nome, email e credenziali GitHub configurati sul computer. Il pulsante non richiede password nella dashboard. Se il push fallisce, il commit resta locale e il pulsante può ritentare l’invio anche senza nuove modifiche.

All’apertura di ogni sessione della dashboard viene eseguito un controllo automatico: gli aggiornamenti GitHub vengono integrati solo se non ci sono modifiche locali e non servono merge. Il pulsante “Recupera aggiornamenti” ripete il controllo manualmente. Prima di aggiornare l’Excel viene conservata una copia `.backup.xlsx`. In caso di connessione assente o conflitto, la dashboard mostra un avviso e conserva i dati locali. Se viene aggiornato anche il codice, riavvia il launcher per caricare moduli e dipendenze aggiornati. Per usare l’Excel su più computer, lavora su uno alla volta e invia a fine lavoro; sull’altro apri la dashboard e verifica l’esito del recupero prima di registrare stampe.

## Github codes to login
git credential-manager configure
git credential-manager github login --browser
