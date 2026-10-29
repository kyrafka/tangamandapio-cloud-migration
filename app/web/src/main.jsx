import React from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './erp.css'
import './account.css'
import './admin.css'
import { createPortalNavigation, hasErpAccess, internalRoles, opsRoles, roleLabels, writeRoles } from './accessPolicy.js'
import { parseInventoryCsv } from './catalogCsv.js'

const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })
const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS'])
let csrfToken = ''

async function api(path, options = {}) {
  const method = String(options.method || 'GET').toUpperCase()
  if (!safeMethods.has(method) && !csrfToken) await api('/api/auth/session')
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (!safeMethods.has(method) && csrfToken) headers.set('X-CSRF-Token', csrfToken)
  const response = await fetch(path, { ...options, method, credentials: 'same-origin', cache: 'no-store', headers })
  const body = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) {
    const messages = {
      current_password_invalid: 'La contraseña actual no coincide.',
      invalid_new_password: 'La nueva contraseña debe tener entre 12 y 256 caracteres.',
      password_reuse_not_allowed: 'Elige una contraseña diferente a la actual.',
      password_change_required: 'Debes cambiar tu contraseña temporal antes de continuar.',
      use_self_service_password_change: 'Usa “Mi cuenta” para cambiar tu propia contraseña.',
    }
    throw Object.assign(new Error(messages[body?.error] || body?.error || `HTTP ${response.status}`), { status: response.status, code: body?.error })
  }
  if (body?.csrf_token) csrfToken = body.csrf_token
  return body
}
function Badge({ children, tone = 'neutral' }) { return <span className={`badge ${tone}`}>{children}</span> }
function Empty({ text }) { return <p className="empty">{text}</p> }

function Login({ onAuthenticated, notice }) {
  const [username, setUsername] = React.useState(''), [password, setPassword] = React.useState(''), [error, setError] = React.useState(''), [loading, setLoading] = React.useState(false)
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError('')
    try { await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); await onAuthenticated() }
    catch (reason) { setError(reason.message === 'invalid_credentials' ? 'Credenciales inválidas o cuenta deshabilitada.' : reason.message) }
    finally { setLoading(false) }
  }
  return <main className="auth-shell"><section className="brand-pane"><p className="eyebrow">Tangamandapio S.A.C. · Portal B2B</p><h1>Operación comercial con trazabilidad multicloud.</h1><p>Pedidos en AWS, integración durable hacia el WMS de Azure y controles de acceso por rol.</p><div className="security-list"><span>Acceso autenticado</span><span>Roles de mínimo privilegio</span><span>Auditoría de operaciones</span></div></section><section className="login-card"><p className="eyebrow">Acceso corporativo</p><h2>Iniciar sesión</h2><form onSubmit={submit}><label>Usuario<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="usuario@empresa" required /></label><label>Contraseña<input autoComplete="current-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label><button className="primary" disabled={loading}>{loading ? 'Verificando…' : 'Ingresar al portal'}</button></form>{error && <p className="alert error" role="alert">{error}</p>}{notice && <p className="alert success" role="status">{notice}</p>}<p className="login-note">Las cuentas son administradas por Tangamandapio. No existe registro público.</p></section></main>
}

function PasswordChange({ user, forced = false, onComplete }) {
  const [currentPassword, setCurrentPassword] = React.useState(''), [newPassword, setNewPassword] = React.useState(''), [confirmation, setConfirmation] = React.useState(''), [error, setError] = React.useState(''), [saving, setSaving] = React.useState(false)
  async function submit(event) {
    event.preventDefault(); setError('')
    if (newPassword !== confirmation) { setError('Las contraseñas nuevas no coinciden.'); return }
    setSaving(true)
    try {
      await api('/api/auth/password', { method: 'POST', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) })
      onComplete()
    } catch (reason) { setError(reason.message) } finally { setSaving(false) }
  }
  const card = <section className={forced ? 'login-card password-card' : 'card form-card'}><p className="eyebrow">Seguridad de la cuenta</p><h2>{forced ? 'Cambia tu contraseña temporal' : 'Cambiar contraseña'}</h2>{forced && <p className="login-note">Antes de continuar, reemplaza la clave temporal asignada por una propia.</p>}<form onSubmit={submit}><label>Contraseña actual<input autoComplete="current-password" type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} minLength="1" required /></label><label>Nueva contraseña<input autoComplete="new-password" type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength="12" maxLength="256" required /></label><label>Confirmar nueva contraseña<input autoComplete="new-password" type="password" value={confirmation} onChange={event => setConfirmation(event.target.value)} minLength="12" maxLength="256" required /></label><p className="form-hint">Usa entre 12 y 256 caracteres y una clave diferente a la actual.</p><button className="primary" disabled={saving}>{saving ? 'Actualizando…' : 'Guardar y volver a iniciar sesión'}</button></form>{error && <p className="alert error" role="alert">{error}</p>}</section>
  if (forced) return <main className="auth-shell"><section className="brand-pane"><p className="eyebrow">Acceso protegido</p><h1>Una actualización necesaria para tu cuenta.</h1><p>{user.username} · {roleLabels[user.role]}</p><div className="security-list"><span>El cambio revoca sesiones anteriores</span><span>La nueva clave no se muestra a otros usuarios</span></div></section>{card}</main>
  return card
}

function Dashboard({ dashboard, health, azure, isOps }) { const databaseStatus = health.status === 'ok' ? 'ok' : health.status === 'degraded' ? 'degradada' : '—'; return <><section className="metric-grid"><article><small>Pedidos visibles</small><strong>{dashboard?.orders ?? '—'}</strong><span>Según permisos de tu rol</span></article><article><small>Eventos entregados</small><strong>{dashboard?.outbox?.delivered ?? '—'}</strong><span>Confirmados por el flujo WMS</span></article><article><small>Eventos pendientes</small><strong>{dashboard?.outbox?.pending ?? '—'}</strong><span>Outbox con reintento seguro</span></article><article><small>Base de datos AWS</small><strong>{databaseStatus}</strong><span>Disponibilidad del portal</span></article></section><section className="flow-card"><div><p className="eyebrow">Arquitectura en ejecución</p><h2>Pedido → transacción durable → WMS</h2><p>El pedido se confirma primero en AWS. Después, el evento se entrega al WMS de Azure sin perder la transacción si el servicio remoto no estuviera disponible.</p></div><div className="flow"><span>AWS<br/><b>Portal y RDS</b></span><i>→</i><span>Outbox<br/><b>Evento auditable</b></span><i>→</i><span>Azure<br/><b>Function · Blob · Queue</b></span></div></section>{isOps && <section className="service-card"><div><p className="eyebrow">Integración Azure</p><h2>{azure?.status === 'connected' ? 'Servicio WMS conectado' : 'Estado de WMS pendiente'}</h2><p>{azure?.status === 'connected' ? 'El endpoint de operaciones responde y la autenticación de servicio está disponible.' : 'Consulta el módulo de Integración WMS para revisar el estado.'}</p></div><Badge tone={azure?.status === 'connected' ? 'success' : 'warning'}>{azure?.status || 'sin dato'}</Badge></section>}</> }

