"""Workbook operations shared by the dashboard and its tests."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import fcntl
import hashlib
import math
import os
import shutil
import tempfile
from openpyxl import load_workbook

FILE = Path(__file__).resolve().parent / 'Tracker_Filament_Dashboard.xlsx'


def load(path=FILE):
    # Read the bytes once so the revision always matches the loaded workbook.
    from io import BytesIO
    data = Path(path).read_bytes()
    wb = load_workbook(BytesIO(data))
    wb._revision = hashlib.sha256(data).digest()
    return wb


def save(wb, path=FILE):
    path = Path(path)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if hashlib.sha256(path.read_bytes()).digest() != wb._revision:
            raise ValueError('I dati sono cambiati in un’altra finestra. Ricarica la pagina e riprova.')
        fd, name = tempfile.mkstemp(dir=path.parent, suffix='.xlsx')
        os.close(fd)
        try:
            wb.save(name)
            shutil.copy2(path, path.with_suffix('.backup.xlsx'))
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def assignments(wb):
    return {int(r[0]): str(r[1] or '') for r in wb['Ugelli'].iter_rows(min_row=2, values_only=True) if r[0] in (1, 2, 3)}


def bobine(wb, include_removed=False):
    loaded = {bid: n for n, bid in assignments(wb).items() if bid}
    out = []
    for row in wb['Bobine'].iter_rows(min_row=2):
        if not row[0].value:
            continue
        vals = [c.value for c in row]
        removed = len(vals) > 10 and vals[10] == 'Eliminata'
        if removed and not include_removed:
            continue
        weight, used = float(vals[4] or 0), float(vals[5] or 0)
        remaining = max(0, weight - used)
        bid = str(vals[0])
        out.append(dict(row=row[0].row, id=bid, eliminata=removed, materiale=str(vals[1] or ''), marca=str(vals[2] or ''),
                        colore=str(vals[3] or ''), peso=weight, usati=used, rim=remaining,
                        pct=remaining / weight * 100 if weight else 0, ugello=loaded.get(bid),
                        stato=f'Ugello {loaded[bid]}' if bid in loaded else ('Esaurita' if remaining == 0 else 'Magazzino')))
    return out


def health(pct):
    if pct <= 0: return 'Esaurita', 'red'
    if pct <= 20: return 'Scorta critica', 'red'
    if pct <= 40: return 'In diminuzione', 'amber'
    return 'Buona disponibilità', 'green'


def sync_states(wb):
    for b in bobine(wb):
        wb['Bobine'].cell(b['row'], 9, 'Esaurita' if not b['rim'] else ('Caricata' if b['ugello'] else 'Disponibile'))


def set_assignments(wb, choices):
    ids = [x for x in choices.values() if x]
    if len(ids) != len(set(ids)):
        raise ValueError('Ogni bobina può essere caricata su un solo ugello. Controlla le selezioni.')
    bs = {b['id']: b for b in bobine(wb)}
    for bid in ids:
        if bid not in bs or bs[bid]['rim'] <= 0:
            raise ValueError(f'{bid}: scegli una bobina con materiale disponibile.')
    for n in (1, 2, 3):
        wb['Ugelli'].cell(n + 1, 2).value = choices.get(n, '')
    sync_states(wb)


def record_print(wb, name, consumption, note='', when=None):
    if not name.strip(): raise ValueError('Inserisci il nome della stampa.')
    if any(not math.isfinite(g) or g < 0 for g in consumption.values()):
        raise ValueError('I consumi devono essere numeri positivi o zero.')
    if sum(consumption.values()) <= 0: raise ValueError('Inserisci un consumo maggiore di zero per almeno un ugello.')
    ass = assignments(wb)
    bids = [x for x in ass.values() if x]
    if len(bids) != len(set(bids)):
        raise ValueError('La stessa bobina è assegnata a più ugelli. Correggi il setup prima di registrare.')
    bs = {b['id']: b for b in bobine(wb)}
    for n, g in consumption.items():
        if not g: continue
        b = bs.get(ass.get(n))
        if not b: raise ValueError(f'Ugello {n}: carica una bobina prima di inserire il consumo.')
        if g > b['rim']: raise ValueError(f"Ugello {n} · {b['id']}: richiesti {g:g} g, disponibili {b['rim']:g} g.")
    now, pid = when or datetime.now(), str(uuid4())
    ws = wb['Stampe']
    ws.cell(1, 8, 'ID Stampa')
    for n, g in consumption.items():
        if g <= 0: continue
        b = bs[ass[n]]
        wb['Bobine'].cell(b['row'], 6, b['usati'] + g)
        ws.append([now, name.strip(), n, b['id'], b['materiale'], g, note.strip(), pid])
    sync_states(wb)


def history(wb):
    groups = {}
    for row_number, row in enumerate(wb['Stampe'].iter_rows(min_row=2, values_only=True), 2):
        if not row[0] and not row[1]: continue
        raw = row[0]
        if isinstance(raw, datetime): date = raw
        else:
            try: date = datetime.fromisoformat(str(raw))
            except (ValueError, TypeError): date = datetime.min
        key = row[7] if len(row) > 7 and row[7] else (str(raw), row[1], row[6])
        item = groups.setdefault(key, dict(data=date, nome=str(row[1] or ''), note=str(row[6] or ''), consumi=[], totale=0.0, rows=[], key=str(row[7]) if len(row) > 7 and row[7] else f'legacy-{row_number}'))
        item['rows'].append(row_number)
        grams = float(row[5] or 0)
        item['consumi'].append(dict(ugello=row[2], bobina=row[3], materiale=row[4], grammi=grams))
        item['totale'] += grams
    return sorted(groups.values(), key=lambda x: x['data'], reverse=True)


def add_spool(wb, material, brand, color, weight):
    if not material.strip() or not color.strip(): raise ValueError('Inserisci materiale e colore della bobina.')
    if not math.isfinite(weight) or weight <= 0: raise ValueError('Il peso netto deve essere maggiore di zero.')
    bs = bobine(wb, include_removed=True)
    ids = [int(b['id'][1:]) for b in bs if b['id'].startswith('B') and b['id'][1:].isdigit()]
    bid = f'B{max(ids, default=0) + 1:03d}'
    r = max([b['row'] for b in bs], default=1) + 1
    values = [bid, material.strip(), brand.strip(), color.strip(), weight, 0,
              f'=MAX(0,E{r}-F{r})', f'=IFERROR(G{r}/E{r},0)', 'Disponibile']
    for c, v in enumerate(values, 1): wb['Bobine'].cell(r, c, v)
    wb['Bobine'].cell(r, 8).number_format = '0%'
    return bid


def restock(bs):
    groups = defaultdict(list)
    for b in bs: groups[(b['materiale'].casefold(), b['colore'].casefold())].append(b)
    out = []
    for group in groups.values():
        # Use one reference spool, so empty historic spools do not inflate the threshold.
        reference = max(b['peso'] for b in group)
        remaining = sum(b['rim'] for b in group)
        if remaining <= reference * .2:
            out.append({'Materiale': group[0]['materiale'], 'Colore': group[0]['colore'],
                        'Disponibili (g)': remaining, 'Soglia (g)': reference * .2,
                        'Ricambi in magazzino': sum(b['rim'] > 0 and not b['ugello'] for b in group),
                        'Priorità': 'Esaurito' if remaining == 0 else 'Da acquistare'})
    return sorted(out, key=lambda x: x['Disponibili (g)'])


def remove_spool(wb, bid):
    spool = next((b for b in bobine(wb) if b['id'] == bid), None)
    if spool is None:
        raise ValueError('Bobina non trovata nel magazzino.')
    if bid in assignments(wb).values():
        raise ValueError('Scarica prima la bobina dall’ugello nella Panoramica.')
    # Keep the row and ID so print history retains color/brand and IDs are never reused.
    wb['Bobine'].cell(1, 11, 'Archivio')
    wb['Bobine'].cell(spool['row'], 11, 'Eliminata')


def restore_spool(wb, bid):
    spool = next((b for b in bobine(wb, include_removed=True) if b['id'] == bid and b['eliminata']), None)
    if spool is None:
        raise ValueError('Bobina non trovata tra quelle eliminate.')
    wb['Bobine'].cell(spool['row'], 11).value = None
    sync_states(wb)


def material_group(material):
    material = material.strip().casefold()
    if material.startswith('abs'):
        return 'ABS'
    if material.startswith(('supporto', 'support')) or material in ('pva', 'bvoh'):
        return 'Supporto'
    return 'Altro'


def update_spool(wb, bid, material, brand, color, weight, used):
    b = next((b for b in bobine(wb, include_removed=True) if b['id'] == bid), None)
    if not b: raise ValueError('Bobina non trovata.')
    if not material.strip() or not color.strip(): raise ValueError('Inserisci materiale e colore.')
    if not all(math.isfinite(x) for x in (weight, used)) or weight <= 0 or not 0 <= used <= weight:
        raise ValueError('Il peso deve essere positivo e il consumo compreso tra zero e il peso iniziale.')
    recorded = sum(x['grammi'] for p in history(wb) for x in p['consumi'] if str(x['bobina']) == bid)
    if used < recorded - 1e-8:
        raise ValueError(f'Lo storico contiene già {recorded:g} g: correggi prima i consumi delle stampe.')
    ws = wb['Bobine']
    for col, value in enumerate([material.strip(), brand.strip(), color.strip(), weight, used], 2):
        ws.cell(b['row'], col, value)
    # The material correction applies to every historical use of this spool.
    for row in wb['Stampe'].iter_rows(min_row=2):
        if str(row[3].value) == bid: row[4].value = material.strip()
    sync_states(wb)


def update_print(wb, key, name, when, note, consumption):
    original = next((p for p in history(wb) if p['key'] == key), None)
    if not original: raise ValueError('Stampa non trovata. Ricarica lo storico.')
    if not name.strip(): raise ValueError('Inserisci il nome della stampa.')
    if not isinstance(when, datetime): raise ValueError('Inserisci data e ora valide.')
    bs = {b['id']: b for b in bobine(wb, include_removed=True)}
    old, new = defaultdict(float), defaultdict(float)
    for x in original['consumi']: old[str(x['bobina'])] += x['grammi']
    rows = []
    for x in consumption:
        try:
            g = float(x['grammi'])
            n = float(x['ugello'])
        except (ValueError, TypeError, KeyError):
            raise ValueError('Controlla ugello e grammi di ogni riga.')
        if not math.isfinite(g) or g < 0: raise ValueError('I grammi devono essere positivi o zero.')
        if n not in (1, 2, 3): raise ValueError('Scegli un ugello tra 1, 2 e 3.')
        if g == 0: continue
        bid = str(x.get('bobina') or '')
        if bid not in bs: raise ValueError('Scegli una bobina valida per ogni consumo.')
        rows.append([int(n), bid, bs[bid]['materiale'], g])
        new[bid] += g
    if not rows: raise ValueError('La stampa deve contenere almeno un consumo maggiore di zero.')
    updated = {}
    for bid in old.keys() | new.keys():
        if bid not in bs: raise ValueError(f'Bobina {bid} non trovata: impossibile correggere i consumi.')
        used = bs[bid]['usati'] - old[bid] + new[bid]
        if used < -1e-8 or used > bs[bid]['peso'] + 1e-8:
            raise ValueError(f'{bid}: la correzione produce un consumo totale di {used:g} g su {bs[bid]["peso"]:g} g. Controlla i valori.')
        updated[bid] = min(bs[bid]['peso'], max(0, used))
    # All checks finish before changing the workbook; other prints remain untouched.
    for bid, used in updated.items(): wb['Bobine'].cell(bs[bid]['row'], 6, used)
    ws = wb['Stampe']
    pid = ws.cell(original['rows'][0], 8).value or str(uuid4())
    ws.cell(1, 8, 'ID Stampa')
    for index, use in enumerate(rows):
        values = [when, name.strip(), *use, note.strip(), pid]
        if index < len(original['rows']):
            for c, value in enumerate(values, 1): ws.cell(original['rows'][index], c).value = value
        else: ws.append(values)
    for r in original['rows'][len(rows):]:
        for cell in ws[r]: cell.value = None
    sync_states(wb)


def delete_print(wb, key):
    original = next((p for p in history(wb) if p['key'] == key), None)
    if not original:
        raise ValueError('Stampa non trovata. Ricarica lo storico.')
    bs = {b['id']: b for b in bobine(wb, include_removed=True)}
    refunds = defaultdict(float)
    for use in original['consumi']:
        refunds[str(use['bobina'])] += use['grammi']
    for bid, grams in refunds.items():
        if bid not in bs:
            raise ValueError(f'Bobina {bid} non trovata: impossibile ripristinare i consumi.')
        if not math.isfinite(grams) or grams < 0 or bs[bid]['usati'] < grams - 1e-8:
            raise ValueError(f'{bid}: i consumi della bobina non corrispondono allo storico. Correggili prima di eliminare la stampa.')
    for bid, grams in refunds.items():
        wb['Bobine'].cell(bs[bid]['row'], 6, max(0, bs[bid]['usati'] - grams))
    # Clear records without shifting the row-based identifiers of older prints.
    for r in original['rows']:
        for cell in wb['Stampe'][r]:
            cell.value = None
    sync_states(wb)
