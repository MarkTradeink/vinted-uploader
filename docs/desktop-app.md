# App local de reventa

Aplicación de escritorio en español, Python 3.11+ y Tkinter. Funciona sin Codex.
Guarda borradores en SQLite, permite revisar fotos, importar el inventario y
rellenar Vinted con Selenium en Chrome visible. El vendedor completa las opciones
del catálogo y pulsa **Publicar** en Vinted. No publica lotes desatendidos.

## Arranque en Windows

1. Ejecuta `Instalar app.bat` una vez (crea `.venv` e instala las dependencias).
2. Ejecuta `Iniciar app.bat`. Si ya tienes Pillow y Selenium, también puedes usar
   `python -m resale_app` sin instalar otra copia. OpenAI solo es necesario para IA.
3. Crea un artículo y añade sus fotos, o exporta el Google Sheet **actual** como
   XLSX y pulsa **Importar XLSX actual**. Selecciona la carpeta raíz de originales.

La importación espera las pestañas y columnas del inventario documentadas en
`data-contract.md`. Conserva IDs; no sobrescribe artículos ya importados.
La app no lee ni sincroniza Google Sheets en directo. Importar una nueva exportación
solo añade IDs nuevos. Los cambios posteriores de filas existentes requieren revisión
manual en la app. El XLSX histórico de `outputs` no representa el estado actual.
Los enlaces y estados se guardan localmente; la copia JSON permite consultarlos y
trasladarlos al maestro. No se actualiza el maestro automáticamente.

## Flujo de publicación

Revisa título, descripción, precio, defectos y dudas. Marca la casilla de revisión.
Abre Chrome desde la pestaña **Subir a Vinted** e inicia sesión tú mismo. Usa un
formulario nuevo y vacío. Pulsa **Rellenar artículo revisado**. El perfil de Chrome
es exclusivo de esta app y conserva tu sesión localmente.

Completa categoría, marca, talla, estado, colores y envío en Vinted. Revisa que
terminen las cargas de fotos y pulsa **Publicar** en la página. Después, con la
página del anuncio abierta, pulsa **Registrar enlace tras publicar**. La app valida
el formato del enlace y pide confirmar que corresponde al artículo. Esa confirmación
del vendedor es el recibo; no se presenta como una verificación independiente.

Una carga queda pendiente incluso si falla a mitad. No se reintenta automáticamente:
comprueba primero si se publicó y registra el enlace, o descarta la carga en Vinted
y restablece el borrador en la app. Tras reiniciar puedes pegar el enlace publicado.
Las fotos idénticas (incluso renombradas) no se asignan a dos artículos distintos.

Vinted restringe bots y herramientas externas en sus
[condiciones](https://www.vinted.es/terms-and-conditions). Comprueba qué permite tu
cuenta antes de usar Selenium. La app no oculta la automatización, no cambia de IP
ni sortea CAPTCHA. Ante una verificación, interviene el vendedor.

### Compatibilidad de Selenium

Chrome debe estar instalado. Selenium Manager puede descargar un controlador en
el primer arranque y necesita conexión. No uses simultáneamente dos instancias de
la app con el mismo perfil. El adaptador usa campos HTML habituales; **no se ha
certificado contra una sesión autenticada de Vinted**. Si la web cambia, falla sin
adivinar otro botón. Se pueden ajustar selectores CSS en el archivo privado
`.local/desktop/selectors.json`, con estas claves:

```json
{
  "title": "input[name=title], input#title",
  "description": "textarea[name=description], textarea#description",
  "price": "input[name=price], input#price",
  "photos": "input[type=file]"
}
```

Debe coincidir un único campo por clave. Solo sube JPG, PNG y WebP; convierte copias
de GIF/HEIC fuera de la app y conserva originales. Las esperas sirven para que cargue
el formulario; no simulan identidades ni intentan evitar detección.

## IA y búsqueda opcionales

En PowerShell, antes de iniciar (no pegues las claves en el repositorio):

```powershell
$env:OPENAI_API_KEY = 'tu-clave'
$env:OPENAI_MODEL = 'gpt-4.1-mini'
python -m resale_app
```

El modelo se puede cambiar en la interfaz. Debe aceptar imágenes y Responses API;
si activas búsqueda web, también debe admitir esa herramienta. Se envían como máximo
las primeras seis fotos, reducidas a 1400 píxeles y sin metadatos EXIF, junto con texto
y notas. Las fotos originales no se modifican. La API se factura aparte de Codex.
Cada botón hace una petición explícita; las respuestas idénticas de OpenAI se
reutilizan desde la caché privada, sin reintentos automáticos.

La propuesta sustituye título y descripción y desmarca la revisión. El precio de
venta se conserva: la sugerencia, comparables y dudas quedan en **IA y comparables**.
Comprueba las URLs y distingue precios anunciados de ventas reales. No hay estimación
de coste monetario en la app: depende del modelo, imágenes y búsquedas. Configura el
presupuesto de tu proyecto API. Nunca se generan propuestas al abrir la app.

Para coincidencias visuales, habilita Google Cloud Vision y define
`GOOGLE_VISION_API_KEY` en el entorno. El botón envía solo la primera foto a
[WEB_DETECTION](https://docs.cloud.google.com/vision/docs/detecting-web).
Devuelve entidades, imágenes y páginas similares; no proporciona por sí solo precios
de venta. **No es una API oficial de Google Lens.** La búsqueda puede tener coste en
Google Cloud. La app no instala ni contrata proveedores externos de Lens.

## Datos y pruebas

Todo se guarda bajo `.local/desktop/`, excluido del repositorio: base SQLite, eventos,
respuestas API y perfil de Chrome. Este último contiene sesiones privadas. Haz copias
de seguridad de la carpeta con la app cerrada; no la compartas ni publiques.
Las claves se leen del entorno y no se guardan en la base de datos.

```powershell
python -m unittest discover -s tests -v
python tests/smoke_browser.py
```

Las pruebas de inventario son offline. La comprobación Selenium contra un formulario
local prueba el mecanismo de rellenado, no acredita compatibilidad en vivo con Vinted.
Wallapop conserva sus textos y precios en el flujo CLI/maestro; la app de escritorio
actual solo prepara el formulario de Vinted.
