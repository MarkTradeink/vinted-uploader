import { workflow, node, trigger, sticky, placeholder, newCredential, splitInBatches, nextBatch, expr } from '@n8n/workflow-sdk';

const disparoManual = trigger({
  type: 'n8n-nodes-base.manualTrigger',
  version: 1,
  config: { name: 'Procesar lote ahora', position: [-660, 200] },
  output: [{}]
});

const disparoProgramado = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.3,
  config: { name: 'Revisar carpeta cada dia', parameters: {}, position: [-660, 420] },
  output: [{}]
});

const configuracion = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Configuracion del lote',
    position: [-440, 300],
    parameters: {
      mode: 'manual',
      includeOtherFields: false,
      assignments: {
        assignments: [
          { id: 'carpeta', name: 'idCarpetaEntrada', value: placeholder('ID de la carpeta de Drive /vinted/entrada (el trozo final de su URL)'), type: 'string' },
          { id: 'urlcarpeta', name: 'urlCarpetaEntrada', value: placeholder('URL completa de esa misma carpeta de Drive'), type: 'string' },
          { id: 'gracia', name: 'minutosDeGracia', value: 10, type: 'number' },
          { id: 'fmin', name: 'fotosMinimas', value: 3, type: 'number' },
          { id: 'fmax', name: 'fotosMaximas', value: 8, type: 'number' },
          { id: 'factor', name: 'factorPedidoPagado', value: 0.65, type: 'number' },
          { id: 'base', name: 'precioBaseTierC', value: 12, type: 'number' },
          { id: 'chat', name: 'chatIdTelegram', value: placeholder('Tu chat ID de Telegram (preguntaselo a @get_id_bot)'), type: 'string' }
        ]
      }
    }
  },
  output: [{ idCarpetaEntrada: '1AbCdEf', urlCarpetaEntrada: 'https://drive.google.com/drive/folders/1AbCdEf', minutosDeGracia: 10, fotosMinimas: 3, fotosMaximas: 8, factorPedidoPagado: 0.65, precioBaseTierC: 12, chatIdTelegram: '123456789' }]
});

const listarFotos = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Listar fotos en Drive con EXIF',
    position: [-220, 300],
    parameters: {
      method: 'GET',
      url: 'https://www.googleapis.com/drive/v3/files',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'googleDriveOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: {
        parameters: [
          { name: 'q', value: expr("{{ \"'\" + $json.idCarpetaEntrada + \"' in parents and mimeType contains 'image/' and trashed = false\" }}") },
          { name: 'fields', value: 'files(id,name,createdTime,webViewLink,imageMediaMetadata(time))' },
          { name: 'pageSize', value: '1000' },
          { name: 'orderBy', value: 'name' }
        ]
      },
      options: { timeout: 30000 }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive Cifral', 'WS9EBgYyvCBSDXo8') }
  },
  output: [{ files: [{ id: '1xY', name: 'IMG_0001.jpg', createdTime: '2026-09-05T10:00:00.000Z', webViewLink: 'https://drive.google.com/file/d/1xY/view', imageMediaMetadata: { time: '2026:09:05 11:58:12' } }] }]
});

const leerProcesadas = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Leer prendas ya procesadas',
    position: [0, 300],
    executeOnce: true,
    alwaysOutputData: true,
    onError: 'continueRegularOutput',
    parameters: {
      resource: 'sheet',
      operation: 'read',
      documentId: { __rl: true, mode: 'list', value: '', cachedResultName: 'Vinted - Clasificacion de prendas' },
      sheetName: { __rl: true, mode: 'name', value: 'Prendas' },
      options: { returnAllMatches: 'returnAllMatches' }
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets account_Cifral', 'QeYpDR8f2M3TTHxR') }
  },
  output: [{ id_prenda: 'pk3f9a-5', marca: 'Levis', score: 88 }]
});

const leerMarcas = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Leer tabla de marcas',
    position: [220, 300],
    executeOnce: true,
    alwaysOutputData: true,
    onError: 'continueRegularOutput',
    parameters: {
      resource: 'sheet',
      operation: 'read',
      documentId: { __rl: true, mode: 'list', value: '', cachedResultName: 'Vinted - Clasificacion de prendas' },
      sheetName: { __rl: true, mode: 'name', value: 'Marcas' },
      options: { returnAllMatches: 'returnAllMatches' }
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets account_Cifral', 'QeYpDR8f2M3TTHxR') }
  },
  output: [{ marca: 'Levis', tier: 'B', multiplicador: 1.6 }]
});

