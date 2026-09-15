import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest
import filament_store as store

ROOT = Path(__file__).resolve().parents[1]

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.xlsx'
        fixture = Workbook()
        fixture.active.title = 'Bobine'
        fixture['Bobine'].append(['ID', 'Materiale', 'Marca', 'Colore', 'Peso', 'Usati', 'Rimasti', '%', 'Stato', 'Note'])
        for row in [
            ['B001', 'ABS', '3ntr', 'Nero', 5000, 4900],
            ['B002', 'Supporto', '3ntr', 'Bianco', 1000, 300],
            ['B003', 'ABS', '3ntr', 'Arancione', 1000, 750],
        ]:
            fixture['Bobine'].append(row)
        fixture.create_sheet('Ugelli').append(['Ugello', 'Bobina'])
        for n in (1, 2, 3): fixture['Ugelli'].append([n, f'B{n:03d}'])
        fixture.create_sheet('Stampe').append(['Data', 'Nome', 'Ugello', 'Bobina', 'Materiale', 'Grammi', 'Note'])
        fixture['Stampe'].append([datetime(2026, 1, 1, 12), 'Stampa precedente', 1, 'B001', 'ABS', 100, 'Test storico'])
        fixture.save(self.path)
        self.wb = store.load(self.path)

    def tearDown(self): self.tmp.cleanup()

    def test_multinozzle_print_and_atomic_validation(self):
        before = {b['id']: b['rim'] for b in store.bobine(self.wb)}
        count = len(store.history(self.wb))
        with self.assertRaises(ValueError):
            store.record_print(self.wb, 'Invalid', {1: 1, 2: 999999, 3: 0})
        self.assertEqual(before, {b['id']: b['rim'] for b in store.bobine(self.wb)})
        store.record_print(self.wb, 'Test', {1: 1.5, 2: 2, 3: 3})
        self.assertEqual(len(store.history(self.wb)), count + 1)
        store.save(self.wb, self.path)
        latest = store.history(store.load(self.path))[0]
        self.assertEqual(latest['totale'], 6.5)
        self.assertEqual(len(latest['consumi']), 3)
        self.assertTrue(self.path.with_suffix('.backup.xlsx').exists())

    def test_setup_and_exhaustion(self):
        with self.assertRaises(ValueError): store.set_assignments(self.wb, {1:'B001',2:'B001',3:''})
        amount = store.bobine(self.wb)[0]['rim']
        store.record_print(self.wb, 'Finish', {1:amount,2:0,3:0})
        self.assertEqual(store.bobine(self.wb)[0]['rim'], 0)
        with self.assertRaises(ValueError): store.set_assignments(self.wb, {1:'B001',2:'',3:''})
        store.set_assignments(self.wb, {1:'',2:'',3:''})
        self.assertTrue(all(not b['ugello'] for b in store.bobine(self.wb)))

    def test_purchase_clears_restock_and_conflicts_rejected(self):
        self.assertTrue(any(x['Materiale'] == 'ABS' and x['Colore'] == 'Nero' for x in store.restock(store.bobine(self.wb))))
        store.add_spool(self.wb, 'ABS', '3ntr', 'Nero', 5000)
        self.assertFalse(any(x['Materiale'] == 'ABS' and x['Colore'] == 'Nero' for x in store.restock(store.bobine(self.wb))))
        stale = store.load(self.path)
        store.save(self.wb, self.path)
        with self.assertRaises(ValueError): store.save(stale, self.path)

    def test_delete_restore_preserves_history_and_ids(self):
        before = store.history(self.wb)
        with self.assertRaises(ValueError): store.remove_spool(self.wb, 'B001')
        store.set_assignments(self.wb, {1:'', 2:'B002', 3:'B003'})
        store.remove_spool(self.wb, 'B001')
        self.assertNotIn('B001', [b['id'] for b in store.bobine(self.wb)])
        self.assertEqual(store.history(self.wb), before)
        archived = next(b for b in store.bobine(self.wb, include_removed=True) if b['id'] == 'B001')
        self.assertEqual(archived['colore'], 'Nero')
        with self.assertRaises(ValueError): store.set_assignments(self.wb, {1:'B001', 2:'', 3:''})
        bid = store.add_spool(self.wb, 'PLA', 'Test', 'Blu', 1000)
        store.remove_spool(self.wb, bid)
        new_id = store.add_spool(self.wb, 'PLA', 'Test', 'Verde', 1000)
        self.assertNotEqual(bid, new_id)
        store.save(self.wb, self.path)
        wb = store.load(self.path)
        store.restore_spool(wb, 'B001')
        self.assertIn('B001', [b['id'] for b in store.bobine(wb)])
        self.assertEqual(store.history(wb), before)

    def test_inventory_controls(self):
        bid = store.add_spool(self.wb, 'PLA', 'Test', 'Blu', 1000)
        store.save(self.wb, self.path)
        original_load, original_save = store.load, store.save
        with patch.object(store, 'FILE', self.path), patch.object(store, 'load', side_effect=lambda: original_load(self.path)), patch.object(store, 'save', side_effect=lambda wb: original_save(wb, self.path)):
            app = AppTest.from_file(str(ROOT / 'filament_dashboard.py')).run()
            self.assertNotIn('Riacquisti', app.sidebar.radio[0].options)
            app.sidebar.radio[0].set_value('Magazzino').run()
            for option in ['Grammi decrescenti', 'Colore A–Z', 'ID bobina']:
                next(x for x in app.selectbox if x.label == 'Ordina per').set_value(option).run()
                self.assertFalse(app.exception)
            self.assertTrue(app.button(key='delete_B001').disabled)
            app.button(key=f'delete_{bid}').click().run()
            self.assertFalse(app.exception)
            self.assertNotIn(bid, [b['id'] for b in store.bobine(original_load(self.path))])
            app.button(key=f'restore_{bid}').click().run()
            self.assertFalse(app.exception)
            self.assertIn(bid, [b['id'] for b in store.bobine(original_load(self.path))])

    def test_new_spool_guided_choices_and_custom_values(self):
        original_load, original_save = store.load, store.save
        with patch.object(store, 'FILE', self.path), \
             patch.object(store, 'load', side_effect=lambda: original_load(self.path)), \
             patch.object(store, 'save', side_effect=lambda wb: original_save(wb, self.path)):
            app = AppTest.from_file(str(ROOT / 'filament_dashboard.py')).run()
            app.sidebar.radio[0].set_value('Magazzino').run()
            self.assertEqual(app.selectbox(key='new_material_choice').value, 'ABS')
            self.assertEqual(app.selectbox(key='new_brand_choice').value, '3ntr')
            self.assertEqual(app.selectbox(key='new_color_choice').value, 'Nero')
            app.selectbox(key='new_material_choice').set_value('Altro').run()
            app.selectbox(key='new_brand_choice').set_value('Altro').run()
            app.selectbox(key='new_color_choice').set_value('Altro').run()
            app.text_input(key='new_material_custom').set_value('PETG')
            app.text_input(key='new_brand_custom').set_value('Prusament')
            app.text_input(key='new_color_custom').set_value('Galaxy Black')
            app.number_input(key='new_spool_weight').set_value(750)
            app.button(key='add_new_spool').click().run()
            self.assertFalse(app.exception)
            added = store.bobine(original_load(self.path))[-1]
            self.assertEqual(
                (added['materiale'], added['marca'], added['colore'], added['peso']),
                ('PETG', 'Prusament', 'Galaxy Black', 750),
            )
            self.assertEqual(app.selectbox(key='new_material_choice').value, 'ABS')
            self.assertEqual(app.selectbox(key='new_brand_choice').value, '3ntr')

    def test_edit_print_moves_consumption_and_rejects_overdraw(self):
        p = store.history(self.wb)[0]
        before = {b['id']: b['usati'] for b in store.bobine(self.wb)}
        with self.assertRaises(ValueError):
            store.update_print(self.wb, p['key'], 'Invalid', p['data'], '', [{'ugello': 2, 'bobina': 'B002', 'grammi': 2000}])
        self.assertEqual(before, {b['id']: b['usati'] for b in store.bobine(self.wb)})
        store.update_print(self.wb, p['key'], 'Corretta', p['data'], 'Note nuove', [
            {'ugello': 2, 'bobina': 'B002', 'grammi': 20},
            {'ugello': 3, 'bobina': 'B003', 'grammi': 5}])
        bs = {b['id']: b for b in store.bobine(self.wb)}
        self.assertEqual(bs['B001']['usati'], before['B001'] - 100)
        self.assertEqual(bs['B002']['usati'], before['B002'] + 20)
        updated = store.history(self.wb)[0]
        self.assertEqual(updated['totale'], 25)
        self.assertEqual(updated['nome'], 'Corretta')
        store.record_print(self.wb, 'Altra stampa', {1: 1, 2: 0, 3: 0})
        store.update_print(self.wb, updated['key'], 'Corretta', p['data'], '', [
            {'ugello': 2, 'bobina': 'B002', 'grammi': 10}])
        store.save(self.wb, self.path)
        result = store.history(store.load(self.path))
        self.assertEqual(len(result), 2)
        self.assertEqual(next(x for x in result if x['nome'] == 'Corretta')['totale'], 10)
        self.assertEqual(next(x for x in result if x['nome'] == 'Altra stampa')['totale'], 1)

    def test_edit_spool_validation_and_history_material(self):
        with self.assertRaises(ValueError): store.update_spool(self.wb, 'B001', 'PLA', 'Test', 'Blu', 50, 100)
        with self.assertRaises(ValueError): store.update_spool(self.wb, 'B001', 'PLA', 'Test', 'Blu', 5000, 50)
        store.update_spool(self.wb, 'B001', 'PLA', 'Test', 'Blu', 6000, 4900)
        b = next(b for b in store.bobine(self.wb) if b['id'] == 'B001')
        self.assertEqual(b['rim'], 1100)
        self.assertEqual(b['colore'], 'Blu')
        self.assertEqual(store.history(self.wb)[0]['consumi'][0]['materiale'], 'PLA')
        self.assertEqual(store.assignments(self.wb)[1], 'B001')

    def test_edit_dialogs_save_and_cancel(self):
        original_load, original_save = store.load, store.save
        with patch.object(store, 'FILE', self.path), patch.object(store, 'load', side_effect=lambda: original_load(self.path)), patch.object(store, 'save', side_effect=lambda wb: original_save(wb, self.path)):
            app = AppTest.from_file(str(ROOT / 'filament_dashboard.py')).run()
            app.sidebar.radio[0].set_value('Magazzino').run()
            app.button(key='edit_spool_B001').click().run()
            self.assertFalse(app.exception)
            app.text_input(key='edit_color').set_value('Grigio')
            next(x for x in app.button if x.label == 'Salva modifiche').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(store.bobine(original_load(self.path))[0]['colore'], 'Grigio')
            app.sidebar.radio[0].set_value('Storico').run()
            next(x for x in app.button if x.key and x.key.startswith('edit_print_')).click().run()
            self.assertFalse(app.exception)
            app.text_input(key='edit_print_name').set_value('Nome corretto')
            next(x for x in app.button if x.label == 'Salva modifiche').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(store.history(original_load(self.path))[0]['nome'], 'Nome corretto')
            next(x for x in app.button if x.key and x.key.startswith('edit_print_')).click().run()
            app.text_input(key='edit_print_name').set_value('Da annullare')
            next(x for x in app.button if x.label == 'Annulla').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(store.history(original_load(self.path))[0]['nome'], 'Nome corretto')

    def test_delete_print_refunds_all_nozzles(self):
        before = {b['id']: b['usati'] for b in store.bobine(self.wb)}
        original = store.history(self.wb)
        store.record_print(self.wb, 'Da eliminare', {1: 10, 2: 20, 3: 30})
        p = store.history(self.wb)[0]
        store.delete_print(self.wb, p['key'])
        self.assertEqual(before, {b['id']: b['usati'] for b in store.bobine(self.wb)})
        self.assertEqual(original, store.history(self.wb))
        with self.assertRaises(ValueError): store.delete_print(self.wb, p['key'])
        self.assertEqual(before, {b['id']: b['usati'] for b in store.bobine(self.wb)})

    def test_delete_print_button(self):
        original_load, original_save = store.load, store.save
        with patch.object(store, 'FILE', self.path), patch.object(store, 'load', side_effect=lambda: original_load(self.path)), patch.object(store, 'save', side_effect=lambda wb: original_save(wb, self.path)):
            app = AppTest.from_file(str(ROOT / 'filament_dashboard.py')).run()
            app.sidebar.radio[0].set_value('Storico').run()
            app.button(key='delete_print_legacy-2').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success)
            self.assertEqual(store.history(original_load(self.path)), [])
            self.assertEqual(store.bobine(original_load(self.path))[0]['usati'], 4800)

    def test_all_pages_and_print_submission(self):
        original_load, original_save = store.load, store.save
        with patch.object(store, 'FILE', self.path), patch.object(store, 'load', side_effect=lambda: original_load(self.path)), patch.object(store, 'save', side_effect=lambda wb: original_save(wb, self.path)):
            app = AppTest.from_file(str(ROOT / 'filament_dashboard.py')).run()
            self.assertFalse(app.exception)
            for page in ['Magazzino','Storico','Nuova stampa']:
                app.sidebar.radio[0].set_value(page).run()
                self.assertFalse(app.exception, page)
            app.text_input(key='print_name').set_value('UI test')
            app.number_input(key='cons_1_B001').set_value(2.5)
            next(b for b in app.button if b.label == 'Registra stampa e aggiorna scorte').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success)
            self.assertEqual(app.sidebar.radio[0].value, 'Panoramica')
            self.assertIn('Stampa salvata', app.success[0].value)
            app.sidebar.radio[0].set_value('Nuova stampa').run()
            self.assertEqual(app.number_input(key='cons_1_B001').value, 0)
            self.assertEqual(app.text_input(key='print_name').value, '')
            self.assertTrue(any(p['nome'] == 'UI test' for p in store.history(original_load(self.path))))

if __name__ == '__main__': unittest.main()
