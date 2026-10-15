const REQUIRED_HEADERS = ['sku', 'name', 'unit', 'sale_price', 'purchase_cost', 'initial_stock']

function detectDelimiter(text) {
  const firstLine = text.split(/\r?\n/, 1)[0]
  let commas = 0
  let semicolons = 0
  let quoted = false
  for (let index = 0; index < firstLine.length; index += 1) {
    const char = firstLine[index]
    if (char === '"' && firstLine[index + 1] === '"' && quoted) { index += 1; continue }
    if (char === '"') quoted = !quoted
    else if (!quoted && char === ',') commas += 1
    else if (!quoted && char === ';') semicolons += 1
  }
  return semicolons > commas ? ';' : ','
}

function parseRecords(text, delimiter) {
  const rows = []
  let row = []
  let field = ''
  let quoted = false
  let justClosedQuote = false

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') { field += '"'; index += 1 }
      else if (char === '"') { quoted = false; justClosedQuote = true }
      else field += char
      continue
    }
    if (char === '"') {
      if (field.trim() || justClosedQuote) throw new Error('Hay comillas en una posición inválida.')
      quoted = true
    } else if (char === delimiter) {
      row.push(field); field = ''; justClosedQuote = false
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[index + 1] === '\n') index += 1
      row.push(field); rows.push(row); row = []; field = ''; justClosedQuote = false
    } else {
      if (justClosedQuote && !/\s/.test(char)) throw new Error('Hay texto después de una comilla de cierre.')
      if (!justClosedQuote) field += char
    }
  }
  if (quoted) throw new Error('El archivo termina con una comilla sin cerrar.')
  if (field || row.length || justClosedQuote) { row.push(field); rows.push(row) }
  return rows.filter(cells => cells.some(value => String(value).trim() !== ''))
}

function parseNumber(value, delimiter, label, rowNumber) {
  let normalized = String(value).trim()
  if (delimiter === ';' && normalized.includes(',') && !normalized.includes('.')) normalized = normalized.replace(',', '.')
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) throw new Error(`Fila ${rowNumber}: ${label} debe ser un número sin separador de miles.`)
  const number = Number(normalized)
  if (!Number.isFinite(number) || number > 1_000_000) throw new Error(`Fila ${rowNumber}: ${label} debe estar entre 0 y 1,000,000.`)
  return number
}

export function parseInventoryCsv(source) {
  if (typeof source !== 'string' || !source.trim()) throw new Error('El archivo está vacío.')
  const text = source.replace(/^\uFEFF/, '')
  const delimiter = detectDelimiter(text)
  const rows = parseRecords(text, delimiter)
  if (rows.length < 2) throw new Error('Incluye los encabezados y al menos un producto.')
  const headers = rows[0].map(value => String(value).trim().toLowerCase())
  if (new Set(headers).size !== headers.length) throw new Error('Hay encabezados repetidos.')
  if (headers.length !== REQUIRED_HEADERS.length || REQUIRED_HEADERS.some(header => !headers.includes(header))) {
    throw new Error(`Los encabezados deben ser: ${REQUIRED_HEADERS.join(', ')}.`)
  }

  const positions = Object.fromEntries(REQUIRED_HEADERS.map(header => [header, headers.indexOf(header)]))
  const seen = new Set()
  const products = []
  rows.slice(1).forEach((cells, index) => {
    const rowNumber = index + 2
    if (cells.length !== headers.length) throw new Error(`Fila ${rowNumber}: tiene ${cells.length} columnas y se esperaban ${headers.length}.`)
    const value = key => String(cells[positions[key]] ?? '').trim()
    const sku = value('sku').toUpperCase()
    const name = value('name')
    const unit = value('unit')
    const salePrice = parseNumber(value('sale_price'), delimiter, 'sale_price', rowNumber)
    const purchaseCost = parseNumber(value('purchase_cost'), delimiter, 'purchase_cost', rowNumber)
    const stockText = value('initial_stock')
    if (!/^[A-Z0-9_-]{3,40}$/.test(sku) || !name || name.length > 180 || !unit || unit.length > 32) {
      throw new Error(`Fila ${rowNumber}: SKU, nombre o unidad inválidos.`)
    }
    if (!/^\d+$/.test(stockText) || Number(stockText) > 1_000_000) throw new Error(`Fila ${rowNumber}: initial_stock debe ser un entero entre 0 y 1,000,000.`)
    if (seen.has(sku)) throw new Error(`Fila ${rowNumber}: el SKU ${sku} está duplicado.`)
    seen.add(sku)
    products.push({ sku, name, unit, sale_price: salePrice, purchase_cost: purchaseCost, initial_stock: Number(stockText) })
  })
  if (!products.length || products.length > 500) throw new Error('La carga debe contener entre 1 y 500 productos.')
  return products
}