const agruparFotos = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Agrupar fotos en prendas',
    position: [440, 300],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode:
        "const cfg = $('Configuracion del lote').first().json;\n" +
        "const resp = $('Listar fotos en Drive con EXIF').first().json;\n" +
        "const archivos = (resp && Array.isArray(resp.files)) ? resp.files : [];\n" +
        "\n" +
        "const yaHechas = {};\n" +
        "for (const fila of $('Leer prendas ya procesadas').all()) {\n" +
        "  const j = fila.json || {};\n" +
        "  if (j.id_prenda) yaHechas[String(j.id_prenda)] = true;\n" +
        "}\n" +
        "\n" +
        "function momento(a) {\n" +
        "  const m = a.imageMediaMetadata && a.imageMediaMetadata.time;\n" +
        "  if (m && m.length >= 19) {\n" +
        "    const iso = m.slice(0, 4) + '-' + m.slice(5, 7) + '-' + m.slice(8, 10) + 'T' + m.slice(11);\n" +
        "    const t = Date.parse(iso);\n" +
        "    if (!isNaN(t)) return t;\n" +
        "  }\n" +
        "  return Date.parse(a.createdTime);\n" +
        "}\n" +
        "\n" +
        "const limite = Date.now() - (Number(cfg.minutosDeGracia) || 10) * 60000;\n" +
        "const fotos = archivos\n" +
        "  .filter(a => Date.parse(a.createdTime) < limite)\n" +
        "  .map(a => ({ id: a.id, name: a.name, url: a.webViewLink, t: momento(a) }))\n" +
        "  .filter(a => !isNaN(a.t))\n" +
        "  .sort((a, b) => a.t - b.t);\n" +
        "\n" +
        "if (fotos.length === 0) return [];\n" +
        "\n" +
        "const huecos = [];\n" +
        "for (let i = 1; i < fotos.length; i++) huecos.push(fotos[i].t - fotos[i - 1].t);\n" +
        "const ordenados = huecos.slice().sort((a, b) => a - b);\n" +
        "const mediana = ordenados.length ? ordenados[Math.floor(ordenados.length / 2)] : 0;\n" +
        "const umbral = Math.max(mediana * 3, 8000);\n" +
        "\n" +
        "const grupos = [];\n" +
        "let actual = [fotos[0]];\n" +
        "for (let i = 1; i < fotos.length; i++) {\n" +
        "  if (fotos[i].t - fotos[i - 1].t > umbral) { grupos.push(actual); actual = []; }\n" +
        "  actual.push(fotos[i]);\n" +
        "}\n" +
        "grupos.push(actual);\n" +
        "\n" +
        "const fmin = Number(cfg.fotosMinimas) || 3;\n" +
        "const fmax = Number(cfg.fotosMaximas) || 8;\n" +
        "const hoy = new Date().toISOString().slice(0, 10);\n" +
        "const salida = [];\n" +
        "\n" +
        "for (const g of grupos) {\n" +
        "  const clave = g.map(f => f.id).join('|');\n" +
        "  let h = 0;\n" +
        "  for (let i = 0; i < clave.length; i++) h = (h * 31 + clave.charCodeAt(i)) | 0;\n" +
        "  const idPrenda = 'p' + Math.abs(h).toString(36) + '-' + g.length;\n" +
        "  if (yaHechas[idPrenda]) continue;\n" +
        "  salida.push({ json: {\n" +
        "    id_prenda: idPrenda,\n" +
        "    fecha_lote: hoy,\n" +
        "    n_fotos: g.length,\n" +
        "    fotos: g.slice(0, fmax).map(f => ({ id: f.id, name: f.name, url: f.url })),\n" +
        "    foto_principal: g[0].url,\n" +
        "    carpeta_drive: cfg.urlCarpetaEntrada,\n" +
        "    flag_agrupacion: (g.length < fmin || g.length > fmax),\n" +
        "    umbral_segundos: Math.round(umbral / 1000)\n" +
        "  } });\n" +
        "}\n" +
        "return salida;"
    }
  },
  output: [{ id_prenda: 'pk3f9a-5', fecha_lote: '2026-09-05', n_fotos: 5, fotos: [{ id: '1xY', name: 'IMG_0001.jpg', url: 'https://drive.google.com/file/d/1xY/view' }], foto_principal: 'https://drive.google.com/file/d/1xY/view', carpeta_drive: 'https://drive.google.com/drive/folders/1AbCdEf', flag_agrupacion: false, umbral_segundos: 14 }]
});