function Orders({ orders, canWrite, onCreated }) {
  const [customer, setCustomer] = React.useState(''), [reference, setReference] = React.useState(''), [total, setTotal] = React.useState(''), [sending, setSending] = React.useState(false)
  async function submit(event) { event.preventDefault(); setSending(true); try { const created = await api('/api/orders', { method: 'POST', body: JSON.stringify({ customer, reference, total: Number(total) }) }); setCustomer(''); setReference(''); setTotal(''); await onCreated(`Pedido #${created.id} registrado y enviado al flujo de cumplimiento.`) } catch (reason) { await onCreated(reason.message) } finally { setSending(false) } }
  return <div className="content-grid"><section className="card orders-card"><div className="card-title"><div><p className="eyebrow">Información comercial</p><h2>Pedidos</h2></div><Badge>{orders.length} visibles</Badge></div>{orders.length ? <div className="table-wrap"><table><thead><tr><th>ID</th><th>Cliente</th><th>Referencia</th><th>Empresa</th><th>Estado</th><th>Total</th></tr></thead><tbody>{orders.map(order => <tr key={order.id}><td>#{order.id}</td><td><b>{order.customer}</b><small>{new Date(order.created_at).toLocaleString('es-PE')}</small></td><td>{order.reference || '—'}</td><td>{order.company || 'Legado'}</td><td><Badge tone="warning">{order.status || 'creado'}</Badge></td><td>{money.format(order.total)}</td></tr>)}</tbody></table></div> : <Empty text="Todavía no hay pedidos visibles para esta cuenta." />}</section>{canWrite && <section className="card form-card"><p className="eyebrow">Operación comercial</p><h2>Nuevo pedido</h2><form onSubmit={submit}><label>Cliente<input value={customer} onChange={e => setCustomer(e.target.value)} required maxLength="120" placeholder="Razón social o contacto" /></label><label>Referencia<input value={reference} onChange={e => setReference(e.target.value)} maxLength="80" placeholder="OC o referencia interna" /></label><label>Total (S/)<input value={total} onChange={e => setTotal(e.target.value)} required type="number" min="0" step="0.01" placeholder="0.00" /></label><button className="primary" disabled={sending}>{sending ? 'Confirmando…' : 'Crear pedido'}</button></form></section>}</div>
}

function Operations({ outbox, azure, onRetry }) { return <section className="card"><div className="card-title"><div><p className="eyebrow">Confiabilidad de integración</p><h2>Eventos hacia WMS Azure</h2></div><Badge tone={azure?.status === 'connected' ? 'success' : 'warning'}>{azure?.status || 'sin dato'}</Badge></div><p className="muted">Un pedido nunca se revierte por una falla remota: el evento queda en outbox, se audita y solo Operaciones puede solicitar un reintento.</p>{outbox.length ? <div className="table-wrap"><table><thead><tr><th>Evento</th><th>Pedido</th><th>Estado</th><th>Intentos</th><th>Acción</th></tr></thead><tbody>{outbox.map(event => <tr key={event.event_id}><td className="mono">{event.event_id}</td><td>#{event.order_id}</td><td><Badge tone={event.status === 'delivered' ? 'success' : 'warning'}>{event.status}</Badge></td><td>{event.attempts}</td><td>{event.status !== 'delivered' && <button className="secondary" onClick={() => onRetry(event.event_id)}>Reintentar</button>}</td></tr>)}</tbody></table></div> : <Empty text="No hay eventos pendientes o entregados todavía." />}</section> }

function Users({ users, companies, actorId, onCreated }) {
  const [form, setForm] = React.useState({ username: '', password: '', role: 'customer', company_id: '' })
  const [saving, setSaving] = React.useState(false), [confirmResetId, setConfirmResetId] = React.useState(null), [resettingId, setResettingId] = React.useState(null), [temporaryCredential, setTemporaryCredential] = React.useState(null), [copied, setCopied] = React.useState(false)
  async function submit(event) {
    event.preventDefault(); setSaving(true)
    try {
      await api('/api/admin/users', { method: 'POST', body: JSON.stringify({ ...form, company_id: Number(form.company_id) }) })
      setForm({ username: '', password: '', role: 'customer', company_id: '' })
      await onCreated('Cuenta creada. El usuario deberá cambiar su contraseña temporal al ingresar.')
    } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) }
  }
  async function resetPassword(user) {
    setResettingId(user.id)
    try {
      const result = await api(`/api/admin/users/${user.id}/reset-password`, { method: 'POST', body: JSON.stringify({}) })
      setTemporaryCredential({ username: result.username, password: result.temporary_password })
      setCopied(false); setConfirmResetId(null)
      await onCreated('Se generó una clave temporal de una sola entrega; compártela por un canal seguro.')
    } catch (reason) { await onCreated(reason.message) } finally { setResettingId(null) }
  }
  async function copyTemporaryCredential() {
    try { await navigator.clipboard.writeText(temporaryCredential.password); setCopied(true) }
    catch { setCopied(false) }
  }
  return <div className="content-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Gobierno de identidad</p><h2>Usuarios y roles</h2></div><Badge>{users.length} cuentas</Badge></div><div className="table-wrap"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Empresa</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{users.map(item => <tr key={item.id}><td>{item.username}</td><td>{roleLabels[item.role]}</td><td>{item.company}</td><td><Badge tone={item.active ? 'success' : 'danger'}>{item.active ? 'activo' : 'bloqueado'}</Badge>{item.must_change_password && <small>Cambio temporal pendiente</small>}</td><td>{item.id !== actorId && item.active && (confirmResetId === item.id ? <div className="inline-actions"><button className="secondary" disabled={resettingId === item.id} onClick={() => resetPassword(item)}>{resettingId === item.id ? 'Generando…' : 'Confirmar'}</button><button className="secondary" onClick={() => setConfirmResetId(null)}>Cancelar</button></div> : <button className="secondary" onClick={() => { setTemporaryCredential(null); setConfirmResetId(item.id) }}>Restablecer</button>)}</td></tr>)}</tbody></table></div>{temporaryCredential && <aside className="temporary-credential" role="status"><div><p className="eyebrow">Clave temporal · mostrar solo ahora</p><strong>{temporaryCredential.username}</strong><code>{temporaryCredential.password}</code><small>El usuario deberá cambiarla al iniciar sesión. No se guarda para volver a consultarla.</small></div><button className="secondary" onClick={copyTemporaryCredential}>{copied ? 'Copiada' : 'Copiar clave'}</button></aside>}</section><section className="card form-card"><p className="eyebrow">Provisionamiento</p><h2>Nueva cuenta</h2><form onSubmit={submit}><label>Usuario<input value={form.username} onChange={event => setForm({ ...form, username: event.target.value })} required /></label><label>Contraseña temporal<input type="password" value={form.password} minLength="12" onChange={event => setForm({ ...form, password: event.target.value })} required /></label><label>Empresa<select value={form.company_id} onChange={event => setForm({ ...form, company_id: event.target.value })} required><option value="">Selecciona una empresa</option>{companies.map(company => <option value={company.id} key={company.id}>{company.name}</option>)}</select></label><label>Rol<select value={form.role} onChange={event => setForm({ ...form, role: event.target.value })}>{Object.entries(roleLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label><button className="primary" disabled={saving}>{saving ? 'Creando…' : 'Crear cuenta'}</button></form></section></div>
}

function Companies({ companies, onCreated }) {
  const [form, setForm] = React.useState({ name: '', slug: '' })
  const [saving, setSaving] = React.useState(false)
  async function submit(event) {
    event.preventDefault(); setSaving(true)
    try {
      await api('/api/admin/companies', { method: 'POST', body: JSON.stringify(form) })
      setForm({ name: '', slug: '' })
      await onCreated('Empresa B2B creada y disponible para asignar cuentas.')
    } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) }
  }
  return <div className="content-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Aislamiento B2B</p><h2>Empresas registradas</h2></div><Badge>{companies.length} empresas</Badge></div><div className="table-wrap"><table><thead><tr><th>Empresa</th><th>Identificador</th><th>Usuarios</th><th>Creada</th></tr></thead><tbody>{companies.map(company => <tr key={company.id}><td><b>{company.name}</b></td><td className="mono">{company.slug}</td><td>{company.users}</td><td>{new Date(company.created_at).toLocaleDateString('es-PE')}</td></tr>)}</tbody></table></div></section><section className="card form-card"><p className="eyebrow">Nuevo tenant</p><h2>Registrar empresa</h2><form onSubmit={submit}><label>Razón social<input value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} maxLength="160" required /></label><label>Identificador técnico<input value={form.slug} onChange={event => setForm({ ...form, slug: event.target.value.toLowerCase() })} pattern="[a-z0-9-]+" maxLength="80" placeholder="cliente-b2b" required /></label><button className="primary" disabled={saving}>{saving ? 'Registrando…' : 'Crear empresa'}</button></form></section></div>
}
function Audit({ entries }) { return <section className="card"><div className="card-title"><div><p className="eyebrow">Trazabilidad</p><h2>Auditoría de operaciones</h2></div><Badge>{entries.length} eventos</Badge></div>{entries.length ? <div className="table-wrap"><table><thead><tr><th>Fecha</th><th>Actor</th><th>Acción</th><th>Objeto</th></tr></thead><tbody>{entries.map(entry => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString('es-PE')}</td><td>{entry.actor}</td><td><span className="mono">{entry.action}</span></td><td>{entry.subject_type} {entry.subject_id || ''}</td></tr>)}</tbody></table></div> : <Empty text="No se registraron eventos de auditoría aún." />}</section> }

const erpRoleLabels = { erp_admin: 'Administración ERP', erp_sales: 'Ventas', erp_finance: 'Finanzas', erp_purchasing: 'Compras', erp_master_data: 'Datos maestros', erp_auditor: 'Auditoría ERP' }
const pen = value => money.format(Number(value || 0))

function OrderComposer({ type, partners, products, onCreated }) {
  const [partnerId, setPartnerId] = React.useState('')
  const [items, setItems] = React.useState([{ sku: '', quantity: 1 }])
  const [saving, setSaving] = React.useState(false)
  const expectedKind = type === 'sales' ? ['customer', 'both'] : ['supplier', 'both']
  const eligible = partners.filter(item => expectedKind.includes(item.kind) && item.active)
  function updateLine(index, key, value) { setItems(current => current.map((line, i) => i === index ? { ...line, [key]: value } : line)) }
  async function submit(event) {
    event.preventDefault(); setSaving(true)
    try {
      const path = type === 'sales' ? '/api/erp/sales/orders' : '/api/erp/purchases/orders'
      const result = await api(path, { method: 'POST', body: JSON.stringify({ partner_id: Number(partnerId), items: items.map(line => ({ sku: line.sku, quantity: Number(line.quantity) })) }) })
      setItems([{ sku: '', quantity: 1 }]); setPartnerId('')
      await onCreated(`${type === 'sales' ? 'Pedido de venta' : 'Orden de compra'} ${result.reference} registrado. ${type === 'sales' ? 'Azure validará el stock y el evento quedará trazado.' : 'Cuando llegue la mercadería, registra la recepción para actualizar el WMS Azure.'}`)
    } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) }
  }
  return <section className="card form-card"><p className="eyebrow">Nuevo documento</p><h2>{type === 'sales' ? 'Pedido de venta' : 'Orden de compra'}</h2>{!eligible.length && <p className="alert">Primero registra un {type === 'sales' ? 'cliente' : 'proveedor'} en Maestros.</p>}<form onSubmit={submit}>
    <label>{type === 'sales' ? 'Cliente' : 'Proveedor'}<select value={partnerId} onChange={event => setPartnerId(event.target.value)} required><option value="">Selecciona una empresa</option>{eligible.map(partner => <option key={partner.id} value={partner.id}>{partner.name}</option>)}</select></label>
    <div className="erp-lines-heading"><strong>Productos</strong><button className="text-button" type="button" onClick={() => setItems(lines => [...lines, { sku: '', quantity: 1 }])} disabled={!products.length}>Añadir línea</button></div>
    {items.map((line, index) => <div className="erp-line" key={index}><label>SKU<select value={line.sku} onChange={event => updateLine(index, 'sku', event.target.value)} required><option value="">Selecciona producto</option>{products.filter(item => item.active).map(product => <option key={product.sku} value={product.sku}>{product.name} · {product.sku}{product.on_hand == null ? '' : ` · ${product.on_hand} disp.`}</option>)}</select></label><label>Cantidad<input type="number" min="1" max="1000" step="1" value={line.quantity} onChange={event => updateLine(index, 'quantity', event.target.value)} required /></label>{items.length > 1 && <button className="icon-button" type="button" aria-label="Quitar línea" onClick={() => setItems(lines => lines.filter((_, i) => i !== index))}>×</button>}</div>)}
    <p className="form-hint">El precio/costo lo toma el ERP. El saldo disponible solo se consulta a Azure; Azure decide la aceptación real del movimiento.</p><button className="primary" disabled={saving || !products.length || !eligible.length}>{saving ? 'Guardando…' : type === 'sales' ? 'Registrar venta y enviar a WMS' : 'Emitir orden de compra'}</button>
  </form></section>
}

