import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parseInventoryCsv } from '../src/catalogCsv.js'

test('parses Excel CSV with headers, UTF-8 BOM, and decimal points', () => {
  const rows = parseInventoryCsv('\uFEFFsku,name,unit,sale_price,purchase_cost,initial_stock\nSKU-TEST-001,"Café, tostado",saco,12.50,9.75,40\n')
  assert.deepEqual(rows, [{ sku: 'SKU-TEST-001', name: 'Café, tostado', unit: 'saco', sale_price: 12.5, purchase_cost: 9.75, initial_stock: 40 }])
})

test('parses semicolon-delimited regional Excel CSV with decimal commas and quoted newlines', () => {
  const rows = parseInventoryCsv('sku;name;unit;sale_price;purchase_cost;initial_stock\r\nSKU-TEST-002;"Producto\nregional";caja;12,50;9,75;3\r\n')
  assert.equal(rows[0].name, 'Producto\nregional')
  assert.equal(rows[0].sale_price, 12.5)
  assert.equal(rows[0].purchase_cost, 9.75)
})

test('the downloadable synthetic catalog template matches the import schema', () => {
  const template = readFileSync(new URL('../public/templates/inventario_sintetico.csv', import.meta.url), 'utf8')
  const products = parseInventoryCsv(template)
  assert.equal(products.length, 12)
  assert.equal(products[0].sku, 'SKU-ARROZ-001')
  assert.equal(products.at(-1).sku, 'SKU-MAIZ-001')
})

test('the AWS ERP package serves the exact parser covered by these tests', () => {
  const source = readFileSync(new URL('../src/catalogCsv.js', import.meta.url), 'utf8')
  const release = readFileSync(new URL('../../aws_release/current/static/assets/catalogCsv.js', import.meta.url), 'utf8')
  assert.equal(release.replace(/\r\n/g, '\n'), source.replace(/\r\n/g, '\n'))
})

test('rejects duplicate SKUs and misspelled headers before submission', () => {
  assert.throws(() => parseInventoryCsv('sku,name,unit,sale_price,purchase_cost,initial_stock\nSKU-A-001,A,unidad,1,1,1\nSKU-A-001,B,unidad,1,1,1'), /duplicado/)
  assert.throws(() => parseInventoryCsv('sku,name,unit,price,purchase_cost,initial_stock\nSKU-A-001,A,unidad,1,1,1'), /encabezados/)
})

test('rejects unsafe, malformed, or oversized rows', () => {
  assert.throws(() => parseInventoryCsv('sku,name,unit,sale_price,purchase_cost,initial_stock\nSKU-A-001,A,unidad,1.234,1,1'), /separador de miles/)
  assert.throws(() => parseInventoryCsv('sku,name,unit,sale_price,purchase_cost,initial_stock\nSKU-A-001,A,unidad,1,1,-1'), /entero/)
  assert.throws(() => parseInventoryCsv('sku,name,unit,sale_price,purchase_cost,initial_stock\nSKU-A-001,"sin cierre,unidad,1,1,1'), /sin cerrar/)
  const header = 'sku,name,unit,sale_price,purchase_cost,initial_stock'
  const excessiveRows = Array.from({ length: 501 }, (_, index) =>
    `SKU-${String(index).padStart(3, '0')},Producto ${index},unidad,1,0.5,0`,
  ).join('\n')
  assert.throws(() => parseInventoryCsv(`${header}\n${excessiveRows}`), /entre 1 y 500 productos/)
})