const recorrerPrendas = splitInBatches({
  version: 3,
  config: { name: 'Recorrer prendas', parameters: { batchSize: 1 }, position: [660, 300] }
});

const separarFotos = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1,
  config: {
    name: 'Separar fotos de la prenda',
    position: [880, 440],
    parameters: { fieldToSplitOut: 'fotos', include: 'noOtherFields' }
  },
  output: [{ id: '1xY', name: 'IMG_0001.jpg', url: 'https://drive.google.com/file/d/1xY/view' }]
});

const descargarFoto = node({
  type: 'n8n-nodes-base.googleDrive',
  version: 3,
  config: {
    name: 'Descargar foto de Drive',
    position: [1100, 440],
    parameters: {
      resource: 'file',
      operation: 'download',
      authentication: 'oAuth2',
      fileId: { __rl: true, mode: 'id', value: expr('{{ $json.id }}') },
      options: { binaryPropertyName: 'data' }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive Cifral', 'WS9EBgYyvCBSDXo8') }
  },
  output: [{ id: '1xY', name: 'IMG_0001.jpg' }]
});

const juntarFotos = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Juntar fotos en un solo item',
    position: [1320, 440],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode:
        "const prenda = $('Recorrer prendas').first().json;\n" +
        "const binarios = {};\n" +
        "const nombres = [];\n" +
        "const entradas = $input.all();\n" +
        "for (let i = 0; i < entradas.length && i < 8; i++) {\n" +
        "  const b = entradas[i].binary;\n" +
        "  if (!b || !b.data) continue;\n" +
        "  const campo = 'foto_' + i;\n" +
        "  binarios[campo] = b.data;\n" +
        "  nombres.push(campo);\n" +
        "}\n" +
        "return [{\n" +
        "  json: {\n" +
        "    id_prenda: prenda.id_prenda,\n" +
        "    fecha_lote: prenda.fecha_lote,\n" +
        "    n_fotos: prenda.n_fotos,\n" +
        "    foto_principal: prenda.foto_principal,\n" +
        "    carpeta_drive: prenda.carpeta_drive,\n" +
        "    flag_agrupacion: prenda.flag_agrupacion,\n" +
        "    campos_binarios: nombres.join(',')\n" +
        "  },\n" +
        "  binary: binarios\n" +
        "}];"
    }
  },
  output: [{ id_prenda: 'pk3f9a-5', fecha_lote: '2026-09-05', n_fotos: 5, foto_principal: 'https://drive.google.com/file/d/1xY/view', carpeta_drive: 'https://drive.google.com/drive/folders/1AbCdEf', flag_agrupacion: false, campos_binarios: 'foto_0,foto_1,foto_2,foto_3,foto_4' }]
});