function Erp({ user, access, onNotify }) {
  const permissions = new Set(access?.permissions || [])
  const can = permission => user.role === 'admin' || permissions.has(permission)
  const [section, setSection] = React.useState(user.role === 'admin' || permissions.size ? 'overview' : 'mail'), [overview, setOverview] = React.useState(null), [partners, setPartners] = React.useState([]), [products, setProducts] = React.useState([]), [wms, setWms] = React.useState(null), [sales, setSales] = React.useState([]), [purchases, setPurchases] = React.useState([]), [finance, setFinance] = React.useState([]), [users, setUsers] = React.useState([]), [loading, setLoading] = React.useState(false)
  const tabs = [
    ['overview', 'Resumen', can('reports:read')], ['masters', 'Maestros', can('master:read')], ['sales', 'Ventas', can('sales:read')],
    ['purchases', 'Compras', can('purchase:read')], ['finance', 'Finanzas', can('finance:read')], ['access', 'Accesos', user.role === 'admin'], ['mail', 'Correo interno', true],
  ].filter(item => item[2])
  const refresh = React.useCallback(async (target = section) => {
    setLoading(true)
    try {
      if (target === 'overview') setOverview(await api('/api/erp/overview'))
      if (target === 'masters') {
        const [p, productState] = await Promise.all([api('/api/erp/partners'), api('/api/erp/products')])
        setPartners(p); setProducts(productState.products || []); setWms(productState.wms)
      }
      if (target === 'sales') {
        const [orders, p, productState] = await Promise.all([api('/api/erp/sales/orders'), api('/api/erp/partners'), api('/api/erp/products')])
        setSales(orders); setPartners(p); setProducts(productState.products || []); setWms(productState.wms)
      }
      if (target === 'purchases') {
        const [orders, p, productState] = await Promise.all([api('/api/erp/purchases/orders'), api('/api/erp/partners'), api('/api/erp/products')])
        setPurchases(orders); setPartners(p); setProducts(productState.products || []); setWms(productState.wms)
      }
      if (target === 'finance') {
        const [docs, summary, p] = await Promise.all([api('/api/erp/finance/documents'), api('/api/erp/overview'), api('/api/erp/partners')])
        setFinance(docs); setOverview(summary); setPartners(p)
      }
      if (target === 'access') setUsers(await api('/api/erp/users'))
    } catch (reason) { onNotify(`No se pudo cargar ${target}: ${reason.message}`) }
    finally { setLoading(false) }
  }, [onNotify, section])
  React.useEffect(() => { if (section !== 'mail' && tabs.some(tab => tab[0] === section)) refresh(section) }, [section, refresh])
  async function notifyAndRefresh(message, target = section) { onNotify(message); await refresh(target) }
  async function refreshSale(id) { try { const result = await api(`/api/erp/sales/orders/${id}/refresh`, { method: 'POST' }); await notifyAndRefresh(`WMS: ${result.status}${result.wms_result?.note ? ` · ${result.wms_result.note}` : ''}`, 'sales') } catch (reason) { onNotify(reason.message) } }
  async function receivePurchase(id) { try { const result = await api(`/api/erp/purchases/orders/${id}/receive`, { method: 'POST' }); await notifyAndRefresh(`Recepción enviada a Azure. Estado: ${result.status}. Actualiza el estado al procesarse.`, 'purchases') } catch (reason) { onNotify(reason.message) } }
  async function refreshPurchase(id) { try { const result = await api(`/api/erp/purchases/orders/${id}/refresh`, { method: 'POST' }); await notifyAndRefresh(`Recepción WMS: ${result.status}${result.wms_result?.note ? ` · ${result.wms_result.note}` : ''}`, 'purchases') } catch (reason) { onNotify(reason.message) } }
  return <section className="erp-page">
    <div className="erp-intro"><div><p className="eyebrow">Gestión interna · módulo local</p><h2>ERP corporativo</h2><p>Ventas, compras, finanzas y maestros conectados al WMS de Azure. El ERP no guarda saldos de inventario.</p></div><span className={`erp-source ${wms?.status === 'connected' || overview?.wms?.status === 'connected' ? 'ok' : 'warn'}`}><i />WMS Azure · {wms?.status || overview?.wms?.status || 'consultando'}</span></div>
    <div className="erp-tabs" role="tablist" aria-label="Secciones del ERP">{tabs.map(([key, label]) => <button type="button" role="tab" aria-selected={section === key} className={section === key ? 'selected' : ''} key={key} onClick={() => setSection(key)}>{label}</button>)}<button className="quiet-button" type="button" onClick={() => refresh()} disabled={loading}>{loading ? 'Actualizando…' : 'Actualizar'}</button></div>
    {section === 'overview' && <><div className="metric-grid erp-metrics">{can('sales:read') && <article><small>Pedidos de venta</small><strong>{overview?.metrics?.sales_orders ?? '—'}</strong><span>Registrados en el ERP</span></article>}{can('purchase:read') && <article><small>Órdenes de compra</small><strong>{overview?.metrics?.purchase_orders ?? '—'}</strong><span>Seguimiento de recepción</span></article>}{can('finance:read') && <><article><small>Cuentas por cobrar</small><strong>{pen(overview?.metrics?.open_receivables)}</strong><span>Saldo abierto</span></article><article><small>Cuentas por pagar</small><strong>{pen(overview?.metrics?.open_payables)}</strong><span>Saldo abierto</span></article></>}</div><section className="card erp-explainer"><div><p className="eyebrow">Propiedad de datos</p><h3>El ERP organiza el negocio; Azure controla las existencias</h3><p>Una venta envía SKU y cantidades al WMS. Una recepción de compra solicita reponerlas. El saldo mostrado se consulta a Azure en el momento; el ERP no lo replica.</p></div><div className="erp-callout"><strong>{overview?.wms?.mode === 'demo-inventory-ledger' ? 'Modo de laboratorio' : overview?.wms?.status === 'connected' ? 'WMS conectado' : 'WMS sin conexión'}</strong><span>{overview?.wms?.note || 'La disponibilidad requiere una respuesta actual de Azure.'}</span></div></section></>}
    {section === 'masters' && <div className="content-grid erp-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Relaciones comerciales</p><h3>Clientes y proveedores</h3></div><Badge>{partners.length}</Badge></div>{partners.length ? <div className="table-wrap"><table><thead><tr><th>Razón social</th><th>Tipo</th><th>RUC / ID</th><th>Contacto</th></tr></thead><tbody>{partners.map(item => <tr key={item.id}><td><b>{item.name}</b></td><td>{item.kind}</td><td>{item.tax_id || '—'}</td><td>{item.email || item.phone || '—'}</td></tr>)}</tbody></table></div> : <Empty text="Aún no hay socios comerciales. Registra un cliente o proveedor para operar." />}</section><PartnerForm canWrite={can('master:write')} onCreated={message => notifyAndRefresh(message, 'masters')} /><ProductMaster canWrite={can('master:write')} products={products} wms={wms} onCreated={message => notifyAndRefresh(message, 'masters')} /></div>}
    {section === 'sales' && <div className="content-grid erp-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Ciclo de venta</p><h3>Pedidos comerciales</h3></div><Badge>{sales.length}</Badge></div>{sales.length ? <div className="table-wrap"><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Líneas</th><th>Estado WMS</th><th>Total</th><th>Acción</th></tr></thead><tbody>{sales.map(order => <tr key={order.id}><td><b>{order.reference}</b><small>{new Date(order.created_at).toLocaleString('es-PE')}</small></td><td>{order.partner_name}</td><td>{order.items.map(item => `${item.sku} × ${item.quantity}`).join(', ')}</td><td><Badge tone={order.status.includes('completed') ? 'success' : order.status === 'rejected' ? 'danger' : 'warning'}>{order.status}</Badge></td><td>{pen(order.total)}</td><td>{!['completed_demo', 'completed', 'rejected'].includes(order.status) && <button className="secondary" type="button" onClick={() => refreshSale(order.id)}>Consultar Azure</button>}</td></tr>)}</tbody></table></div> : <Empty text="Todavía no hay pedidos de venta del ERP." />}</section>{can('sales:write') && <OrderComposer type="sales" partners={partners} products={products} onCreated={message => notifyAndRefresh(message, 'sales')} />}</div>}
    {section === 'purchases' && <div className="content-grid erp-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Abastecimiento</p><h3>Órdenes de compra</h3></div><Badge>{purchases.length}</Badge></div>{purchases.length ? <div className="table-wrap"><table><thead><tr><th>Orden</th><th>Proveedor</th><th>Líneas</th><th>Estado</th><th>Total</th><th>Acciones</th></tr></thead><tbody>{purchases.map(order => <tr key={order.id}><td><b>{order.reference}</b></td><td>{order.partner_name}</td><td>{order.items.map(item => `${item.sku} × ${item.quantity}`).join(', ')}</td><td><Badge tone={order.status.includes('received') ? 'success' : 'warning'}>{order.status}</Badge></td><td>{pen(order.total)}</td><td>{order.status === 'ordered' ? <button className="secondary" type="button" onClick={() => receivePurchase(order.id)}>Registrar recepción</button> : order.status === 'receipt_pending' ? <button className="secondary" type="button" onClick={() => refreshPurchase(order.id)}>Consultar Azure</button> : '—'}</td></tr>)}</tbody></table></div> : <Empty text="Todavía no hay órdenes de compra." />}</section>{can('purchase:write') && <OrderComposer type="purchases" partners={partners} products={products} onCreated={message => notifyAndRefresh(message, 'purchases')} />}</div>}
    {section === 'finance' && <FinancePanel canWrite={can('finance:write')} documents={finance} partners={partners} summary={overview} onCreated={message => notifyAndRefresh(message, 'finance')} />}
    {section === 'access' && <ErpAccess users={users} onCreated={message => notifyAndRefresh(message, 'access')} />}
    {section === 'mail' && <InternalMail user={user} onNotify={onNotify} />}
  </section>
}

function PartnerForm({ onCreated, canWrite }) {
  const [form, setForm] = React.useState({ kind: 'customer', name: '', tax_id: '', email: '', phone: '', address: '' }), [saving, setSaving] = React.useState(false)
  async function submit(event) { event.preventDefault(); setSaving(true); try { await api('/api/erp/partners', { method: 'POST', body: JSON.stringify(form) }); setForm({ kind: 'customer', name: '', tax_id: '', email: '', phone: '', address: '' }); await onCreated('Socio comercial guardado en el ERP.') } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) } }
  return canWrite && <section className="card form-card"><p className="eyebrow">Maestro comercial</p><h3>Nuevo cliente o proveedor</h3><form onSubmit={submit}><label>Tipo<select value={form.kind} onChange={e => setForm({ ...form, kind: e.target.value })}><option value="customer">Cliente</option><option value="supplier">Proveedor</option><option value="both">Ambos</option></select></label><label>Razón social<input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} maxLength="160" required /></label><label>RUC / identificador<input value={form.tax_id} onChange={e => setForm({ ...form, tax_id: e.target.value })} maxLength="32" /></label><label>Correo<input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label><label>Teléfono<input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} maxLength="40" /></label><button className="primary" disabled={saving}>{saving ? 'Guardando…' : 'Guardar socio'}</button></form></section>
}

