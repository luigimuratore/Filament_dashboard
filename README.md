# Filament · MITIC Lab - 3ntr 3D printer

Avvia `Avvia_Dashboard.command` con un doppio clic. Se la dashboard era già aperta, aggiorna la pagina.

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