const clasificarPrenda = node({
  type: '@n8n/n8n-nodes-langchain.anthropic',
  version: 1,
  config: {
    name: 'Clasificar prenda con Claude',
    position: [1540, 440],
    onError: 'continueRegularOutput',
    retryOnFail: true,
    maxTries: 3,
    waitBetweenTries: 3000,
    parameters: {
      resource: 'image',
      operation: 'analyze',
      modelId: { __rl: true, mode: 'list', value: 'claude-opus-5', cachedResultName: 'claude-opus-5' },
      inputType: 'binary',
      binaryPropertyName: expr('{{ $json.campos_binarios }}'),
      simplify: true,
      options: { maxTokens: 2048 },
      text:
        'Eres un tasador experto de ropa de segunda mano para Vinted y Wallapop en Espana.\n\n' +
        'Todas las imagenes adjuntas son de UNA MISMA prenda: frontal, etiqueta de marca, etiqueta de talla y composicion, trasera y detalles.\n\n' +
        'Responde UNICAMENTE con un objeto JSON valido. Sin markdown, sin bloques de codigo, sin texto antes ni despues.\n\n' +
        'Esquema exacto:\n' +
        '{\n' +
        '  "misma_prenda": true,\n' +
        '  "fotos_que_sobran": [],\n' +
        '  "categoria": "Mujer|Hombre|Nino|Unisex",\n' +
        '  "tipo_prenda": "camiseta, vaqueros, cazadora...",\n' +
        '  "marca": "nombre o null",\n' +
        '  "marca_origen": "etiqueta|logo|inferido|desconocido",\n' +
        '  "talla": "tal cual figura en la etiqueta, o null",\n' +
        '  "talla_origen": "etiqueta|inferido|desconocido",\n' +
        '  "talla_es": "equivalente espanol normalizado",\n' +
        '  "color_principal": "",\n' +
        '  "color_secundario": "o null",\n' +
        '  "material": "composicion leida, o null",\n' +
        '  "material_legible": true,\n' +
        '  "patron": "liso, rayas, estampado...",\n' +
        '  "estilo": "casual, deportivo, vintage...",\n' +
        '  "temporada": "verano|invierno|entretiempo",\n' +
        '  "condicion": "Nuevo con etiquetas|Nuevo sin etiquetas|Muy bueno|Bueno|Satisfactorio",\n' +
        '  "defectos": "lo que veas, o cadena vacia",\n' +
        '  "foto_prenda_completa_nitida": true,\n' +
        '  "titulo": "",\n' +
        '  "descripcion": "",\n' +
        '  "keywords": ""\n' +
        '}\n\n' +
        'Reglas que debes respetar:\n' +
        '1. marca_origen vale "etiqueta" SOLO si has leido literalmente el nombre en una etiqueta cosida o impresa. Vale "logo" si lo reconoces por un logotipo en la prenda. Vale "inferido" si lo deduces del estilo o la confeccion. Si no lo sabes: marca null y "desconocido".\n' +
        '2. Lo mismo para talla_origen. NUNCA adivines la talla por el aspecto de la prenda: si no ves la etiqueta, talla es null.\n' +
        '3. Devolver null es mucho mejor que inventar. Un dato inventado hace perder dinero real.\n' +
        '4. misma_prenda es false si las fotos muestran claramente prendas distintas; entonces indica en fotos_que_sobran los indices (empezando en 0) que no encajan.\n' +
        '5. titulo: maximo 60 caracteres, formato "Marca Tipo Color Talla". Sin emojis y sin mayusculas sostenidas.\n' +
        '6. descripcion: de 3 a 5 lineas en espanol, honesta, citando material y estado. No inventes medidas. No afirmes nada sobre autenticidad.\n' +
        '7. condicion: elige literalmente una de las cinco etiquetas de la lista.'
    },
    credentials: { anthropicApi: newCredential('Anthropic account', 'IeHNLdLXPGjr3JlL') }
  },
  output: [{ content: '{"misma_prenda":true,"categoria":"Hombre","tipo_prenda":"vaqueros","marca":"Levis","marca_origen":"etiqueta","talla":"W32 L34","talla_origen":"etiqueta","talla_es":"42","color_principal":"azul","material":"100% algodon","material_legible":true,"condicion":"Muy bueno","foto_prenda_completa_nitida":true,"titulo":"Levis 501 vaqueros azul W32 L34","descripcion":"Vaqueros Levis 501 en azul medio.","keywords":"levis 501 denim"}' }]
});

