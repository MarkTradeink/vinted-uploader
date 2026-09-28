"""Visible Selenium session. User completes taxonomy and presses Publish in Vinted."""
import json
from pathlib import Path

from .store import validate, listing_url

DEFAULT_SELECTORS = {
    'title': 'input[name="title"], input#title',
    'description': 'textarea[name="description"], textarea#description',
    'price': 'input[name="price"], input#price',
    'photos': 'input[type="file"]',
}


class Browser:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.driver = None
        self.active_id = None

    def open(self):
        if self.driver is None:
            from selenium import webdriver
            options = webdriver.ChromeOptions()
            options.add_argument('--user-data-dir=' + str((self.data_dir / 'chrome-profile').resolve()))
            self.driver = webdriver.Chrome(options=options)
        self.driver.get('https://www.vinted.es/items/new')

    def fill(self, item):
        validate(item)
        paths = item['photos']
        if any(Path(p).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp') for p in paths):
            raise ValueError('Para subir, usa fotos JPG, PNG o WebP. Convierte copias de otros formatos.')
        if self.driver is None:
            raise ValueError('Abre Vinted e inicia sesión primero.')
        from urllib.parse import urlparse
        page = urlparse(self.driver.current_url)
        if page.hostname not in ('www.vinted.es', 'vinted.es') or page.path.rstrip('/') != '/items/new':
            raise ValueError('Abre el formulario de nuevo artículo en Vinted y resuelve el acceso manualmente.')
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        selectors = DEFAULT_SELECTORS.copy()
        config = self.data_dir / 'selectors.json'
        if config.exists():
            selectors.update(json.loads(config.read_text(encoding='utf-8')))

        def unique(driver, name):
            matches = driver.find_elements(By.CSS_SELECTOR, selectors[name])
            if name != 'photos':
                matches = [e for e in matches if e.is_displayed() and e.is_enabled()]
            return matches[0] if len(matches) == 1 else False

        elements = {name: WebDriverWait(self.driver, 12).until(lambda d, n=name: unique(d, n))
                    for name in DEFAULT_SELECTORS}
        # Refuse to overwrite any pre-existing draft. No automatic retry after partial upload.
        if any(elements[n].get_attribute('value') for n in ('title', 'description', 'price', 'photos')):
            raise ValueError('El formulario contiene datos. Revisa o descarta ese borrador en Vinted primero.')
        self.active_id = item['id']
        for name in ('title', 'description', 'price'):
            value = str(item[name]).replace(',', '.') if name == 'price' else item[name]
            elements[name].send_keys(value)
        # Upload original supported formats; never alter originals.
        elements['photos'].send_keys('\n'.join(str(Path(p).resolve()) for p in paths))
        return 'Texto y fotos enviados. Revisa la carga, categoría, marca, talla, estado y envío; publica en Vinted.'

    def receipt(self, item_id):
        if self.driver is None or self.active_id != item_id:
            raise ValueError('Esta sesión no ha preparado el artículo seleccionado.')
        url = self.driver.current_url
        if not listing_url(url):
            raise ValueError('No se ve una URL de artículo publicado. Publica y abre su página primero.')
        return url

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