function ProductMaster({ products, wms, onCreated, canWrite }) {
  const [form, setForm] = React.useState({ sku: '', name: '', unit: 'unidad', sale_price: '', purchase_cost: '', initial_stock: '0' }), [saving, setSaving] = React.useState(false)
  const [importRows, setImportRows] = React.useState([]), [importFile, setImportFile] = React.useState(''), [importError, setImportError] = React.useState(''), [importing, setImporting] = React.useState(false)
  async function submit(event) { event.preventDefault(); setSaving(true); try { await api('/api/erp/products', { method: 'POST', body: JSON.stringify({ ...form, sale_price: Number(form.sale_price), purchase_cost: Number(form.purchase_cost), initial_stock: Number(form.initial_stock) }) }); setForm({ sku: '', name: '', unit: 'unidad', sale_price: '', purchase_cost: '', initial_stock: '0' }); await onCreated('Ficha guardada en ERP y WMS. Si el SKU ya existía, su saldo se conservó.') } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) } }
  async function selectImport(event) {
    const file = event.target.files?.[0]
    setImportRows([]); setImportError(''); setImportFile(file?.name || '')
    if (!file) return
    if (file.size > 1_000_000) { setImportError('El archivo supera el límite de 1 MB.'); return }
    try { setImportRows(parseInventoryCsv(await file.text())) } catch (reason) { setImportError(reason.message) }
  }
  async function submitImport() {
    if (!importRows.length) return
    setImporting(true); setImportError('')
    try {
      const result = await api('/api/erp/products/import', { method: 'POST', body: JSON.stringify({ products: importRows }) })
      setImportRows([]); setImportFile('')
      const picker = document.getElementById('erp-catalog-file'); if (picker) picker.value = ''
      await onCreated(`Carga lista: ${result.created} SKU nuevos y ${result.updated} actualizados. Los saldos existentes se conservaron.`)
    } catch (reason) { setImportError(reason.message) }
    finally { setImporting(false) }
  }
  return <>
    <section className="card">
      <div className="card-title"><div><p className="eyebrow">Catálogo comercial · Azure WMS</p><h3>Productos</h3></div><Badge tone={wms?.status === 'connected' ? 'success' : 'warning'}>{wms?.status || 'sin dato'}</Badge></div>
      {wms?.note && <p className="form-hint">{wms.note}</p>}
      <div className="table-wrap"><table><thead><tr><th>SKU</th><th>Producto</th><th>Venta</th><th>Costo</th><th>Saldo Azure</th></tr></thead><tbody>{products.map(item => <tr key={item.sku}><td className="mono">{item.sku}</td><td>{item.name}</td><td>{pen(item.sale_price)}</td><td>{pen(item.purchase_cost)}</td><td>{item.on_hand ?? 'No disponible'}</td></tr>)}</tbody></table></div>
    </section>
    {canWrite && <>
      <section className="card catalog-import">
        <div>
          <p className="eyebrow">Carga masiva · datos sintéticos</p>
          <h3>Importar catálogo desde Excel</h3>
          <p>Abre y edita la plantilla Excel; luego guárdala como CSV UTF-8 para importarla. Se valida el archivo completo antes de sincronizar.</p>
          <p className="form-hint">El saldo inicial solo se usa para SKU nuevos. Actualizar un SKU nunca reemplaza su saldo actual.</p>
          <div className="catalog-template-actions">
            <a className="secondary catalog-template" href="/templates/plantilla_catalogo_sintetico.xlsx" download>Descargar plantilla Excel</a>
            <a className="secondary catalog-template" href="/templates/inventario_sintetico.csv" download>Descargar CSV</a>
          </div>
        </div>
        <div className="catalog-upload">
          <label htmlFor="erp-catalog-file">Archivo CSV UTF-8<input id="erp-catalog-file" type="file" accept=".csv,text/csv" onChange={selectImport} /></label>
          {importFile && !importError && <p className="form-hint">{importFile} · {importRows.length} productos validados</p>}
          {importError && <p className="alert error" role="alert">{importError}</p>}
          {importRows.length > 0 && <>
            <div className="catalog-preview"><strong>Vista previa</strong><span>{importRows.slice(0, 5).map(item => `${item.sku} · ${item.initial_stock}`).join('  |  ')}{importRows.length > 5 ? ` · y ${importRows.length - 5} más` : ''}</span></div>
            <button className="primary" type="button" disabled={importing} onClick={submitImport}>{importing ? 'Sincronizando…' : `Importar ${importRows.length} productos`}</button>
          </>}
        </div>
      </section>
      <section className="card form-card">
        <p className="eyebrow">Ficha comercial</p><h3>Alta / actualización de SKU</h3>
        <form onSubmit={submit}>
          <label>SKU<input value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value.toUpperCase() })} required maxLength="40" placeholder="SKU-..." /></label>
          <label>Nombre<input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required maxLength="180" /></label>
          <label>Unidad<input value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} required maxLength="32" /></label>
          <div className="erp-two-fields"><label>Precio venta (S/)<input type="number" min="0" step="0.01" value={form.sale_price} onChange={e => setForm({ ...form, sale_price: e.target.value })} required /></label><label>Costo compra (S/)<input type="number" min="0" step="0.01" value={form.purchase_cost} onChange={e => setForm({ ...form, purchase_cost: e.target.value })} required /></label></div>
          <label>Saldo inicial si el SKU es nuevo<input type="number" min="0" max="1000000" step="1" value={form.initial_stock} onChange={e => setForm({ ...form, initial_stock: e.target.value })} required /></label>
          <p className="form-hint">El saldo sintético se registra en Azure WMS. Si el SKU ya existe, el saldo actual no cambia.</p>
          <button className="primary" disabled={saving}>{saving ? 'Guardando…' : 'Guardar producto'}</button>
        </form>
      </section>
    </>}
  </>
}