const parsearClasificacion = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Parsear clasificacion',
    position: [1760, 440],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode:
        "const prenda = $('Juntar fotos en un solo item').first().json;\n" +
        "const cruda = $input.first().json;\n" +
        "let texto = '';\n" +
        "if (typeof cruda === 'string') texto = cruda;\n" +
        "else if (typeof cruda.content === 'string') texto = cruda.content;\n" +
        "else if (Array.isArray(cruda.content) && cruda.content[0] && cruda.content[0].text) texto = cruda.content[0].text;\n" +
        "else if (typeof cruda.text === 'string') texto = cruda.text;\n" +
        "else if (cruda.message && typeof cruda.message.content === 'string') texto = cruda.message.content;\n" +
        "else texto = JSON.stringify(cruda);\n" +
        "\n" +
        "const ini = texto.indexOf('{');\n" +
        "const fin = texto.lastIndexOf('}');\n" +
        "let datos = null;\n" +
        "if (ini >= 0 && fin > ini) {\n" +
        "  try { datos = JSON.parse(texto.slice(ini, fin + 1)); } catch (e) { datos = null; }\n" +
        "}\n" +
        "\n" +
        "if (!datos) {\n" +
        "  return [{ json: Object.assign({}, prenda, { parse_error: true, consulta_serper: '', respuesta_cruda: texto.slice(0, 1500) }) }];\n" +
        "}\n" +
        "\n" +
        "const marca = datos.marca || '';\n" +
        "const tipo = datos.tipo_prenda || '';\n" +
        "const talla = datos.talla || '';\n" +
        "const consulta = (marca + ' ' + tipo + ' ' + talla).trim() + ' vinted';\n" +
        "return [{ json: Object.assign({}, prenda, datos, { parse_error: false, consulta_serper: consulta }) }];"
    }
  },
  output: [{ id_prenda: 'pk3f9a-5', marca: 'Levis', tipo_prenda: 'vaqueros', condicion: 'Muy bueno', parse_error: false, consulta_serper: 'Levis vaqueros W32 L34 vinted' }]
});

const buscarComparables = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Buscar precios comparables',
    position: [1980, 440],
    onError: 'continueRegularOutput',
    parameters: {
      method: 'POST',
      url: 'https://google.serper.dev/search',
      authentication: 'genericCredentialType',
      genericAuthType: 'httpHeaderAuth',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ q: $json.consulta_serper, gl: "es", hl: "es", num: 20 }) }}'),
      options: { timeout: 20000 }
    },
    credentials: { httpHeaderAuth: newCredential('Serper API', '0Ff6IGtl8LvVYzBB') }
  },
  output: [{ organic: [{ title: 'Levis 501 W32', snippet: 'Vaqueros Levis en muy buen estado 28,00 €' }] }]
});

