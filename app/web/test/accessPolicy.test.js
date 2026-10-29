import assert from 'node:assert/strict'
import test from 'node:test'
import { createPortalNavigation, internalRoles, opsRoles, roleLabels, writeRoles } from '../src/accessPolicy.js'

test('ERP access is enabled only when the authenticated session has an effective permission', async () => {
  const policy = await import('../src/accessPolicy.js')
  assert.equal(typeof policy.hasErpAccess, 'function')
  assert.equal(policy.hasErpAccess(['sales:read']), true)
  assert.equal(policy.hasErpAccess([]), false)
  assert.equal(policy.hasErpAccess(undefined), false)
})

const expectedNavigation = {
  customer: ['dashboard', 'orders', 'account'],
  sales: ['dashboard', 'orders', 'erp', 'account'],
  warehouse: ['dashboard', 'orders', 'operations', 'erp', 'account'],
  operations: ['dashboard', 'orders', 'operations', 'erp', 'audit', 'account'],
  auditor: ['dashboard', 'orders', 'operations', 'erp', 'audit', 'account'],
  admin: ['dashboard', 'orders', 'operations', 'erp', 'administration', 'audit', 'account'],
}

for (const [role, expected] of Object.entries(expectedNavigation)) {
  test(`navigation for ${role} matches the minimum-privilege menu`, () => {
    assert.deepEqual(createPortalNavigation(role).map(([key]) => key), expected)
    assert.ok(roleLabels[role])
  })
}

test('unknown roles fail closed and receive no internal or administrative modules', () => {
  const keys = createPortalNavigation('unexpected-role').map(([key]) => key)
  assert.deepEqual(keys, ['dashboard', 'orders', 'account'])
  assert.equal(internalRoles.has('unexpected-role'), false)
  assert.equal(opsRoles.has('unexpected-role'), false)
})

test('only customer, sales, and administrator roles are granted portal write capabilities', () => {
  assert.deepEqual([...writeRoles].sort(), ['admin', 'customer', 'sales'])
})
