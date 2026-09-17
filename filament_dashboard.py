from datetime import datetime, timedelta
from html import escape
import csv
import io
import streamlit as st
from streamlit_calendar import calendar
import importlib
import filament_store
import filament_sync
if not all(hasattr(filament_sync, name) for name in (
        'pull_project', 'authenticate_github', 'clear_legacy_github_username')):
    importlib.reload(filament_sync)
from filament_sync import (
    sync_project, pull_project, authenticate_github, SyncError,
)

# An already-running Streamlit session may retain the module from before an update.
# Reload only when the required inventory API is missing, before importing its names.
if not all(hasattr(filament_store, name) for name in (
        'remove_spool', 'restore_spool', 'material_group', 'update_spool',
        'update_print', 'delete_print', 'planned_prints', 'add_planned_print',
        'schedule_planned_print', 'unschedule_planned_print',
        'complete_planned_print', 'delete_planned_print')):
    importlib.invalidate_caches()
    importlib.reload(filament_store)

from filament_store import (
    FILE, load, save, bobine, assignments, history, health, restock,
    set_assignments, record_print, add_spool, remove_spool, restore_spool,
    material_group, update_spool, update_print, delete_print, planned_prints,
    add_planned_print, schedule_planned_print, unschedule_planned_print,
    complete_planned_print, delete_planned_print,
)

st.set_page_config(page_title='Filament ·  MITIC lab', page_icon='◉', layout='wide')
st.markdown('''<style>
:root{--ink:#23332f;--muted:#65746d;--green:#23725a;--line:#dfe6df}
.stApp{background:#f5f7f3;color:var(--ink)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stMainBlockContainer"]{max-width:1440px;padding:2.5rem 3rem 4rem}
[data-testid="stSidebar"]{background:#e9eee7;border-right:1px solid #dce3da}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:1.2rem}
h1,h2,h3{color:var(--ink);letter-spacing:-.035em}h1{font-size:2.65rem!important;font-weight:650!important}h2{font-size:1.45rem!important}h3{font-size:1.1rem!important}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px 22px}
[data-testid="stMetricLabel"]{color:var(--muted)}[data-testid="stMetricValue"]{font-size:2rem!important}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:14px!important}
[data-testid="stForm"],[data-testid="stExpander"]{background:#fff;border-radius:14px}
.stButton button,.stFormSubmitButton button,.stDownloadButton button{border-radius:9px;min-height:42px}
button[kind="primary"],button[kind="primaryFormSubmit"]{background:#23725a;border-color:#23725a;color:white}
[data-testid="stRadio"] label{padding:6px 0}
.brand{font-size:29px;font-weight:750;letter-spacing:-1.3px}.brand span{color:#23725a}.kicker{color:#65746d;font-size:11px;letter-spacing:2px;font-weight:700;text-transform:uppercase;margin-bottom:6px}
.lead{color:#65746d;font-size:15px;line-height:1.6;margin:-6px 0 25px}
.card{background:#fff;border:1px solid #dfe6df;border-radius:16px;padding:23px;min-height:275px;margin-bottom:12px;position:relative;overflow:hidden}
.card-top{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:23px}.slot{font-size:12px;letter-spacing:1.4px;font-weight:750}.tag{border-radius:20px;padding:5px 10px;font-size:11px;font-weight:650;background:#edf3ef;color:#3d6654}
.material{font-size:25px;letter-spacing:-.7px;font-weight:700;margin-top:9px}.meta{color:#65746d;font-size:13px;margin:4px 0 23px}.weight{display:flex;justify-content:space-between;align-items:baseline;margin:10px 0}.weight strong{font-size:29px;letter-spacing:-1px}.weight span{color:#65746d;font-size:13px}
.track{height:8px;background:#eef1ed;border-radius:20px;overflow:hidden}.fill{height:100%;border-radius:20px}.status{font-size:12px;font-weight:600;margin-top:10px}.green{color:#23725a}.amber{color:#986210}.red{color:#b54236}.fill.green{background:#378768}.fill.amber{background:#d3a13d}.fill.red{background:#cc6352}
.swatch{display:inline-block;width:12px;height:12px;border-radius:50%;border:1px solid #cbd2cc;margin-right:7px}.empty{border:1px dashed #c9d3c7;background:#f0f4ed}.empty .material{color:#7c8980}.hint{font-size:13px;color:#65746d;line-height:1.6}.notice{background:#fbf1e5;border:1px solid #ead7b7;padding:17px 21px;border-radius:12px;color:#795326;margin:22px 0}.activity{display:flex;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid #e6ebe3}.activity small{color:#65746d}.activity strong{font-size:14px}.footer{color:#7b877d;font-size:12px;margin-top:30px}.hero-count{font-size:12px;color:#23725a;border:1px solid #b8cfbd;background:#edf4ec;border-radius:20px;padding:7px 12px;display:inline-block;margin-bottom:10px}
[class*="st-key-stock_card_"]{background:#fff;border-radius:14px}
[class*="st-key-stock_card_"] [data-testid="stVerticalBlock"]{gap:8px}
[class*="st-key-stock_card_"] button{min-height:30px;padding:3px 10px;font-size:12px}
[class*="st-key-delete_"] button:not(:disabled){color:#a64035}
[class*="st-key-print_card_"]{background:#fff;border-radius:14px}
[class*="st-key-print_card_"] .print-card{border:0;padding:4px;margin:0}
.card.compact-spool{min-height:0;padding:0;border:0;border-radius:0;margin:0;overflow:visible}
.compact-spool .card-top{margin-bottom:8px}.compact-spool .material{font-size:19px;margin-top:0}.compact-spool .meta{font-size:12px;margin:3px 0 10px}.compact-spool .weight{margin:6px 0}.compact-spool .weight strong{font-size:24px}.compact-spool .status{margin-top:6px;font-size:11px}.compact-spool .track{height:6px}.compact-spool .tag{padding:3px 8px}
.stock-heading{border-bottom:2px solid #b8cdbd;padding:4px 0 16px;margin-bottom:18px}.stock-heading h2{margin:0;padding-bottom:4px}.nozzle-card{border-top:4px solid #23725a;padding:26px;min-height:315px}.nozzle-card .slot{font-size:32px;letter-spacing:-1px;font-weight:750}.nozzle-card .card-top{margin-bottom:23px}.nozzle-card .material{font-size:23px}.nozzle-card .meta{margin-bottom:28px}
.print-card{background:white;border:1px solid var(--line);border-radius:14px;padding:22px;margin:12px 0 18px}.print-head{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;margin-bottom:18px}.print-name{font-size:19px;font-weight:700;overflow-wrap:anywhere}.print-date{font-size:12px;color:var(--muted);margin-top:4px}.print-total{text-align:right;white-space:nowrap;font-size:23px;font-weight:700}.print-total small{display:block;font-size:11px;font-weight:400;color:var(--muted)}.print-uses{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.print-use{background:#f5f7f3;border-radius:10px;padding:14px;overflow-wrap:anywhere}.print-use strong{display:block;font-size:15px;margin:9px 0 5px}.print-use .use-grams{font-size:20px;font-weight:700;margin-top:12px}.print-unused{color:#77847b;background:#fafbf9}.print-notes{border-top:1px solid var(--line);margin-top:16px;padding-top:12px;font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}.print-notes span{color:var(--muted)}
.plan-summary{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:8px 0 4px}.plan-summary .print-name{font-size:17px}.plan-meta{color:var(--muted);font-size:12px;margin-top:5px;line-height:1.5}.plan-time{font-weight:700;color:var(--green)}
@media(max-width:760px){.print-uses{grid-template-columns:1fr}.nozzle-card .slot{font-size:29px}}
@media(max-width:760px){[data-testid="stMainBlockContainer"]{padding:1.5rem 1rem}h1{font-size:2rem!important}.card{min-height:245px}}
</style>''', unsafe_allow_html=True)