const calcularPrecios = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Calcular precios y score',
    position: [2200, 440],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode:
        "const d = $('Parsear clasificacion').first().json;\n" +
        "const cfg = $('Configuracion del lote').first().json;\n" +
        "const res = $input.first().json || {};\n" +
        "\n" +
        "const textos = [];\n" +
        "if (Array.isArray(res.organic)) for (const o of res.organic) textos.push((o.title || '') + ' ' + (o.snippet || ''));\n" +
        "if (Array.isArray(res.shopping)) for (const s of res.shopping) textos.push((s.title || '') + ' ' + (s.price || ''));\n" +
        "\n" +
        "const precios = [];\n" +
        "for (const t of textos) {\n" +
        "  const rx = /(\\d{1,4})(?:[.,](\\d{1,2}))?\\s?(?:€|EUR|eur)/g;\n" +
        "  let m = rx.exec(t);\n" +
        "  while (m !== null) {\n" +
        "    const v = parseFloat(m[1] + '.' + (m[2] || '0'));\n" +
        "    if (v >= 2 && v <= 500) precios.push(v);\n" +
        "    m = rx.exec(t);\n" +
        "  }\n" +
        "}\n" +
        "precios.sort((a, b) => a - b);\n" +
        "\n" +
        "let usados = precios;\n" +
        "if (precios.length >= 5) usados = precios.slice(Math.floor(precios.length * 0.1), Math.ceil(precios.length * 0.9));\n" +
        "const n = usados.length;\n" +
        "const mediana = n ? usados[Math.floor(n / 2)] : null;\n" +
        "const minC = n ? usados[0] : null;\n" +
        "const maxC = n ? usados[n - 1] : null;\n" +
        "const dispersion = (n > 1 && mediana) ? (maxC - minC) / mediana : null;\n" +
        "\n" +
        "const marca = String(d.marca || '').toLowerCase().trim();\n" +
        "let multMarca = 1;\n" +
        "let tier = 'sin_clasificar';\n" +
        "if (marca) {\n" +
        "  for (const fila of $('Leer tabla de marcas').all()) {\n" +
        "    const j = fila.json || {};\n" +
        "    if (j.marca && String(j.marca).toLowerCase().trim() === marca) {\n" +
        "      multMarca = Number(j.multiplicador) || 1;\n" +
        "      tier = j.tier || 'C';\n" +
        "    }\n" +
        "  }\n" +
        "}\n" +
        "\n" +
        "const porEstado = { 'Nuevo con etiquetas': 1.25, 'Nuevo sin etiquetas': 1.1, 'Muy bueno': 1.0, 'Bueno': 0.85, 'Satisfactorio': 0.65 };\n" +
        "const multEstado = porEstado[d.condicion] || 0.85;\n" +
        "const factor = Number(cfg.factorPedidoPagado) || 0.65;\n" +
        "const base = Number(cfg.precioBaseTierC) || 12;\n" +
        "\n" +
        "let objetivo;\n" +
        "let fuente;\n" +
        "if (mediana) { objetivo = mediana * factor * multEstado; fuente = 'comparables online'; }\n" +
        "else { objetivo = base * multMarca * multEstado; fuente = 'tier de marca (sin comparables)'; }\n" +
        "\n" +
        "function redondear(v) { return Math.max(3, Math.round(v * 2) / 2); }\n" +
        "const precioObjetivo = redondear(objetivo);\n" +
        "const precioMin = redondear(objetivo * 0.75);\n" +
        "const precioSuelo = redondear(objetivo * 0.6);\n" +
        "\n" +
        "let score = 0;\n" +
        "const desglose = [];\n" +
        "if (d.marca_origen === 'etiqueta') { score += 25; desglose.push('+25 marca leida de etiqueta'); }\n" +
        "else if (d.marca_origen === 'logo') { score += 10; desglose.push('+10 marca por logo'); }\n" +
        "else if (d.marca_origen === 'inferido') { score -= 15; desglose.push('-15 marca solo inferida'); }\n" +
        "if (d.talla_origen === 'etiqueta') { score += 20; desglose.push('+20 talla leida de etiqueta'); }\n" +
        "if (Number(d.n_fotos) >= 3 && d.foto_prenda_completa_nitida === true) { score += 15; desglose.push('+15 fotos suficientes y nitidas'); }\n" +
        "if (d.material_legible === true) { score += 10; desglose.push('+10 composicion legible'); }\n" +
        "if (n >= 3) { score += 20; desglose.push('+20 ' + n + ' comparables'); }\n" +
        "else if (n > 0) { score += 8; desglose.push('+8 solo ' + n + ' comparables'); }\n" +
        "if (dispersion !== null && dispersion < 0.4) { score += 10; desglose.push('+10 precios consistentes'); }\n" +
        "if (d.flag_agrupacion === true || d.misma_prenda === false) { score -= 20; desglose.push('-20 agrupacion dudosa'); }\n" +
        "if (d.parse_error === true) { score = 0; desglose.length = 0; desglose.push('el modelo no devolvio JSON valido'); }\n" +
        "score = Math.max(0, Math.min(100, score));\n" +
        "\n" +
        "const flags = [];\n" +
        "if (d.flag_agrupacion === true) flags.push('agrupacion_dudosa');\n" +
        "if (d.misma_prenda === false) flags.push('fotos_de_prendas_distintas');\n" +
        "if (!d.marca) flags.push('sin_marca');\n" +
        "if (!d.talla) flags.push('sin_talla');\n" +
        "if (n === 0) flags.push('sin_comparables');\n" +
        "if (tier === 'sin_clasificar' && marca) flags.push('marca_no_esta_en_la_tabla');\n" +
        "if (d.parse_error === true) flags.push('error_de_parseo');\n" +
        "\n" +
        "return [{ json: {\n" +
        "  id_prenda: d.id_prenda,\n" +
        "  fecha_lote: d.fecha_lote,\n" +
        "  n_fotos: d.n_fotos,\n" +
        "  foto_principal: d.foto_principal,\n" +
        "  carpeta_drive: d.carpeta_drive,\n" +
        "  categoria: d.categoria || '',\n" +
        "  tipo_prenda: d.tipo_prenda || '',\n" +
        "  marca: d.marca || '',\n" +
        "  marca_origen: d.marca_origen || 'desconocido',\n" +
        "  talla: d.talla || '',\n" +
        "  talla_es: d.talla_es || '',\n" +
        "  talla_origen: d.talla_origen || 'desconocido',\n" +
        "  color_principal: d.color_principal || '',\n" +
        "  color_secundario: d.color_secundario || '',\n" +
        "  material: d.material || '',\n" +
        "  patron: d.patron || '',\n" +
        "  estilo: d.estilo || '',\n" +
        "  temporada: d.temporada || '',\n" +
        "  condicion: d.condicion || '',\n" +
        "  defectos: d.defectos || '',\n" +
        "  titulo: d.titulo || '',\n" +
        "  descripcion: d.descripcion || '',\n" +
        "  keywords: d.keywords || '',\n" +
        "  precio_objetivo: precioObjetivo,\n" +
        "  precio_min: precioMin,\n" +
        "  precio_suelo: precioSuelo,\n" +
        "  n_comparables: n,\n" +
        "  rango_comparables: n ? (minC + ' - ' + maxC + ' EUR') : '',\n" +
        "  fuente_precio: fuente,\n" +
        "  tier_marca: tier,\n" +
        "  score: score,\n" +
        "  score_desglose: desglose.join(' | '),\n" +
        "  flags: flags.join(', '),\n" +
        "  estado: 'pendiente'\n" +
        "} }];"
    }
  },
  output: [{ id_prenda: 'pk3f9a-5', marca: 'Levis', titulo: 'Levis 501 vaqueros azul W32 L34', precio_objetivo: 18.5, precio_min: 14, precio_suelo: 11, n_comparables: 7, rango_comparables: '15 - 34 EUR', fuente_precio: 'comparables online', score: 90, flags: '', estado: 'pendiente' }]
});

