"""Optional real Chrome test: python -m tests.smoke_browser is not needed; run this file.

Run from repository root: python tests/smoke_browser.py
Only a temporary local HTML file is opened. No account or marketplace is contacted.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from selenium import webdriver
from resale_app.browser import Browser
from resale_app.store import draft


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        photo = root / 'test.png'
        Image.new('RGB', (20, 20), 'blue').save(photo)
        page = root / 'form.html'
        page.write_text('<input name="title"><textarea name="description"></textarea>'
                        '<input name="price"><input type="file" multiple>', encoding='utf-8')
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--user-data-dir=' + str(root / 'profile'))
        with webdriver.Chrome(options=options) as driver:
            driver.get(page.as_uri())
            class LocalFixture:
                # Deliberate test seam for the production origin guard, while all DOM
                # operations use the actual local Chrome page above.
                current_url = 'https://www.vinted.es/items/new'
                def find_elements(self, *args):
                    return driver.find_elements(*args)
            browser = Browser(root)
            browser.driver = LocalFixture()
            item = draft([str(photo)])
            item.update(title='Camisa azul', description='Usada, con una marca visible.',
                        price='9,50', reviewed=True)
            browser.fill(item)
            values = driver.execute_script('return [document.querySelector("input[name=title]").value,'
                'document.querySelector("textarea").value,document.querySelector("input[name=price]").value,'
                'document.querySelector("input[type=file]").files.length]')
            assert values == [item['title'], item['description'], '9.50', 1], values
            try:
                browser.fill(item)
                raise AssertionError('Duplicate fill should be blocked')
            except ValueError:
                pass
            print('Real Chrome local fixture: fields, photo upload and duplicate protection OK')


if __name__ == '__main__':
    main()
