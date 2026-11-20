import test from 'node:test'
import assert from 'node:assert/strict'
import { createPortalApi } from '../../aws_release/current/static/assets/portal-api.mjs'

test('concurrent writes share one session lookup and send the issued CSRF token', async () => {
  const calls = []
  const api = createPortalApi({}, async (path, options) => {
    calls.push({ path, options })
    if (path === '/api/auth/session') return Response.json({ csrf_token: 'test-token' })
    return new Response(null, { status: 204 })
  })

  assert.deepEqual(await Promise.all([
    api('/api/admin/users/1', { method: 'patch', body: '{}' }),
    api('/api/auth/logout', { method: 'POST' }),
  ]), [null, null])

  assert.equal(calls.filter(call => call.path === '/api/auth/session').length, 1)
  for (const { options } of calls.slice(1)) {
    assert.equal(options.headers.get('X-CSRF-Token'), 'test-token')
    assert.equal(options.credentials, 'same-origin')
    assert.equal(options.cache, 'no-store')
  }
  assert.equal(calls[1].options.method, 'PATCH')
  assert.equal(calls[1].options.headers.get('Content-Type'), 'application/json')
})

test('the API client preserves pagination headers and reports rejected requests by code', async () => {
  const api = createPortalApi({ insufficient_role: 'Acceso restringido' }, async path => {
    if (path === '/api/outbox') return Response.json([], { headers: { 'X-Total-Count': '3' } })
    return Response.json({ error: 'insufficient_role' }, { status: 403 })
  })

  const page = await api('/api/outbox', { includeMeta: true })
  assert.deepEqual(page.payload, [])
  assert.equal(page.headers.get('X-Total-Count'), '3')
  await assert.rejects(api('/api/admin/users'), {
    message: 'Acceso restringido', status: 403, code: 'insufficient_role',
  })
  await assert.rejects(api('//other.invalid/api/auth/session'), TypeError)
})