const escribirEnSheet = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Escribir prenda en el Sheet',
    position: [2420, 440],
    onError: 'continueRegularOutput',
    retryOnFail: true,
    maxTries: 3,
    waitBetweenTries: 2000,
    parameters: {
      resource: 'sheet',
      operation: 'appendOrUpdate',
      documentId: { __rl: true, mode: 'list', value: '', cachedResultName: 'Vinted - Clasificacion de prendas' },
      sheetName: { __rl: true, mode: 'name', value: 'Prendas' },
      columns: {
        mappingMode: 'autoMapInputData',
        matchingColumns: ['id_prenda'],
        value: {},
        schema: [
          { id: 'id_prenda', displayName: 'id_prenda', required: false, defaultMatch: true, display: true, type: 'string', canBeUsedToMatch: true }
        ]
      },
      options: { cellFormat: 'USER_ENTERED', handlingExtraData: 'insertInNewColumn' }
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets account_Cifral', 'QeYpDR8f2M3TTHxR') }
  },
  output: [{ id_prenda: 'pk3f9a-5', titulo: 'Levis 501 vaqueros azul W32 L34', precio_objetivo: 18.5, score: 90 }]
});

const resumirLote = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Resumir el lote',
    position: [880, 160],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode:
        "const filas = $input.all();\n" +
        "let total = 0;\n" +
        "let revisar = 0;\n" +
        "let dudosas = 0;\n" +
        "let valor = 0;\n" +
        "for (const f of filas) {\n" +
        "  const j = f.json || {};\n" +
        "  total++;\n" +
        "  valor += Number(j.precio_objetivo) || 0;\n" +
        "  const s = Number(j.score);\n" +
        "  if (!isNaN(s) && s < 50) dudosas++;\n" +
        "  else if (!isNaN(s) && s < 85) revisar++;\n" +
        "}\n" +
        "return [{ json: {\n" +
        "  total: total,\n" +
        "  publicables: total - revisar - dudosas,\n" +
        "  revisar: revisar,\n" +
        "  refotografiar: dudosas,\n" +
        "  valor_estimado: Math.round(valor)\n" +
        "} }];"
    }
  },
  output: [{ total: 18, publicables: 12, revisar: 3, refotografiar: 3, valor_estimado: 412 }]
});