def html(value): st.markdown(value, unsafe_allow_html=True)
def e(value): return escape(str(value))
def grams(value): return f'{value:,.1f}'.replace(',', ' ').replace('.0', '').replace('.', ',')
def duration_label(minutes):
    hours, minutes = divmod(int(minutes or 0), 60)
    if hours and minutes: return f'{hours} h {minutes} min'
    if hours: return f'{hours} h'
    return f'{minutes} min'
def weekday_label(value): return ('Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom')[value.weekday()]
def jump(page): st.session_state['page'] = page

def commit(action, message, reset_print=False, reset_spool=False, next_page=None):
    try:
        action()
        save(wb)
    except (ValueError, OSError) as exc:
        st.error(str(exc))
    else:
        st.session_state.pop('editor', None)
        st.session_state['flash'] = message
        if reset_print:
            st.session_state['reset_print'] = True
            st.session_state['next_page'] = next_page or 'Panoramica'
        if reset_spool:
            st.session_state['reset_spool'] = True
        st.rerun()


def parse_calendar_datetime(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def normalize_spool_choices(rows):
    return [dict(row, bobina=spool_ids_by_label.get(str(row.get('bobina')), str(row.get('bobina') or ''))) for row in rows]


def spool_card(b, n=None, compact=False):
    top = f'Ugello {n}' if n else e(b['id'])
    card_class = 'card nozzle-card' if n else ('card compact-spool' if compact else 'card')
    if not b:
        html(f'<div class="{card_class} empty"><div class="card-top"><span class="slot">{top}</span><span class="tag">Libero</span></div><div class="material">Pronto per una bobina</div><div class="meta">Nessun materiale caricato</div><p class="hint">Assegna una bobina dal magazzino<br>per registrare i consumi di questo ugello.</p></div>')
        return
    label, tone = health(b['pct'])
    color = {'nero':'#303732','bianco':'#fafafa','arancione':'#e79845','rosso':'#c45848','blu':'#5488b4','verde':'#619273','grigio':'#9da49f','giallo':'#e1c34c'}.get(b['colore'].casefold(), '#b6aaa0')
    pct = min(100, max(0, b['pct']))
    html(f'''<div class="{card_class}"><div class="card-top"><span class="slot">{top}</span><span class="tag">{e('Caricata' if n else b['stato'])}</span></div>
    <div class="material">{e(b['materiale'])} <span style="font-weight:400">/ {e(b['colore'])}</span></div>
    <div class="meta"><span class="swatch" style="background:{color}"></span>{e(b['marca'] or 'Marca non indicata')} · {e(b['id'])}</div>
    <div class="weight"><strong>{grams(b['rim'])} <span>g</span></strong><span>{pct:.0f}% di {grams(b['peso'])} g</span></div>
    <div class="track" role="meter" aria-label="Percentuale residua" aria-valuenow="{pct:.1f}" aria-valuemin="0" aria-valuemax="100"><div class="fill {tone}" style="width:{pct}%"></div></div>
    <div class="status {tone}">● {label}</div></div>''')


def print_card_content(p):
    uses = []
    for n in (1, 2, 3):
        records = [x for x in p['consumi'] if x['ugello'] == n]
        if not records:
            uses.append(f'<div class="print-use print-unused"><div class="slot">Ugello #{n}</div><strong>Non utilizzato</strong><div class="hint">Nessun consumo registrato</div></div>')
            continue
        details = []
        for use in records:
            spool = history_spools.get(str(use['bobina']), {})
            material = e(use['materiale'] or 'Materiale non indicato')
            color = e(spool.get('colore') or 'Colore non disponibile')
            brand = e(spool.get('marca') or 'Marca non disponibile')
            details.append(f'<strong>{material} / {color}</strong><div class="hint">{e(use["bobina"])} · {brand}</div><div class="use-grams">{grams(use["grammi"])} g</div>')
        uses.append(f'<div class="print-use"><div class="slot">Ugello #{n}</div>{"".join(details)}</div>')
    date = p['data'].strftime('%d/%m/%Y · %H:%M:%S') if p['data'] != datetime.min else 'Data non disponibile'
    if p.get('durata'):
        date += f' · durata {duration_label(p["durata"])}'
    count = len({x['ugello'] for x in p['consumi']})
    note = e(p['note']) if p['note'] else '<span>Nessuna nota aggiunta.</span>'
    html(f'<article class="print-card"><div class="print-head"><div><div class="print-name">{e(p["nome"])}</div><div class="print-date">{date} · {count} ugelli utilizzati</div></div><div class="print-total">{grams(p["totale"])} g<small>Consumo totale</small></div></div><div class="print-uses">{"".join(uses)}</div><div class="print-notes"><b>Note</b> · {note}</div></article>')


def close_editor():
    st.session_state.pop('editor', None)


@st.dialog('Modifica bobina', on_dismiss=close_editor)
def edit_spool_dialog(b):
    st.caption(f'Bobina {b["id"]} · Le modifiche aggiornano anche i dettagli nello storico.')
    with st.form(f'edit_spool_form_{b["id"]}'):
        material = st.text_input('Materiale', value=b['materiale'], key='edit_material')
        brand = st.text_input('Marca', value=b['marca'], key='edit_brand')
        color = st.text_input('Colore', value=b['colore'], key='edit_color')
        a, c = st.columns(2)
        weight = a.number_input('Peso iniziale netto (g)', min_value=0.1, value=float(b['peso']), step=100.0)
        used = c.number_input('Consumo totale (g)', min_value=0.0, value=float(b['usati']), step=0.1)
        st.caption('Il consumo totale include le stampe e l’eventuale uso precedente. Per correggere una singola stampa, usa Modifica nello storico.')
        save_action, cancel = st.columns(2)
        submitted = save_action.form_submit_button('Salva modifiche', type='primary', width='stretch')
        cancelled = cancel.form_submit_button('Annulla', width='stretch')
    if cancelled:
        close_editor()
        st.rerun()
    if submitted:
        commit(lambda: update_spool(wb, b['id'], material, brand, color, weight, used), f'Bobina {b["id"]} aggiornata.')


@st.dialog('Modifica stampa', width='large', on_dismiss=close_editor)
def edit_print_dialog(p):
    st.caption('Correggi i dati della stampa: i vecchi consumi saranno sostituiti e le scorte ricalcolate. Le bobine sono quelle della stampa, indipendentemente dal setup attuale.')
    with st.form(f'edit_print_form_{p["key"]}'):
        name = st.text_input('Nome stampa', value=p['nome'], key='edit_print_name')
        date_col, time_col = st.columns(2)
        date = date_col.date_input('Data', value=p['data'].date() if p['data'] != datetime.min else datetime.now().date())
        time = time_col.time_input('Ora', value=p['data'].time(), step=60)
        duration_col, minutes_col = st.columns(2)
        initial_hours, initial_minutes = divmod(int(p.get('durata') or 0), 60)
        duration_hours = duration_col.number_input('Durata · ore', min_value=0, value=initial_hours, step=1, key='edit_print_duration_hours')
        duration_minutes = minutes_col.number_input('Durata · minuti', min_value=0, max_value=59, value=initial_minutes, step=1, key='edit_print_duration_minutes')
        options = [spool_labels_by_id[b['id']] for b in all_spools]
        st.caption('Puoi cambiare ugello, bobina e grammi, aggiungere righe o rimuoverle. Le bobine eliminate restano selezionabili per correggere le stampe passate.')
        edited = st.data_editor(
            [{'ugello': x['ugello'], 'bobina': spool_labels_by_id.get(str(x['bobina']), str(x['bobina'])), 'grammi': x['grammi']} for x in p['consumi']],
            num_rows='dynamic', hide_index=True, width='stretch', key=f'edit_consumption_{p["key"]}',
            column_config={
                'ugello': st.column_config.SelectboxColumn('Ugello', options=[1, 2, 3], required=True),
                'bobina': st.column_config.SelectboxColumn('Bobina · materiale / colore', options=options, required=True, width='large'),
                'grammi': st.column_config.NumberColumn('Consumo (g)', min_value=0.0, step=0.1, required=True),
            })
        note = st.text_area('Note', value=p['note'], key='edit_print_note')
        a, b = st.columns(2)
        submitted = a.form_submit_button('Salva modifiche', type='primary', width='stretch')
        cancelled = b.form_submit_button('Annulla', width='stretch')
    if cancelled:
        close_editor()
        st.rerun()
    if submitted:
        duration = int(duration_hours) * 60 + int(duration_minutes)
        commit(lambda: update_print(wb, p['key'], name, datetime.combine(date, time), note, normalize_spool_choices(edited), duration or None), 'Stampa corretta e scorte aggiornate.')


@st.dialog('Inserisci nel calendario', on_dismiss=close_editor)
def schedule_print_dialog(p):
    now = datetime.now().replace(second=0, microsecond=0)
    rounded = now + timedelta(minutes=(15 - now.minute % 15) % 15)
    initial = p['inizio'] or rounded
    st.caption(f'«{p["nome"]}» · trova uno spazio libero: il blocco occuperà esattamente la durata indicata.')
    with st.form(f'schedule_print_form_{p["key"]}'):
        day_col, time_col = st.columns(2)
        day = day_col.date_input('Giorno', value=initial.date(), key=f'schedule_day_{p["key"]}')
        clock = time_col.time_input('Ora di inizio', value=initial.time(), step=900, key=f'schedule_time_{p["key"]}')
        hours, minutes = divmod(int(p['durata']), 60)
        hour_col, minute_col = st.columns(2)
        duration_hours = hour_col.number_input('Durata · ore', min_value=0, value=hours, step=1, key=f'schedule_hours_{p["key"]}')
        duration_minutes = minute_col.number_input('Durata · minuti', min_value=0, max_value=59, value=minutes, step=1, key=f'schedule_minutes_{p["key"]}')
        start = datetime.combine(day, clock)
        duration = int(duration_hours) * 60 + int(duration_minutes)
        if duration:
            st.info(f'Fine prevista: {(start + timedelta(minutes=duration)).strftime("%d/%m/%Y alle %H:%M")}')
        save_action, cancel = st.columns(2)
        submitted = save_action.form_submit_button('Salva nel calendario', type='primary', width='stretch')
        cancelled = cancel.form_submit_button('Annulla', width='stretch')
    if cancelled:
        close_editor()
        st.rerun()
    if submitted:
        st.session_state['calendar_focus_date'] = day
        st.session_state['calendar_nonce'] = st.session_state.get('calendar_nonce', 0) + 1
        commit(lambda: schedule_planned_print(wb, p['key'], start, duration), 'Pianificazione aggiornata.')


@st.dialog('Completa stampa pianificata', width='large', on_dismiss=close_editor)
def complete_print_dialog(p):
    st.caption('Conferma data e consumi effettivi. Solo ora i grammi verranno scalati dalle bobine e la stampa passerà nello storico.')
    with st.form(f'complete_print_form_{p["key"]}'):
        now = datetime.now().replace(second=0, microsecond=0)
        day_col, time_col = st.columns(2)
        day = day_col.date_input('Data effettiva', value=now.date(), key=f'complete_day_{p["key"]}')
        clock = time_col.time_input('Ora effettiva', value=now.time(), step=60, key=f'complete_time_{p["key"]}')
        options = [spool_labels_by_id[b['id']] for b in all_spools if not b['eliminata']]
        actual = st.data_editor(
            [{'ugello': x['ugello'], 'bobina': spool_labels_by_id.get(str(x['bobina']), str(x['bobina'])), 'grammi': x['grammi']} for x in p['consumi']],
            num_rows='dynamic', hide_index=True, width='stretch', key=f'complete_consumption_{p["key"]}',
            column_config={
                'ugello': st.column_config.SelectboxColumn('Ugello', options=[1, 2, 3], required=True),
                'bobina': st.column_config.SelectboxColumn('Bobina · materiale / colore', options=options, required=True, width='large'),
                'grammi': st.column_config.NumberColumn('Consumo effettivo (g)', min_value=0.0, step=0.1, required=True),
            })
        confirm, cancel = st.columns(2)
        submitted = confirm.form_submit_button('Completa e aggiorna scorte', type='primary', width='stretch')
        cancelled = cancel.form_submit_button('Annulla', width='stretch')
    if cancelled:
        close_editor()
        st.rerun()
    if submitted:
        commit(lambda: complete_planned_print(wb, p['key'], datetime.combine(day, clock), normalize_spool_choices(actual)), 'Stampa completata: consumi aggiornati e voce aggiunta allo storico.')


def print_card(p, can_delete=False):
    with st.container(border=True, key=f'print_card_{p["key"]}'):
        print_card_content(p)
        edit, delete, _ = st.columns([1, 1, 3])
        if edit.button('Modifica', icon=':material/edit:', key=f'edit_print_{p["key"]}', width='stretch'):
            st.session_state['editor'] = ('print', p['key'])
        if can_delete and delete.button('Elimina', icon=':material/delete:', key=f'delete_print_{p["key"]}', width='stretch',
                                        help='Elimina la stampa e restituisce i grammi consumati alle bobine coinvolte.'):
            commit(lambda: delete_print(wb, p['key']), f'Stampa «{p["nome"]}» eliminata. Ripristinati {grams(p["totale"])} g sulle bobine.')


def setup():
    with st.expander('Cambia bobine / configura i tre ugelli'):
        st.caption('Una bobina per ugello. Le bobine rimosse tornano automaticamente in magazzino; i consumi restano salvati.')
        with st.form('setup'):
            choices = {}
            for n, col in enumerate(st.columns(3), 1):
                options = [''] + [b['id'] for b in bs if b['rim'] > 0 or ass.get(n) == b['id']]
                current = ass.get(n, '')
                choices[n] = col.selectbox(f'Ugello {n}', options, index=options.index(current) if current in options else 0,
                    format_func=lambda bid: 'Nessuna bobina' if not bid else f"{bid} · {byid[bid]['materiale']} {byid[bid]['colore']} · {grams(byid[bid]['rim'])} g")
            if st.form_submit_button('Salva configurazione', type='primary'):
                commit(lambda: set_assignments(wb, choices), 'Configurazione aggiornata. Le bobine sono pronte.')


def csv_bytes(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=';')
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue().encode('utf-8-sig')


def recover_updates():
    with st.spinner('Controllo aggiornamenti su GitHub…'):
        try:
            changed, message = pull_project(FILE.parent)
        except (SyncError, OSError) as exc:
            st.session_state['pull_result'] = ('warning', str(exc))
        else:
            st.session_state['pull_result'] = ('success', message)
            if changed:
                st.session_state.pop('editor', None)
            return changed
    return False


if not st.session_state.get('pull_checked'):
    st.session_state['pull_checked'] = True
    if recover_updates():
        st.rerun()

try:
    wb = load()
    bs = bobine(wb); ass = assignments(wb); prints = history(wb); plans = planned_prints(wb)
except (OSError, KeyError, ValueError) as exc:
    st.error(f'Impossibile leggere il magazzino: {exc}')
    st.stop()
byid = {b['id']: b for b in bs}
all_spools = bobine(wb, include_removed=True)
history_spools = {b['id']: b for b in all_spools}
spool_labels_by_id = {
    b['id']: f"{b['id']} · {b['materiale']} / {b['colore']}" + (' · eliminata' if b['eliminata'] else '')
    for b in all_spools
}
spool_ids_by_label = {label: bid for bid, label in spool_labels_by_id.items()}
if st.session_state.get('page') == 'Riacquisti':
    st.session_state['page'] = 'Panoramica'
to_buy = restock(bs)
loaded = sum(bool(byid.get(ass.get(n))) for n in (1, 2, 3))
warehouse = [b for b in bs if not b['ugello'] and b['rim'] > 0]

if 'next_page' in st.session_state:
    st.session_state['page'] = st.session_state.pop('next_page')

with st.sidebar:
    html('<div class="brand"><span>◉</span> filament<span>.</span></div><div class="kicker">MITIC Lab</div>')
    st.radio('Workspace', ['Panoramica', 'Nuova stampa', 'Pianificazione', 'Magazzino', 'Storico'], key='page', label_visibility='collapsed')
    st.divider()
    html(f'<div class="kicker">Stampante / 3 ugelli</div><div class="hint">{loaded} ugelli occupati · {len(warehouse)} bobine di ricambio</div>')
    st.caption('Residuo bobine')
    html('<div class="hint"><span class="green">●</span> Oltre il 40% · Disponibile<br><span class="amber">●</span> 21–40% · In diminuzione<br><span class="red">●</span> Fino al 20% · Critico</div>')
    st.divider()
    st.download_button('Scarica archivio Excel', FILE.read_bytes(), FILE.name, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', width='stretch')
    st.caption('Dati salvati localmente · copia di sicurezza automatica a ogni modifica.')
    st.divider()
    st.caption('Aggiornamenti GitHub')
    st.caption('Controllo automatico all’apertura. Le modifiche locali bloccano il pull per proteggere i dati.')
    st.caption('Il push è consentito solo agli account aggiunti come Collaborators della repository.')
    login_windows, login_mac = st.columns(2)
    login_system = None
    if login_windows.button('GitHub · Windows', icon=':material/login:', key='login_github_windows',
                            width='stretch', help='Accesso tramite Gestore credenziali di Windows.'):
        login_system = 'windows'
    if login_mac.button('GitHub · Mac', icon=':material/login:', key='login_github_macos',
                        width='stretch', help='Accesso tramite Git Credential Manager e Portachiavi di macOS.'):
        login_system = 'macos'
    if login_system:
        with st.spinner('Completa l’accesso nella finestra del browser…'):
            try:
                auth_message = authenticate_github(system=login_system)
            except (SyncError, OSError) as exc:
                st.session_state['auth_result'] = ('error', str(exc))
            else:
                st.session_state['auth_result'] = ('success', auth_message)
                st.session_state['pull_checked'] = False
    if 'auth_result' in st.session_state:
        auth_kind, auth_message = st.session_state['auth_result']
        getattr(st, auth_kind)(auth_message)
    if st.button('Recupera aggiornamenti', icon=':material/cloud_download:', key='pull_github', width='stretch'):
        if recover_updates():
            st.rerun()
    if 'pull_result' in st.session_state:
        pull_kind, pull_message = st.session_state['pull_result']
        getattr(st, pull_kind)(pull_message)

    st.caption('Invia codice, configurazione e archivio Excel a GitHub con un commit e push. Le modifiche restano locali fino al clic.')
    if st.button('Sincronizza con GitHub', icon=':material/cloud_upload:', key='sync_github', width='stretch'):
        with st.spinner('Commit e invio a GitHub…'):
            try:
                result = sync_project()
            except (SyncError, OSError) as exc:
                st.session_state['sync_result'] = ('error', str(exc))
            else:
                st.session_state['sync_result'] = ('success', result)
    if 'sync_result' in st.session_state:
        kind, message = st.session_state['sync_result']
        getattr(st, kind)(message)


if st.session_state.pop('reset_print', False):
    for key in list(st.session_state):
        if key.startswith('cons_') or key in (
                'print_name', 'print_note', 'print_mode', 'print_duration_hours',
                'print_duration_minutes'):
            del st.session_state[key]

if st.session_state.pop('reset_spool', False):
    for key in (
            'new_material_choice', 'new_material_custom', 'new_brand_choice',
            'new_brand_custom', 'new_color_choice', 'new_color_custom',
            'new_spool_weight'):
        st.session_state.pop(key, None)

if 'flash' in st.session_state: st.success(st.session_state.pop('flash'))
if 'flash_error' in st.session_state: st.error(st.session_state.pop('flash_error'))
page = st.session_state['page']
html(f'<div class="kicker">WORKSPACE / {e(page)}</div>')

if page == 'Panoramica':
    _, action = st.columns([3, 1])
    with action:
        st.button('＋ Registra una stampa', type='primary', width='stretch', on_click=jump, args=('Nuova stampa',))
    for n, col in enumerate(st.columns(3), 1):
        with col: spool_card(byid.get(ass.get(n)), n)
    setup()
    upcoming = [p for p in plans if p['inizio'] is not None and p['inizio'] + timedelta(minutes=p['durata']) >= datetime.now()]
    if upcoming:
        next_plan = min(upcoming, key=lambda p: p['inizio'])
        html(f'<div class="notice"><strong>Prossima stampa: {e(next_plan["nome"])}</strong><br>{next_plan["inizio"].strftime("%d/%m/%Y alle %H:%M")} · {duration_label(next_plan["durata"])}.</div>')
        st.button('Apri la pianificazione →', on_click=jump, args=('Pianificazione',))
    elif plans:
        st.info(f'{len(plans)} stampe in coda da inserire nel calendario.')
        st.button('Pianifica le stampe →', on_click=jump, args=('Pianificazione',))
    critical = [b for b in bs if b['pct'] <= 20]
    if critical:
        html(f'<div class="notice"><strong>{len(critical)} bobine al 20% o meno.</strong> Controlla i ricambi prima della prossima stampa.</div>')
    st.subheader('Ultima stampa')
    if not prints: st.info('Il tuo storico parte da qui. Registra la prima stampa con i dati dello slicer.')
    for p in prints[:1]:
        print_card(p)
    st.button('Apri lo storico →', on_click=jump, args=('Storico',))
    st.subheader('Da tenere d’occhio')
    if to_buy:
        for row in to_buy[:3]:
            html(f'<div class="activity"><div><strong>{e(row["Materiale"])} / {e(row["Colore"])}</strong><br><small>{row["Ricambi in magazzino"]} ricambi in magazzino</small></div><strong class="red">{grams(row["Disponibili (g)"])} g</strong></div>')
        st.button('Controlla il magazzino →', on_click=jump, args=('Magazzino',))
    else: st.success('Le scorte coprono la soglia minima.')

elif page == 'Nuova stampa':
    st.title('Dallo slicer al magazzino.')
    html('<p class="lead">Registra una stampa conclusa oppure prepara il lavoro e mandalo nella coda di pianificazione.</p>')
    setup()
    mode = st.radio(
        'Stato della stampa', ['Già avvenuta', 'Da programmare'], horizontal=True,
        key='print_mode', help='Le stampe da programmare non scalano il magazzino finché non vengono completate.')
    name = st.text_input('Nome della stampa', placeholder='Es. Supporto sensore · revisione 02', key='print_name')
    if mode == 'Già avvenuta':
        day, clock = st.columns(2)
        date = day.date_input('Data della stampa', value=datetime.now().date(), max_value=datetime.now().date())
        time = clock.time_input('Ora', value=datetime.now().time().replace(second=0, microsecond=0))
    duration_hours_col, duration_minutes_col = st.columns(2)
    duration_hours = duration_hours_col.number_input('Durata · ore', min_value=0, value=1, step=1, key='print_duration_hours')
    duration_minutes = duration_minutes_col.number_input('Durata · minuti', min_value=0, max_value=59, value=0, step=1, key='print_duration_minutes')
    duration = int(duration_hours) * 60 + int(duration_minutes)
    cons = {}
    for n, col in enumerate(st.columns(3), 1):
        with col:
            b = byid.get(ass.get(n))
            spool_card(b, n)
            cons[n] = st.number_input(f'Consumo ugello {n} (g)', min_value=0.0, value=0.0, step=0.1, format='%.1f', disabled=not b, key=f'cons_{n}_{ass.get(n)}')
            if b:
                after = b['rim'] - cons[n]
                if after < 0: st.error(f'Mancano {grams(-after)} g. Controlla consumo o bobina.')
                else: st.caption(f'Dopo la stampa: {grams(after)} g · {after / b["peso"] * 100 if b["peso"] else 0:.0f}%')
    note = st.text_area('Note (facoltative)', placeholder='Impostazioni, commessa o risultato della stampa.', height=90, key='print_note')
    if mode == 'Già avvenuta':
        st.info(f"Totale da scalare: {grams(sum(cons.values()))} g · {sum(g > 0 for g in cons.values())} ugelli utilizzati. Registra una sola volta, a stampa conclusa.")
        if st.button('Registra stampa e aggiorna scorte', type='primary', disabled=not loaded or duration <= 0):
            commit(lambda: record_print(wb, name, cons, note, datetime.combine(date, time), duration), 'Stampa salvata. Consumi e magazzino aggiornati.', reset_print=True)
    else:
        st.info(f"Previsione: {duration_label(duration)} · {grams(sum(cons.values()))} g. Verrà aggiunta alla coda senza scalare le bobine.")
        if st.button('Aggiungi alla coda di pianificazione', type='primary', disabled=not loaded or duration <= 0):
            commit(lambda: add_planned_print(wb, name, cons, duration, note), 'Stampa aggiunta alla coda. Ora puoi inserirla nel calendario.', reset_print=True, next_page='Pianificazione')

elif page == 'Pianificazione':
    st.title('La regia delle stampe.')
    html('<p class="lead">Prepara la coda, assegna un orario e usa i blocchi in calendario per occupare ogni spazio senza sovrapposizioni.</p>')
    queued = [p for p in plans if p['inizio'] is None]
    scheduled = [p for p in plans if p['inizio'] is not None]
    m1, m2, m3 = st.columns(3)
    m1.metric('Da inserire', len(queued))
    m2.metric('In calendario', len(scheduled))
    m3.metric('Tempo pianificato', duration_label(sum(p['durata'] for p in scheduled)))

    demand = {}
    for plan in plans:
        for use in plan['consumi']:
            demand[str(use['bobina'])] = demand.get(str(use['bobina']), 0) + use['grammi']
    risks = [(bid, grams_needed, history_spools.get(bid, {}).get('rim', 0)) for bid, grams_needed in demand.items()
             if grams_needed > history_spools.get(bid, {}).get('rim', 0)]
    if risks:
        details = ' · '.join(f'{bid}: previsti {grams(need)} g, disponibili {grams(available)} g' for bid, need, available in risks)
        st.warning(f'Il piano complessivo supera la disponibilità di alcune bobine. {details}')

    st.subheader('Calendario settimanale')
    st.caption('Trascina un blocco con il mouse per cambiare giorno o ora. Gli spostamenti sono agganciati a intervalli di 15 minuti e vengono salvati al rilascio.')
    calendar_events = [{
        'id': p['key'],
        'title': f"{p['nome']} · {duration_label(p['durata'])} · {grams(p['totale'])} g",
        'start': p['inizio'].isoformat(),
        'end': (p['inizio'] + timedelta(minutes=p['durata'])).isoformat(),
        'backgroundColor': '#28775f' if sum(ord(c) for c in p['key']) % 2 else '#486f86',
        'borderColor': 'transparent',
        'textColor': '#ffffff',
    } for p in scheduled]
    focus_date = st.session_state.get('calendar_focus_date', datetime.now().date())
    if isinstance(focus_date, datetime):
        focus_date = focus_date.date()
    calendar_state = calendar(
        events=calendar_events,
        options={
            'initialView': 'timeGridWeek',
            'initialDate': focus_date.isoformat(),
            'locale': 'it',
            'firstDay': 1,
            'editable': True,
            'eventStartEditable': True,
            'eventDurationEditable': False,
            'eventOverlap': False,
            'slotEventOverlap': False,
            'allDaySlot': False,
            'nowIndicator': True,
            'slotMinTime': '00:00:00',
            'slotMaxTime': '24:00:00',
            'slotDuration': '01:00:00',
            'slotLabelInterval': '01:00:00',
            'snapDuration': '00:15:00',
            'height': 'auto',
            'expandRows': False,
            'headerToolbar': {'left': 'prev,next today', 'center': 'title', 'right': ''},
            'buttonText': {'today': 'Oggi'},
            'eventTimeFormat': {'hour': '2-digit', 'minute': '2-digit', 'hour12': False},
            'slotLabelFormat': {'hour': '2-digit', 'minute': '2-digit', 'hour12': False},
        },
        custom_css='''
            .fc { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #23332f; font-size: 9px; }
            .fc .fc-header-toolbar.fc-toolbar { margin-bottom: 4px; min-height: 25px; }
            .fc .fc-toolbar-title { font-size: 13px; font-weight: 700; }
            .fc .fc-button { font-size: 9px; line-height: 1; padding: 4px 7px; }
            .fc .fc-button-primary { background: #23725a; border-color: #23725a; border-radius: 6px; }
            .fc .fc-button-primary:hover { background: #195d49; border-color: #195d49; }
            .fc .fc-button-primary:disabled { background: #94aaa0; border-color: #94aaa0; }
            .fc .fc-col-header-cell-cushion { font-size: 9px; padding: 2px 3px; }
            .fc .fc-timegrid-slot { height: 12px !important; }
            .fc .fc-timegrid-slot-label-cushion { font-size: 8px; line-height: 1; padding: 0 3px; }
            .fc .fc-timegrid-event { border-radius: 4px; cursor: grab; box-shadow: 0 1px 3px #173f3326; font-size: 8px; line-height: 1; }
            .fc .fc-timegrid-event:active { cursor: grabbing; }
            .fc .fc-event-main { padding: 1px 2px; }
            .fc .fc-event-time { font-size: 7px; }
            .fc .fc-event-title { font-size: 8px; }
            .fc .fc-col-header-cell-cushion, .fc .fc-timegrid-axis-cushion { color: #23332f; }
            .fc .fc-timegrid-now-indicator-line {
                border-color: #d23427;
                border-top-width: 4px;
                margin-top: -2px;
                box-shadow: 0 0 0 1px #ffffff, 0 1px 5px #8f211b80;
            }
            .fc .fc-timegrid-now-indicator-arrow {
                border-top-width: 8px;
                border-bottom-width: 8px;
                border-left-width: 10px;
                border-left-color: #d23427;
                margin-top: -8px;
            }
        ''',
        callbacks=['eventChange'],
        key=f'planning_calendar_{st.session_state.get("calendar_nonce", 0)}',
    )
    if calendar_state and calendar_state.get('callback') == 'eventChange':
        changed = calendar_state.get('eventChange', {}).get('event', {})
        try:
            moved_key = str(changed['id'])
            moved_start = parse_calendar_datetime(changed['start'])
            schedule_planned_print(wb, moved_key, moved_start)
            save(wb)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            st.session_state['flash_error'] = f'Spostamento annullato: {exc}'
        else:
            moved_name = next((p['nome'] for p in scheduled if p['key'] == moved_key), 'Stampa')
            st.session_state['flash'] = f'«{moved_name}» spostata al {moved_start.strftime("%d/%m/%Y alle %H:%M")}.'
            st.session_state['calendar_focus_date'] = moved_start.date()
        st.session_state['calendar_nonce'] = st.session_state.get('calendar_nonce', 0) + 1
        st.rerun()

    st.subheader('Coda da pianificare')
    if not queued:
        st.success('La coda è vuota: tutte le stampe sono state inserite nel calendario.')
    for p in queued:
        with st.container(border=True, key=f'queue_card_{p["key"]}'):
            info, action = st.columns([4, 1.4])
            with info:
                html(f'<div class="plan-summary"><div class="print-name">{e(p["nome"])}</div><div class="plan-meta">{duration_label(p["durata"])} · {grams(p["totale"])} g previsti · {len(p["consumi"])} ugelli</div></div>')
            with action:
                if st.button('Pianifica', icon=':material/calendar_add_on:', key=f'schedule_{p["key"]}', type='primary', width='stretch'):
                    st.session_state['editor'] = ('schedule', p['key'])
                if st.button('Elimina', icon=':material/delete:', key=f'delete_plan_{p["key"]}', width='stretch'):
                    commit(lambda key=p['key']: delete_planned_print(wb, key), f'«{p["nome"]}» rimossa dalla pianificazione.')

    st.subheader('Stampe in calendario')
    if not scheduled:
        st.info('Nessuna stampa calendarizzata. Usa “Pianifica” su una voce della coda.')
    for p in scheduled:
        end = p['inizio'] + timedelta(minutes=p['durata'])
        end_label = end.strftime('%H:%M') if end.date() == p['inizio'].date() else end.strftime('%d/%m · %H:%M')
        with st.container(border=True, key=f'scheduled_card_{p["key"]}'):
            html(f'<div class="plan-summary"><div class="print-name">{e(p["nome"])}</div><div class="plan-meta"><span class="plan-time">{weekday_label(p["inizio"])} {p["inizio"].strftime("%d/%m · %H:%M")}–{end_label}</span> · {duration_label(p["durata"])} · {grams(p["totale"])} g previsti</div></div>')
            move, complete, queue_again, remove = st.columns(4)
            if move.button('Sposta', icon=':material/edit_calendar:', key=f'move_plan_{p["key"]}', width='stretch'):
                st.session_state['editor'] = ('schedule', p['key'])
            if complete.button('Completa', icon=':material/check_circle:', key=f'complete_plan_{p["key"]}', type='primary', width='stretch'):
                st.session_state['editor'] = ('complete', p['key'])
            if queue_again.button('In coda', icon=':material/undo:', key=f'unschedule_plan_{p["key"]}', width='stretch'):
                commit(lambda key=p['key']: unschedule_planned_print(wb, key), f'«{p["nome"]}» rimessa nella coda.')
            if remove.button('Elimina', icon=':material/delete:', key=f'delete_scheduled_{p["key"]}', width='stretch'):
                commit(lambda key=p['key']: delete_planned_print(wb, key), f'«{p["nome"]}» rimossa dalla pianificazione.')

elif page == 'Magazzino':
    st.title('Il tuo magazzino.')
    html('<p class="lead">ABS, supporti e altri materiali: trova subito una bobina e controlla quanto filamento rimane.</p>')
    with st.expander('＋ Aggiungi una bobina acquistata'):
        material_col, brand_col, color_col, weight_col = st.columns(4)
        material_choice = material_col.selectbox(
            'Materiale', ['ABS', 'Supporto', 'PLA', 'Altro'], index=0,
            key='new_material_choice')
        brand_choice = brand_col.selectbox(
            'Marca', ['3ntr', 'Altro'], index=0, key='new_brand_choice')
        color_choice = color_col.selectbox(
            'Colore', [
                'Nero', 'Bianco', 'Grigio', 'Rosso', 'Arancione', 'Giallo',
                'Verde', 'Blu', 'Viola', 'Rosa', 'Marrone', 'Trasparente',
                'Naturale', 'Altro',
            ], index=0, key='new_color_choice')
        weight = weight_col.number_input(
            'Peso netto (g)', min_value=1.0, value=1000.0, step=100.0,
            key='new_spool_weight')

        custom_cols = st.columns(3)
        material_custom = custom_cols[0].text_input(
            'Specifica materiale', key='new_material_custom',
            placeholder='Es. PETG, TPU…') if material_choice == 'Altro' else ''
        brand_custom = custom_cols[1].text_input(
            'Specifica marca', key='new_brand_custom',
            placeholder='Nome produttore') if brand_choice == 'Altro' else ''
        color_custom = custom_cols[2].text_input(
            'Specifica colore', key='new_color_custom',
            placeholder='Nome colore') if color_choice == 'Altro' else ''

        material = material_custom.strip() if material_choice == 'Altro' else material_choice
        brand = brand_custom.strip() if brand_choice == 'Altro' else brand_choice
        color = color_custom.strip() if color_choice == 'Altro' else color_choice
        st.caption('Escludi il peso della bobina vuota. La nuova bobina sarà disponibile in magazzino.')
        if st.button('Aggiungi al magazzino', type='primary', key='add_new_spool'):
            commit(
                lambda: add_spool(wb, material, brand, color, weight),
                'Nuova bobina aggiunta al magazzino.', reset_spool=True)
    a, b, c, d = st.columns([2, 1, 1, 1.4])
    query = a.text_input('Cerca', placeholder='Materiale, colore, marca o ID')
    place = b.selectbox('Posizione', ['Tutte', 'Magazzino', 'Caricate', 'Esaurite'])
    level = c.selectbox('Disponibilità', ['Tutte', 'Critica (≤20%)', 'In diminuzione (21–40%)', 'Buona (>40%)'])
    order = d.selectbox('Ordina per', ['Residuo % crescente', 'Residuo % decrescente', 'Grammi crescenti', 'Grammi decrescenti', 'Colore A–Z', 'ID bobina'])
    visible = [b for b in bs if query.casefold() in ' '.join(str(b[k]) for k in ('id','materiale','marca','colore')).casefold()
        and (place == 'Tutte' or (place == 'Magazzino' and not b['ugello'] and b['rim'] > 0) or (place == 'Caricate' and b['ugello']) or (place == 'Esaurite' and b['rim'] == 0))
        and (level == 'Tutte' or (level.startswith('Critica') and b['pct'] <= 20) or (level.startswith('In diminuzione') and 20 < b['pct'] <= 40) or (level.startswith('Buona') and b['pct'] > 40))]
    sort_keys = {
        'Residuo % crescente': lambda b: (b['pct'], b['id']),
        'Residuo % decrescente': lambda b: (-b['pct'], b['id']),
        'Grammi crescenti': lambda b: (b['rim'], b['id']),
        'Grammi decrescenti': lambda b: (-b['rim'], b['id']),
        'Colore A–Z': lambda b: (b['colore'].casefold(), b['id']),
        'ID bobina': lambda b: b['id'],
    }
    visible.sort(key=sort_keys[order])
    st.caption(f'{len(visible)} bobine visualizzate · {grams(sum(b["rim"] for b in visible))} g disponibili · ordinamento applicato in ogni colonna')
    for group, col in zip(('ABS', 'Supporto', 'Altro'), st.columns(3, gap='medium')):
        with col:
            items = [b for b in visible if material_group(b['materiale']) == group]
            html(f'<div class="stock-heading"><h2>{group}</h2><div class="hint">{len(items)} bobine · <b>{grams(sum(b["rim"] for b in items))} g</b></div></div>')
            if not items:
                st.caption('Nessuna bobina con questi filtri.' if any(material_group(b['materiale']) == group for b in bs) else 'Non hai ancora bobine in questa categoria.')
            for b in items:
                with st.container(border=True, key=f'stock_card_{b["id"]}'):
                    spool_card(b, compact=True)
                    st.caption(f'Consumati: {grams(b["usati"])} g')
                    edit, action = st.columns(2)
                    if edit.button('Modifica', icon=':material/edit:', key=f'edit_spool_{b["id"]}', width='stretch'):
                        st.session_state['editor'] = ('spool', b['id'])
                    help_text = ('Scarica prima la bobina dall’ugello nella Panoramica.' if b['ugello']
                                 else 'Rimuovi dalle scorte. Lo storico resta disponibile; puoi ripristinarla da “Bobine eliminate”.')
                    if action.button('Elimina', icon=':material/delete:', key=f'delete_{b["id"]}',
                                     disabled=bool(b['ugello']), help=help_text, width='stretch'):
                        commit(lambda bid=b['id']: remove_spool(wb, bid), f'Bobina {b["id"]} eliminata dalle scorte. Puoi ripristinarla da “Bobine eliminate”.')
    removed = [b for b in all_spools if b['eliminata']]
    if removed:
        with st.expander(f'Bobine eliminate ({len(removed)})'):
            st.caption('Escluse dalle scorte e dalla selezione degli ugelli. Stampe e dettagli delle bobine rimangono nello storico.')
            for b in removed:
                label, action = st.columns([3, 1])
                label.write(f'{b["id"]} · {b["materiale"]} / {b["colore"]} · {grams(b["rim"])} g')
                if action.button('Ripristina', key=f'restore_{b["id"]}', width='stretch'):
                    commit(lambda bid=b['id']: restore_spool(wb, bid), f'Bobina {b["id"]} ripristinata nel magazzino.')

elif page == 'Storico':
    st.title('Il diario delle tue stampe.')
    html('<p class="lead">Ogni stampa riunisce i consumi dei tre ugelli. Ritrova lavorazioni, materiali e note.</p>')
    query = st.text_input('Cerca nello storico', placeholder='Nome stampa, materiale, note o bobina')
    visible = [p for p in prints if query.casefold() in str(p).casefold()]
    a, b, c = st.columns(3)
    a.metric('Stampe trovate', len(visible))
    b.metric('Consumo totale', f'{grams(sum(p["totale"] for p in visible))} g')
    c.metric('Consumo medio / stampa', f'{grams(sum(p["totale"] for p in visible) / len(visible) if visible else 0)} g')
    if not visible: st.info('Nessuna stampa trovata.' if prints else 'Nessuna stampa registrata. Aggiungi i consumi dalla sezione Nuova stampa.')
    else:
        export = []
        for p in visible:
            for use in p['consumi']:
                export.append({'Data': p['data'].isoformat(sep=' ', timespec='seconds'), 'Stampa': p['nome'], 'Durata (min)': p.get('durata') or '', 'Ugello': use['ugello'], 'Bobina': use['bobina'], 'Materiale': use['materiale'], 'Colore': history_spools.get(str(use['bobina']), {}).get('colore', ''), 'Marca': history_spools.get(str(use['bobina']), {}).get('marca', ''), 'Grammi': use['grammi'], 'Note': p['note']})
        st.download_button('Esporta consumi CSV', csv_bytes(export), 'storico_consumi.csv', 'text/csv')
        pages = max(1, (len(visible) + 19) // 20)
        number = st.number_input('Pagina (20 stampe)', min_value=1, max_value=pages, value=1, step=1)
        for p in visible[(number-1)*20:number*20]:
            print_card(p, can_delete=True)

html('<div class="footer">FILAMENT / Quantità stimate dai dati dello slicer · ricorda di includere scarti e spurghi nei consumi.</div>')


if 'editor' in st.session_state:
    kind, identifier = st.session_state['editor']
    if kind == 'spool':
        target = history_spools.get(identifier)
        if target: edit_spool_dialog(target)
        else: close_editor()
    elif kind == 'print':
        target = next((p for p in prints if p['key'] == identifier), None)
        if target: edit_print_dialog(target)
        else: close_editor()
    elif kind == 'schedule':
        target = next((p for p in plans if p['key'] == identifier), None)
        if target: schedule_print_dialog(target)
        else: close_editor()
    elif kind == 'complete':
        target = next((p for p in plans if p['key'] == identifier), None)
        if target: complete_print_dialog(target)
        else: close_editor()