function FinancePanel({ documents, partners, summary, canWrite, onCreated }) {
  const [form, setForm] = React.useState({ description: '', partner_id: '', reference: '', amount: '', due_date: '' }), [saving, setSaving] = React.useState(false)
  async function submit(event) { event.preventDefault(); setSaving(true); try { await api('/api/erp/finance/expenses', { method: 'POST', body: JSON.stringify({ ...form, partner_id: form.partner_id ? Number(form.partner_id) : null, amount: Number(form.amount) }) }); setForm({ description: '', partner_id: '', reference: '', amount: '', due_date: '' }); await onCreated('Cuenta por pagar registrada.') } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) } }
  async function settle(id) { try { await api(`/api/erp/finance/documents/${id}/settle`, { method: 'POST' }); await onCreated('Documento marcado como pagado/cobrado.') } catch (reason) { await onCreated(reason.message) } }
  return <><div className="metric-grid erp-metrics"><article><small>Cuentas por cobrar abiertas</small><strong>{pen(summary?.metrics?.open_receivables)}</strong><span>Ventas completadas por el WMS</span></article><article><small>Cuentas por pagar abiertas</small><strong>{pen(summary?.metrics?.open_payables)}</strong><span>Compras recibidas y gastos</span></article></div><div className="content-grid erp-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Cuentas internas</p><h3>Cobros y pagos</h3></div><Badge>{documents.length}</Badge></div>{documents.length ? <div className="table-wrap"><table><thead><tr><th>Referencia</th><th>Tipo</th><th>Socio</th><th>Concepto</th><th>Vencimiento</th><th>Estado</th><th>Monto</th><th /></tr></thead><tbody>{documents.map(doc => <tr key={doc.id}><td>{doc.reference}</td><td>{doc.kind === 'receivable' ? 'Por cobrar' : 'Por pagar'}</td><td>{doc.partner_name || '—'}</td><td>{doc.description}</td><td>{doc.due_date || '—'}</td><td><Badge tone={doc.status === 'paid' ? 'success' : 'warning'}>{doc.status}</Badge></td><td>{pen(doc.amount)}</td><td>{canWrite && doc.status === 'open' && <button className="secondary" type="button" onClick={() => settle(doc.id)}>{doc.kind === 'receivable' ? 'Registrar cobro' : 'Registrar pago'}</button>}</td></tr>)}</tbody></table></div> : <Empty text="No hay documentos financieros todavía." />}<p className="form-hint">Registro operativo básico; no es contabilidad de partida doble ni comprobante tributario.</p></section>{canWrite && <section className="card form-card"><p className="eyebrow">Gasto / cuenta por pagar</p><h3>Registrar gasto</h3><form onSubmit={submit}><label>Concepto<input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} maxLength="180" required /></label><label>Proveedor<select value={form.partner_id} onChange={e => setForm({ ...form, partner_id: e.target.value })}><option value="">Sin proveedor asociado</option>{partners.filter(p => p.kind === 'supplier' || p.kind === 'both').map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Referencia<input value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })} maxLength="80" placeholder="Generada si se deja vacía" /></label><label>Monto (S/)<input type="number" min="0.01" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} required /></label><label>Vencimiento<input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} /></label><button className="primary" disabled={saving}>{saving ? 'Guardando…' : 'Registrar gasto'}</button></form></section>}</div></>
}