const avisarTelegram = node({
  type: 'n8n-nodes-base.telegram',
  version: 1.2,
  config: {
    name: 'Avisar por Telegram',
    position: [1100, 160],
    onError: 'continueRegularOutput',
    parameters: {
      resource: 'message',
      operation: 'sendMessage',
      chatId: expr("{{ $('Configuracion del lote').first().json.chatIdTelegram }}"),
      text: expr(
        '<b>Lote clasificado</b>\n' +
        '{{ $json.total }} prendas procesadas\n\n' +
        'Publicables sin revisar (score 85+): {{ $json.publicables }}\n' +
        'Revisar 2 campos (50-84): {{ $json.revisar }}\n' +
        'Refotografiar (menos de 50): {{ $json.refotografiar }}\n\n' +
        'Valor estimado del lote: {{ $json.valor_estimado }} EUR'
      ),
      additionalFields: { parse_mode: 'HTML', appendAttribution: false }
    },
    credentials: { telegramApi: newCredential('Telegram Cifral Notifications', 'uq9HMlgF8AWmtxSM') }
  },
  output: [{ ok: true }]
});

const notaCabecera = sticky(
  '## 1. Preparacion\n\nRellena **Configuracion del lote** con el ID de tu carpeta de Drive y tu chat de Telegram.\n\nLa lista de fotos va por HTTP y no por el nodo de Drive porque solo la API devuelve `imageMediaMetadata.time`, el EXIF con el que se agrupan las fotos en prendas.\n\nLas dos lecturas de Sheets llevan **Always Output Data** para que el primer lote funcione con el Sheet vacio.',
  [configuracion, listarFotos, leerProcesadas, leerMarcas],
  { color: 4 }
);

const notaAgrupar = sticky(
  '## 2. Agrupacion\n\nOrdena por EXIF y corta donde el hueco entre fotos supera **3 veces la mediana** del propio lote: se adapta a si fotografias rapido o despacio.\n\nIgnora las fotos subidas hace menos de 10 minutos (podrias estar subiendo aun) y **salta las prendas cuyo id ya esta en el Sheet**, asi que relanzar el workflow no duplica ni vuelve a pagar.',
  [agruparFotos, recorrerPrendas],
  { color: 3 }
);

const notaClasificar = sticky(
  '## 3. Clasificacion\n\nLas fotos de la prenda se descargan y se juntan en un solo item con campos binarios `foto_0..foto_n`, para que Claude vea **todas las fotos en una sola llamada** y pueda cruzar la etiqueta con la prenda.\n\nEl prompt obliga a declarar si la marca y la talla salen de una **etiqueta leida** o de una inferencia. Ese campo es el que alimenta el score.',
  [separarFotos, descargarFoto, juntarFotos, clasificarPrenda, parsearClasificacion],
  { color: 5 }
);

const notaPrecio = sticky(
  '## 4. Precio y fiabilidad\n\nEl precio **no lo decide el LLM**: se calcula. Mediana de comparables recortada al 10-90%, por el factor pedido-a-pagado (0,65), por el multiplicador de estado. Sin comparables cae al tier de marca y lo dice en `fuente_precio`.\n\nEl score tambien se calcula, no se pregunta: la autoconfianza declarada de un modelo esta mal calibrada. Ajusta el factor en **Configuracion del lote** cuando tengas ventas reales.',
  [buscarComparables, calcularPrecios, escribirEnSheet],
  { color: 6 }
);

export default workflow('vinted-clasificar-lote', 'Vinted - Clasificar lote de prendas')
  .add(disparoManual)
  .to(configuracion)
  .add(disparoProgramado)
  .to(configuracion)
  .add(configuracion)
  .to(listarFotos)
  .to(leerProcesadas)
  .to(leerMarcas)
  .to(agruparFotos)
  .to(recorrerPrendas
    .onDone(resumirLote.to(avisarTelegram))
    .onEachBatch(
      separarFotos
        .to(descargarFoto)
        .to(juntarFotos)
        .to(clasificarPrenda)
        .to(parsearClasificacion)
        .to(buscarComparables)
        .to(calcularPrecios)
        .to(escribirEnSheet)
        .to(nextBatch(recorrerPrendas))
    )
  )
  .add(notaCabecera)
  .add(notaAgrupar)
  .add(notaClasificar)
  .add(notaPrecio);
