import tempfile
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from resale_app.store import Store, draft, validate, listing_url
from resale_app.browser import Browser, DEFAULT_SELECTORS


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'db.sqlite3')
        self.photo = self.root / 'a.jpg'
        self.photo.write_bytes(b'original-photo')

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def ready(self):
        item = draft([str(self.photo)])
        item.update(title='Camisa azul', description='Tiene una mancha.', price='8,50', reviewed=True)
        return item

    def test_renamed_duplicate_rejected_without_new_row(self):
        item = self.ready()
        self.store.save(item)
        renamed = self.root / 'renamed.jpg'
        renamed.write_bytes(self.photo.read_bytes())
        with self.assertRaises(ValueError):
            self.store.save(draft([str(renamed)]))
        self.assertEqual(len(self.store.all()), 1)

    def test_receipt_cannot_be_erased(self):
        item = self.ready()
        item['url'] = 'https://www.vinted.es/items/123-shirt'
        item['status'] = 'publicado'
        self.store.save(item)
        item['url'] = ''
        with self.assertRaises(ValueError):
            self.store.save(item)
        self.assertTrue(self.store.all()[0]['url'])

    def test_unreviewed_pending_published_and_invalid_price_blocked(self):
        validate(self.ready())
        for update in [dict(reviewed=False), dict(status='en navegador'), dict(status='publicado'),
                       dict(price='nan'), dict(price='inf'), dict(price=0), dict(price='foo'),
                       dict(photos=[]), dict(title='a' * 51)]:
            item = self.ready()
            item.update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate(item)

    def test_receipt_urls(self):
        self.assertTrue(listing_url('https://www.vinted.es/items/123-shirt'))
        for url in ['https://www.vinted.es/items/new', 'https://vinted.es.evil.test/items/123',
                    'http://vinted.es/items/123', 'https://www.vinted.es/items/123/edit']:
            self.assertFalse(listing_url(url))

    @unittest.skipUnless(importlib.util.find_spec('selenium'), 'Optional app dependency')
    def test_browser_fills_once_and_rejects_wrong_page(self):
        class Element:
            def __init__(self):
                self.value = ''
            def is_displayed(self):
                return True
            def is_enabled(self):
                return True
            def get_attribute(self, name):
                return self.value
            def send_keys(self, text):
                self.value += text
        class Driver:
            current_url = 'https://www.vinted.es/items/new'
            fields = {selector: Element() for selector in DEFAULT_SELECTORS.values()}
            def find_elements(self, by, selector):
                return [self.fields[selector]]
        browser = Browser(self.root)
        browser.driver = Driver()
        item = self.ready()
        browser.fill(item)
        self.assertEqual(browser.driver.fields[DEFAULT_SELECTORS['price']].value, '8.50')
        self.assertEqual(browser.active_id, item['id'])
        with self.assertRaises(ValueError):
            browser.fill(item)
        browser.driver.current_url = 'https://other.test/items/new'
        with self.assertRaises(ValueError):
            browser.fill(item)

    def test_import_preserves_existing_local_and_rejects_path_escape(self):
        original = self.ready()
        original['id'] = 'V01'
        self.store.save(original)
        master = {'sheets': {
            'Precios': {'rows': [[], ['V01', '', '', 99]]},
            'Anuncios': {'rows': [[], ['V01', 'Changed', 'Changed', '', 'a.jpg']]},
            'Fotos': {'rows': [[], ['V01', 1, 'a.jpg']]}}}
        with patch('resale_app.store.read_xlsx', return_value=master), patch('resale_app.store.check_master'):
            self.assertEqual(self.store.import_xlsx('export.xlsx', self.root), 0)
            self.assertEqual(self.store.all()[0]['price'], '8,50')
            master['sheets']['Fotos']['rows'][1][2] = '../outside.jpg'
            with self.assertRaises(ValueError):
                self.store.import_xlsx('export.xlsx', self.root)


if __name__ == '__main__':
    unittest.main()