function ErpAccess({ users, onCreated }) {
  const roleKeys = Object.keys(erpRoleLabels)
  async function toggle(user, role) {
    const next = user.erp_roles.includes(role) ? user.erp_roles.filter(item => item !== role) : [...user.erp_roles, role]
    try { await api(`/api/erp/users/${user.id}/roles`, { method: 'PUT', body: JSON.stringify({ roles: next }) }); await onCreated(`Permisos ERP actualizados para ${user.username}.`) } catch (reason) { await onCreated(reason.message) }
  }
  return <section className="card"><div className="card-title"><div><p className="eyebrow">Control de acceso</p><h3>Roles ERP por usuario</h3></div><Badge>{users.length} cuentas internas</Badge></div><p className="form-hint">Los permisos del ERP son independientes del rol de acceso al portal. El administrador global siempre conserva el acceso ERP.</p><div className="table-wrap"><table><thead><tr><th>Cuenta</th><th>Rol portal</th>{roleKeys.map(role => <th key={role}>{erpRoleLabels[role]}</th>)}</tr></thead><tbody>{users.map(user => <tr key={user.id}><td><b>{user.username}</b><small>{user.company}</small></td><td>{user.role}</td>{roleKeys.map(role => <td key={role}><input className="role-check" aria-label={`${erpRoleLabels[role]} para ${user.username}`} type="checkbox" checked={user.erp_roles.includes(role)} disabled={user.role === 'admin' && role === 'erp_admin'} onChange={() => toggle(user, role)} /></td>)}</tr>)}</tbody></table></div></section>
}

