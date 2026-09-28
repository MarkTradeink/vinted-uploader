"""Run with python -m resale_app."""
import copy
import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageOps, ImageTk

from .browser import Browser
from .services import generate, visual_search
from .store import Store, draft, validate, listing_url

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.local' / 'desktop'


class App:
    def __init__(self, window):
        self.window = window
        window.title('Reventa · borradores y subida supervisada')
        window.geometry('1180x840')
        self.store = Store(DATA / 'inventory.sqlite3')
        self.browser = Browser(DATA)
        self.item = None
        self.busy = False
        self.events = queue.Queue()
        self.fields = {}
        bar = ttk.Frame(window, padding=8)
        bar.pack(fill='x')
        for label, action in [('Nuevo artículo', self.new), ('Importar XLSX actual', self.import_sheet),
                              ('Guardar', self.save), ('Exportar copia JSON', self.export)]:
            ttk.Button(bar, text=label, command=lambda a=action: self.guard(a)).pack(side='left', padx=3)
        self.status = tk.StringVar(value='Datos privados en .local/desktop. Selecciona un artículo o crea uno.')
        ttk.Label(window, textvariable=self.status, wraplength=1100, padding=8).pack(side='bottom', fill='x')
        split = ttk.Panedwindow(window, orient='horizontal')
        split.pack(fill='both', expand=True, padx=8)
        left = ttk.Frame(split)
        split.add(left, weight=1)
        self.tree = ttk.Treeview(left, columns=('title', 'price', 'state'), show='headings', selectmode='browse')
        for name, label, width in [('title', 'Artículo', 245), ('price', 'EUR', 55), ('state', 'Estado', 90)]:
            self.tree.heading(name, text=label)
            self.tree.column(name, width=width)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        panel = ttk.Frame(split, padding=8)
        split.add(panel, weight=3)
        notebook = ttk.Notebook(panel)
        notebook.pack(fill='both', expand=True)
        edit, photos, ai, upload = [ttk.Frame(notebook, padding=12) for _ in range(4)]
        for frame, title in [(edit, 'Anuncio'), (photos, 'Fotos'), (ai, 'IA y comparables'), (upload, 'Subir a Vinted')]:
            notebook.add(frame, text=title)
        for name, label in [('title', 'Título · máximo 50 caracteres'), ('price', 'Precio Vinted · EUR')]:
            ttk.Label(edit, text=label).pack(anchor='w')
            self.fields[name] = tk.StringVar()
            ttk.Entry(edit, textvariable=self.fields[name]).pack(fill='x', pady=(0, 10))
        for name, label, height in [('description', 'Descripción pública', 10),
                                    ('notes', 'Notas privadas / dudas por resolver', 5)]:
            ttk.Label(edit, text=label).pack(anchor='w')
            self.fields[name] = tk.Text(edit, height=height, wrap='word', undo=True)
            self.fields[name].pack(fill='both', expand=True, pady=(0, 10))
        self.reviewed = tk.BooleanVar()
        ttk.Checkbutton(edit, text='He revisado fotos, texto y precio; he resuelto las dudas esenciales.',
                        variable=self.reviewed).pack(anchor='w')
        self.provenance = tk.StringVar()
        ttk.Label(edit, textvariable=self.provenance, wraplength=620).pack(anchor='w', pady=8)
        self.photo_list = tk.Listbox(photos, height=9, exportselection=False)
        self.photo_list.pack(fill='x')
        self.photo_list.bind('<<ListboxSelect>>', self.preview)
        pb = ttk.Frame(photos)
        pb.pack(fill='x', pady=8)
        for label, action in [('Añadir', self.add_photos), ('Quitar', self.remove_photo),
                              ('↑', lambda: self.move_photo(-1)), ('↓', lambda: self.move_photo(1))]:
            ttk.Button(pb, text=label, command=lambda a=action: self.guard(a)).pack(side='left')
        ttk.Label(photos, text='La primera foto será la principal. La IA analiza las primeras 6.').pack(anchor='w')
        self.photo_preview = ttk.Label(photos)
        self.photo_preview.pack(fill='both', expand=True)
        ttk.Label(ai, text='API opcional: envía las primeras 6 fotos y el texto a OpenAI.\n'
                  'Se factura en tu cuenta API. Los resultados idénticos se reutilizan localmente.',
                  wraplength=600).pack(anchor='w', pady=8)
        self.model = tk.StringVar(value=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
        ttk.Label(ai, text='Modelo (configurable)').pack(anchor='w')
        ttk.Entry(ai, textvariable=self.model).pack(fill='x')
        self.search = tk.BooleanVar(value=False)
        ttk.Checkbutton(ai, text='Incluir búsqueda web de comparables (consumo adicional)', variable=self.search).pack(anchor='w', pady=8)
        ttk.Button(ai, text='Generar propuesta con OpenAI', command=lambda: self.guard(self.ai)).pack(anchor='w')
        ttk.Button(ai, text='Buscar primera foto con Google Cloud Vision',
                   command=lambda: self.guard(self.vision)).pack(anchor='w', pady=8)
        ttk.Label(ai, text='Vision devuelve páginas e imágenes similares; no verifica marca ni precio.').pack(anchor='w')
        self.research = tk.Text(ai, wrap='word', height=20)
        self.research.pack(fill='both', expand=True, pady=8)
        ttk.Label(upload, text='1. Guarda y revisa el artículo.\n2. Abre Chrome e inicia sesión manualmente.\n'
                  '3. En un formulario nuevo y vacío, pulsa Rellenar.\n4. Revisa fotos, categoría, marca, talla, estado y envío.\n'
                  '5. Pulsa Publicar en Vinted; después registra el enlace aquí.\n\n'
                  'No se oculta Selenium ni se resuelven verificaciones automáticamente.\n'
                  'Los selectores de Vinted pueden cambiar. Consulta docs/desktop-app.md.',
                  wraplength=590, justify='left').pack(anchor='w', pady=10)
        for label, action in [('Abrir Chrome / nuevo formulario', self.open_browser),
                              ('Rellenar artículo revisado', self.fill),
                              ('Registrar enlace tras publicar', self.receipt),
                              ('Descarté la carga pendiente: permitir nuevo intento', self.reset_pending)]:
            ttk.Button(upload, text=label, command=lambda a=action: self.guard(a)).pack(anchor='w', pady=7)
        self.url = tk.StringVar()
        ttk.Entry(upload, textvariable=self.url, state='readonly').pack(fill='x', pady=12)
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()
        self.window.after(150, self.poll)

    def guard(self, action):
        if self.busy:
            messagebox.showinfo('Operación en curso', 'Espera a que termine la operación actual.')
            return
        try:
            action()
        except Exception as exc:
            messagebox.showerror('No se pudo completar', str(exc))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.items = {i['id']: i for i in self.store.all()}
        for key, item in self.items.items():
            self.tree.insert('', 'end', iid=key, values=(item['title'] or key, item['price'], item['status']))

    def read_form(self):
        if self.item is None:
            raise ValueError('Selecciona o crea un artículo.')
        item = copy.deepcopy(self.item)
        for name, widget in self.fields.items():
            item[name] = widget.get('1.0', 'end-1c') if isinstance(widget, tk.Text) else widget.get()
        item['research'] = self.research.get('1.0', 'end-1c')
        item['reviewed'] = self.reviewed.get()
        return item

    def show(self, item):
        self.item = copy.deepcopy(item)
        for name, widget in self.fields.items():
            if isinstance(widget, tk.Text):
                widget.delete('1.0', 'end')
                widget.insert('1.0', item[name])
            else:
                widget.set(item[name])
        self.reviewed.set(item['reviewed'])
        self.provenance.set(item['id'] + ' · ' + item['provenance'])
        self.url.set(item['url'])
        self.research.delete('1.0', 'end')
        self.research.insert('1.0', item.get('research', ''))
        self.update_photos()

    def select(self, event=None):
        ids = self.tree.selection()
        if self.busy or not ids or ids[0] not in self.items:
            return
        if self.item and self.item['id'] != ids[0]:
            try:
                saved = self.read_form()
                self.store.save(saved)
                self.items[saved['id']] = saved
            except Exception as exc:
                messagebox.showerror('No se guardaron los cambios', str(exc))
                return
        self.show(self.items[ids[0]])

    def save(self):
        self.item = self.read_form()
        self.store.save(self.item)
        self.refresh()
        self.status.set('Borrador guardado en este ordenador.')

    def new(self):
        if self.item:
            self.save()
        item = draft()
        self.store.save(item)
        self.refresh()
        self.show(item)

    def import_sheet(self):
        if self.item:
            self.save()
        path = filedialog.askopenfilename(title='Exportación reciente del Google Sheet maestro', filetypes=[('Excel', '*.xlsx')])
        if not path:
            return
        root = filedialog.askdirectory(title='Carpeta raíz de las fotos originales')
        if root:
            count = self.store.import_xlsx(path, root)
            self.refresh()
            self.status.set(f'{count} artículos importados. Los IDs existentes se conservan sin sobrescribir.')

    def export(self):
        if self.item:
            self.save()
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            Path(path).write_text(json.dumps(self.store.all(), indent=2, ensure_ascii=False), encoding='utf-8')
            self.status.set('Copia exportada. Contiene datos privados; no la subas al repositorio público.')

    def update_photos(self):
        self.photo_list.delete(0, 'end')
        for p in self.item['photos']:
            self.photo_list.insert('end', Path(p).name)
        self.photo_preview.configure(image='')
        if self.item['photos']:
            self.photo_list.selection_set(0)
            self.preview()

    def add_photos(self):
        item = self.read_form()
        paths = filedialog.askopenfilenames(filetypes=[('Fotos', '*.jpg *.jpeg *.png *.webp *.gif')])
        item['photos'] = list(dict.fromkeys(item['photos'] + list(paths)))
        item['reviewed'] = False
        self.store.save(item)
        self.show(item)

    def remove_photo(self):
        selection = self.photo_list.curselection()
        if selection:
            item = self.read_form()
            item['photos'].pop(selection[0])
            item['reviewed'] = False
            self.show(item)

    def move_photo(self, direction):
        selection = self.photo_list.curselection()
        if selection:
            n = selection[0]
            item = self.read_form()
            other = n + direction
            if 0 <= other < len(item['photos']):
                item['photos'][n], item['photos'][other] = item['photos'][other], item['photos'][n]
                item['reviewed'] = False
                self.show(item)
                self.photo_list.selection_clear(0, 'end')
                self.photo_list.selection_set(other)
                self.preview()

    def preview(self, event=None):
        selection = self.photo_list.curselection()
        if not selection or not self.item:
            return
        try:
            with Image.open(self.item['photos'][selection[0]]) as im:
                im = ImageOps.exif_transpose(im)
                im.thumbnail((570, 410))
                self.preview_image = ImageTk.PhotoImage(im.copy())
            self.photo_preview.configure(image=self.preview_image)
        except Exception:
            self.status.set('No se pudo previsualizar esta foto.')

    def run(self, work, done):
        self.busy = True
        self.locked = []
        def lock(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Button, ttk.Checkbutton, tk.Text)):
                    self.locked.append((child, child.cget('state')))
                    child.configure(state='disabled')
                lock(child)
        lock(self.window)
        self.status.set('Operación en curso…')
        def worker():
            try:
                self.events.put((done, work(), None))
            except Exception as exc:
                # SDK/HTTP exceptions can include headers or URLs; keep secrets out of dialogs/logs.
                message = str(exc) if isinstance(exc, ValueError) else (
                    type(exc).__name__ + ': revisa conexión, API/modelo o navegador. No hubo reintento automático.')
                self.events.put((done, None, message))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            done, result, error = self.events.get_nowait()
            self.busy = False
            for widget, state in self.locked:
                widget.configure(state=state)
            if error:
                self.status.set(error)
                messagebox.showerror('Operación detenida', error)
            else:
                self.guard(lambda: done(result))
        except queue.Empty:
            pass
        self.window.after(150, self.poll)

    def ai(self):
        self.save()
        item = copy.deepcopy(self.item)
        if not item['photos']:
            raise ValueError('Añade fotos primero.')
        model, search = self.model.get(), self.search.get()
        def done(data):
            proposal = {k: v for k, v in data.items() if k != '_response'}
            item['research'] = json.dumps(proposal, indent=2, ensure_ascii=False)
            item['title'], item['description'] = data['title'], data['description']
            # Keep seller's price. AI recommendation appears in research for deliberate adoption.
            item['notes'] += '\nDudas de IA: ' + json.dumps(data.get('uncertainties', []), ensure_ascii=False)
            item['reviewed'] = False
            self.store.save(item)
            self.show(item)
            self.refresh()
            self.status.set('Propuesta guardada para revisar. El precio del vendedor se conserva; la sugerencia está en IA.')
        self.run(lambda: generate(item, model, search, DATA / 'api-cache'), done)

    def vision(self):
        self.save()
        item = copy.deepcopy(self.item)
        if not item['photos']:
            raise ValueError('Añade fotos primero.')
        def done(data):
            item['research'] += '\nGoogle Cloud Vision:\n' + json.dumps(data, ensure_ascii=False, indent=2)
            self.store.save(item)
            self.show(item)
            self.status.set('Coincidencias guardadas. Comprueba las páginas antes de adoptar un precio o una marca.')
        self.run(lambda: visual_search(item['photos'][0]), done)

    def open_browser(self):
        if any(i['status'] == 'en navegador' for i in self.store.all()):
            raise ValueError('Hay una carga pendiente. Registra su enlace o descártala antes de abrir otro formulario.')
        self.run(self.browser.open, lambda _: self.status.set('Inicia sesión y deja abierto un formulario nuevo y vacío.'))

    def fill(self):
        self.save()
        item = copy.deepcopy(self.item)
        validate(item)
        if any(i['status'] == 'en navegador' for i in self.store.all()):
            raise ValueError('Resuelve la carga pendiente antes de cargar otro artículo.')
        pending = copy.deepcopy(item)
        pending['status'] = 'en navegador'
        self.store.save(pending)
        self.store.event(item['id'], 'fill_started')
        self.show(pending)
        self.refresh()
        self.run(lambda: self.browser.fill(item), lambda result: self.status.set(result))

    def receipt(self):
        self.save()
        item = copy.deepcopy(self.item)
        if item['url']:
            raise ValueError('Este artículo ya tiene un enlace registrado.')
        if item['status'] != 'en navegador':
            raise ValueError('El artículo no tiene una carga pendiente.')
        def record(url):
            if not messagebox.askyesno('Comprobar artículo', '¿Este enlace corresponde a este artículo y ya está publicado?\n'
                                      + item['title'] + '\n' + url):
                return
            item.update(url=url, status='publicado')
            self.store.save(item)
            self.store.event(item['id'], 'seller_confirmed_publication', url)
            self.show(item)
            self.refresh()
            self.status.set('Enlace de publicación registrado con confirmación del vendedor.')
        if self.browser.driver is not None and self.browser.active_id == item['id']:
            self.run(lambda: self.browser.receipt(item['id']), record)
        else:
            url = simpledialog.askstring('Recuperar tras reinicio', 'Pega el enlace del artículo publicado en Vinted:')
            if url:
                if not listing_url(url):
                    raise ValueError('El enlace no tiene formato de artículo de Vinted España.')
                record(url)

    def reset_pending(self):
        self.save()
        if self.item['url']:
            raise ValueError('No se reinician artículos publicados.')
        if messagebox.askyesno('Evitar duplicados', '¿Has comprobado que no se publicó y descartado la carga en Vinted?'):
            self.item['status'] = 'borrador'
            self.item['reviewed'] = False
            self.store.save(self.item)
            self.store.event(self.item['id'], 'seller_reset_pending')
            self.show(self.item)
            self.refresh()

    def close(self):
        if self.busy:
            messagebox.showinfo('Operación en curso', 'Espera a que termine antes de cerrar.')
            return
        try:
            if self.item:
                self.save()
        except Exception as exc:
            messagebox.showerror('No se guardó', str(exc))
            return
        try:
            self.browser.close()
        finally:
            self.store.db.close()
            self.window.destroy()


def main():
    window = tk.Tk()
    App(window)
    window.mainloop()


if __name__ == '__main__':
    main()