function InternalMail({ user, onNotify }) {
  const [folder, setFolder] = React.useState('inbox'), [messages, setMessages] = React.useState([]), [recipients, setRecipients] = React.useState([]), [mailStatus, setMailStatus] = React.useState(null), [selected, setSelected] = React.useState(null), [compose, setCompose] = React.useState(false), [form, setForm] = React.useState({ recipient_id: '', subject: '', body: '' }), [loading, setLoading] = React.useState(false)
  const refresh = React.useCallback(async (currentFolder = folder) => {
    setLoading(true)
    try { const [list, people, status] = await Promise.all([api(`/api/erp/mail?folder=${currentFolder}`), api('/api/erp/mail/users'), api('/api/erp/mail/status')]); setMessages(list); setRecipients(people); setMailStatus(status) }
    catch (reason) { onNotify(`No se pudo cargar el correo interno: ${reason.message}`) }
    finally { setLoading(false) }
  }, [folder, onNotify])
  React.useEffect(() => { refresh(folder) }, [folder, refresh])
  async function openMessage(message) { setSelected(message); setCompose(false); if (folder === 'inbox' && !message.read_at) { try { await api(`/api/erp/mail/${message.id}/read`, { method: 'POST' }); await refresh('inbox') } catch (reason) { onNotify(reason.message) } } }
  async function send(event) { event.preventDefault(); setLoading(true); try { const result = await api('/api/erp/mail', { method: 'POST', body: JSON.stringify({ ...form, recipient_id: Number(form.recipient_id) }) }); setForm({ recipient_id: '', subject: '', body: '' }); setCompose(false); setFolder('sent'); onNotify(result.smtp_status === 'accepted_by_smtp' ? 'Mensaje guardado; el relay SMTP aceptó la copia.' : result.smtp_status === 'smtp_failed' ? 'Mensaje guardado en el portal; SMTP no aceptó la copia.' : 'Mensaje guardado en el buzón interno.') } catch (reason) { onNotify(reason.message) } finally { setLoading(false) } }
  async function testSmtp() { setLoading(true); try { const result = await api('/api/erp/mail/smtp-test', { method: 'POST' }); onNotify(`Prueba aceptada por SMTP (${result.message_id}). ${['localhost', '127.0.0.1'].includes(window.location.hostname) ? 'Revisa la bandeja local en localhost:8025.' : ''}`) } catch (reason) { onNotify(`Prueba SMTP: ${reason.message}`) } finally { setLoading(false) } }
  const localPreview = ['localhost', '127.0.0.1'].includes(window.location.hostname)
  const deliveryText = status => status === 'accepted_by_smtp' ? 'SMTP aceptó copia' : status === 'smtp_failed' ? 'SMTP no disponible' : status === 'recipient_address_missing' ? 'Cuenta sin dirección SMTP' : 'Solo buzón del portal'
  return <section className="mail-page"><div className="mail-intro"><div><p className="eyebrow">Comunicación de la empresa</p><h2>Correo interno</h2><p>La bandeja del portal guarda el mensaje; un relay SMTP opcional puede enviar una copia a la cuenta interna.</p></div><div className="mail-toolbar"><span className={`mail-transport ${mailStatus?.smtp_configured ? 'configured' : ''}`}>{mailStatus?.smtp_configured ? `SMTP configurado · ${mailStatus.security}` : 'Buzón interno activo'}</span><div className="mail-actions">{user.role === 'admin' && mailStatus?.smtp_configured && <button className="secondary" type="button" onClick={testSmtp} disabled={loading}>Probar SMTP</button>}{localPreview && mailStatus?.smtp_configured && <a className="secondary" href="http://localhost:8025" target="_blank" rel="noreferrer">Ver correo de prueba</a>}<button className="primary" type="button" onClick={() => { setCompose(true); setSelected(null) }}>Redactar mensaje</button></div></div></div><div className="mail-layout"><aside className="mail-folders"><button className={folder === 'inbox' ? 'active' : ''} onClick={() => { setCompose(false); setFolder('inbox'); setSelected(null) }}>Bandeja de entrada</button><button className={folder === 'sent' ? 'active' : ''} onClick={() => { setCompose(false); setFolder('sent'); setSelected(null) }}>Enviados</button></aside><div className="mail-list">{loading && <p className="form-hint">Actualizando…</p>}{messages.length ? messages.map(message => <button className={`mail-row ${selected?.id === message.id ? 'selected' : ''} ${message.unread ? 'unread' : ''}`} type="button" key={message.id} onClick={() => openMessage(message)}><strong>{folder === 'inbox' ? message.sender : message.recipient}</strong><span>{message.subject}</span><small>{new Date(message.created_at).toLocaleString('es-PE')} · {deliveryText(message.smtp_status)}</small></button>) : !loading && <Empty text={folder === 'inbox' ? 'Tu bandeja está vacía.' : 'Aún no has enviado mensajes.'} />}</div><article className="mail-reading">{compose ? <form onSubmit={send}><p className="eyebrow">Nuevo mensaje interno</p><label>Para<select value={form.recipient_id} onChange={e => setForm({ ...form, recipient_id: e.target.value })} required><option value="">Selecciona una cuenta interna</option>{recipients.filter(item => item.id !== user.id).map(item => <option key={item.id} value={item.id}>{item.username}</option>)}</select></label><label>Asunto<input value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} maxLength="160" required /></label><label>Mensaje<textarea value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} rows="8" maxLength="20000" required /></label><button className="primary" disabled={loading}>{loading ? 'Enviando…' : 'Enviar mensaje'}</button></form> : selected ? <><p className="eyebrow">{folder === 'inbox' ? `De ${selected.sender}` : `Para ${selected.recipient}`}</p><h3>{selected.subject}</h3><small>{new Date(selected.created_at).toLocaleString('es-PE')} · {deliveryText(selected.smtp_status)}</small><p className="mail-body">{selected.body}</p></> : <Empty text="Selecciona un mensaje o redacta uno nuevo." />}</article></div><p className="form-hint">SMTP confirma que el relay aceptó el mensaje; no garantiza entrega final. El correo público requiere dominio verificado y buzones reales.</p></section>
}

function Portal({ user, onLogout, onSessionExpired, onPasswordChanged }) {
  const [view, setView] = React.useState('dashboard'), [health, setHealth] = React.useState({ status: 'consultando' }), [dashboard, setDashboard] = React.useState(null), [orders, setOrders] = React.useState([]), [outbox, setOutbox] = React.useState([]), [azure, setAzure] = React.useState(null), [users, setUsers] = React.useState([]), [companies, setCompanies] = React.useState([]), [audit, setAudit] = React.useState([]), [erpAccess, setErpAccess] = React.useState({ permissions: [] }), [notice, setNotice] = React.useState(''), [lastRefresh, setLastRefresh] = React.useState('—')
  const isOps = opsRoles.has(user.role), isAdmin = user.role === 'admin', canWrite = writeRoles.has(user.role)
  const isInternal = internalRoles.has(user.role)
  const canAccessErp = hasErpAccess(erpAccess.permissions)
  const handleNotify = React.useCallback(message => setNotice(message), [])
  const refresh = React.useCallback(async () => {
    setNotice('')
    const healthRequest = fetch('/health', { credentials: 'same-origin', cache: 'no-store' }).then(async response => {
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw Object.assign(new Error(body.error || `HTTP ${response.status}`), { status: response.status })
      return body
    })
    const coreSpecs = [['dashboard', '/api/dashboard'], ['orders', '/api/orders']]
    const coreResults = await Promise.allSettled([
      healthRequest,
      ...coreSpecs.map(([, path]) => api(path))
    ])
    const [healthResult, ...dataResults] = coreResults
    const errors = []

    if (healthResult.status === 'fulfilled') setHealth(healthResult.value)
    else {
      setHealth({ status: 'unavailable', database: 'sin verificar' })
      errors.push(`salud: ${healthResult.reason.message}`)
    }

    dataResults.forEach((result, index) => {
      const [key] = coreSpecs[index]
      if (result.status === 'fulfilled') {
        if (key === 'dashboard') setDashboard(result.value)
        if (key === 'orders') setOrders(result.value)
      } else {
        errors.push(`${key === 'dashboard' ? 'resumen' : 'pedidos'}: ${result.reason.message}`)
      }
    })

    const optionalSpecs = []
    if (isOps) optionalSpecs.push(['outbox', '/api/outbox'], ['azure', '/api/multicloud'])
    if (isAdmin) optionalSpecs.push(['users', '/api/admin/users'], ['companies', '/api/admin/companies'])
    if (['admin', 'operations', 'auditor'].includes(user.role)) optionalSpecs.push(['audit', '/api/audit'])
    if (isInternal) optionalSpecs.push(['erpAccess', '/api/erp/access'])
    const optionalResults = await Promise.allSettled(optionalSpecs.map(([, path]) => api(path)))
    optionalResults.forEach((result, index) => {
      const [key] = optionalSpecs[index]
      if (result.status === 'fulfilled') {
        if (key === 'outbox') setOutbox(result.value)
        if (key === 'azure') setAzure(result.value)
        if (key === 'users') setUsers(result.value)
        if (key === 'companies') setCompanies(result.value)
        if (key === 'audit') setAudit(result.value)
        if (key === 'erpAccess') setErpAccess(result.value)
        return
      }
      const reason = result.reason
      if (key === 'azure') setAzure({ status: 'unavailable', error: reason.message })
      if (key === 'outbox') setOutbox([])
      if (key === 'users') setUsers([])
      if (key === 'companies') setCompanies([])
      if (key === 'audit') setAudit([])
      if (key === 'erpAccess') setErpAccess({ permissions: [] })
      errors.push(`${key}: ${reason.message}`)
    })

    const unauthorized = [...dataResults, ...optionalResults]
      .find(result => result.status === 'rejected' && result.reason.status === 401)
    if (unauthorized) {
      const session = await api('/api/auth/session').catch(() => ({ authenticated: false }))
      if (!session.authenticated) {
        onSessionExpired()
        return
      }
    }

    setLastRefresh(new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    if (errors.length) setNotice(`Algunos datos no se pudieron cargar (${errors.join(' · ')}). Revisa la sesión y vuelve a actualizar.`)
  }, [isAdmin, isInternal, isOps, onSessionExpired, user.role])
  React.useEffect(() => { refresh().catch(reason => setNotice(reason.message)) }, [refresh])
  async function signOut() { await api('/api/auth/logout', { method: 'POST' }); csrfToken = ''; onLogout() }
  async function retry(eventId) { try { const result = await api(`/api/outbox/${eventId}/retry`, { method: 'POST' }); setNotice(result.status === 'delivered' ? 'Evento entregado al WMS Azure.' : 'El evento continúa pendiente; quedó registrado para reintento.'); await refresh() } catch (reason) { setNotice(reason.message) } }
  const navigation = createPortalNavigation(user.role)
  const title = view === 'dashboard' ? 'Resumen operativo' : navigation.find(item => item[0] === view)?.[1]
  return <div className="app-shell"><aside className="sidebar"><div className="logo"><span>T</span><div><strong>Tangamandapio</strong><small>Portal B2B</small></div></div><div className="identity"><span className="avatar">{user.username.slice(0, 1).toUpperCase()}</span><div><strong>{user.username}</strong><small>{roleLabels[user.role]} · {user.company}</small></div></div><nav aria-label="Secciones del portal">{navigation.map(([key, label]) => key === 'administration' ? <a className="portal-admin-link" href="/administracion" key={key}><span aria-hidden="true">⚙</span>{label}</a> : <button type="button" key={key} className={view === key ? 'active' : ''} aria-current={view === key ? 'page' : undefined} onClick={() => setView(key)}>{label}</button>)}</nav><div className="sidebar-foot"><button onClick={refresh}>Actualizar datos</button><button onClick={signOut}>Cerrar sesión</button></div></aside><main className="workspace"><header className="topbar"><div><p className="eyebrow">Centro de operaciones</p><h1>{title}</h1></div><div className="topbar-meta"><Badge tone={health.status === 'ok' ? 'success' : 'danger'}>AWS: {health.status || 'sin dato'}</Badge><span>Actualizado {lastRefresh}</span></div></header>{notice && <p className="alert">{notice}</p>}{view === 'dashboard' && <Dashboard dashboard={dashboard} health={health} azure={azure} isOps={isOps} />}{view === 'orders' && <Orders orders={orders} canWrite={canWrite} onCreated={async message => { setNotice(message); await refresh() }} />}{view === 'operations' && <Operations outbox={outbox} azure={azure} onRetry={retry} />}{view === 'users' && <Users users={users} companies={companies} actorId={user.id} onCreated={async message => { setNotice(message); await refresh() }} />}{view === 'companies' && <Companies companies={companies} onCreated={async message => { setNotice(message); await refresh() }} />}{view === 'audit' && <Audit entries={audit} />}{view === 'erp' && (canAccessErp ? <Erp user={user} access={erpAccess} onNotify={handleNotify} /> : <section className="card"><p className="eyebrow">Control de acceso</p><h2>Sin permisos ERP</h2><p>Tu cuenta puede entrar al portal, pero no tiene permisos ERP asignados. Solicita la asignación al administrador.</p></section>)}{view === 'account' && <PasswordChange user={user} onComplete={onPasswordChanged} />}</main></div>
}

function App() {
  const [session, setSession] = React.useState(null), [loading, setLoading] = React.useState(true), [loginNotice, setLoginNotice] = React.useState('')
  const restore = React.useCallback(async () => { try { const data = await api('/api/auth/session'); setSession(data.authenticated ? data.user : null); setLoginNotice('') } finally { setLoading(false) } }, [])
  const expireSession = React.useCallback(() => { csrfToken = ''; setSession(null) }, [])
  const afterPasswordChange = React.useCallback(() => { csrfToken = ''; setLoginNotice('Contraseña actualizada. Inicia sesión con tu nueva clave.'); setSession(null) }, [])
  React.useEffect(() => { restore() }, [restore])
  if (loading) return <main className="loading">Cargando portal protegido…</main>
  if (session?.must_change_password) return <PasswordChange user={session} forced onComplete={afterPasswordChange} />
  return session ? <Portal user={session} onLogout={expireSession} onSessionExpired={expireSession} onPasswordChanged={afterPasswordChange} /> : <Login onAuthenticated={restore} notice={loginNotice} />
}
createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
