import React from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const money = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })
const roleLabels = { customer: 'Cliente B2B', sales: 'Comercial', warehouse: 'Operador WMS', operations: 'Operaciones TI', admin: 'Administrador', auditor: 'Auditor' }
const opsRoles = new Set(['operations', 'admin', 'auditor', 'warehouse'])
const writeRoles = new Set(['customer', 'sales', 'admin'])

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', cache: 'no-store', headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) }, ...options })
  const body = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) throw Object.assign(new Error(body?.error || `HTTP ${response.status}`), { status: response.status, code: body?.error })
  return body
}
function Badge({ children, tone = 'neutral' }) { return <span className={`badge ${tone}`}>{children}</span> }
function Empty({ text }) { return <p className="empty">{text}</p> }

function Login({ onAuthenticated }) {
  const [username, setUsername] = React.useState(''), [password, setPassword] = React.useState(''), [error, setError] = React.useState(''), [loading, setLoading] = React.useState(false)
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError('')
    try { await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); await onAuthenticated() }
    catch (reason) { setError(reason.message === 'invalid_credentials' ? 'Credenciales inválidas o cuenta deshabilitada.' : reason.message) }
    finally { setLoading(false) }
  }
  return <main className="auth-shell"><section className="brand-pane"><p className="eyebrow">Tangamandapio S.A.C. · Portal B2B</p><h1>Operación comercial con trazabilidad multicloud.</h1><p>Pedidos en AWS, integración durable hacia el WMS de Azure y controles de acceso por rol.</p><div className="security-list"><span>Acceso autenticado</span><span>Roles de mínimo privilegio</span><span>Auditoría de operaciones</span></div></section><section className="login-card"><p className="eyebrow">Acceso corporativo</p><h2>Iniciar sesión</h2><form onSubmit={submit}><label>Usuario<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="usuario@empresa" required /></label><label>Contraseña<input autoComplete="current-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label><button className="primary" disabled={loading}>{loading ? 'Verificando…' : 'Ingresar al portal'}</button></form>{error && <p className="alert error" role="alert">{error}</p>}<p className="login-note">Las cuentas son administradas por Tangamandapio. No existe registro público.</p></section></main>
}

function Dashboard({ dashboard, health, azure, isOps }) { return <><section className="metric-grid"><article><small>Pedidos visibles</small><strong>{dashboard?.orders ?? '—'}</strong><span>Según permisos de tu rol</span></article><article><small>Eventos entregados</small><strong>{dashboard?.outbox?.delivered ?? '—'}</strong><span>Confirmados por el flujo WMS</span></article><article><small>Eventos pendientes</small><strong>{dashboard?.outbox?.pending ?? '—'}</strong><span>Outbox con reintento seguro</span></article><article><small>Base de datos AWS</small><strong>{health.database || '—'}</strong><span>Estado de dependencia</span></article></section><section className="flow-card"><div><p className="eyebrow">Arquitectura en ejecución</p><h2>Pedido → transacción durable → WMS</h2><p>El pedido se confirma primero en AWS. Después, el evento se entrega al WMS de Azure sin perder la transacción si el servicio remoto no estuviera disponible.</p></div><div className="flow"><span>AWS<br/><b>Portal y RDS</b></span><i>→</i><span>Outbox<br/><b>Evento auditable</b></span><i>→</i><span>Azure<br/><b>Function · Blob · Queue</b></span></div></section>{isOps && <section className="service-card"><div><p className="eyebrow">Integración Azure</p><h2>{azure?.status === 'connected' ? 'Servicio WMS conectado' : 'Estado de WMS pendiente'}</h2><p>{azure?.status === 'connected' ? 'El endpoint de operaciones responde y la autenticación de servicio está disponible.' : 'Consulta el módulo de Integración WMS para revisar el estado.'}</p></div><Badge tone={azure?.status === 'connected' ? 'success' : 'warning'}>{azure?.status || 'sin dato'}</Badge></section>}</> }

function Orders({ orders, canWrite, onCreated }) {
  const [customer, setCustomer] = React.useState(''), [reference, setReference] = React.useState(''), [total, setTotal] = React.useState(''), [sending, setSending] = React.useState(false)
  async function submit(event) { event.preventDefault(); setSending(true); try { const created = await api('/api/orders', { method: 'POST', body: JSON.stringify({ customer, reference, total: Number(total) }) }); setCustomer(''); setReference(''); setTotal(''); await onCreated(`Pedido #${created.id} registrado y enviado al flujo de cumplimiento.`) } catch (reason) { await onCreated(reason.message) } finally { setSending(false) } }
  return <div className="content-grid"><section className="card orders-card"><div className="card-title"><div><p className="eyebrow">Información comercial</p><h2>Pedidos</h2></div><Badge>{orders.length} visibles</Badge></div>{orders.length ? <div className="table-wrap"><table><thead><tr><th>ID</th><th>Cliente</th><th>Referencia</th><th>Empresa</th><th>Estado</th><th>Total</th></tr></thead><tbody>{orders.map(order => <tr key={order.id}><td>#{order.id}</td><td><b>{order.customer}</b><small>{new Date(order.created_at).toLocaleString('es-PE')}</small></td><td>{order.reference || '—'}</td><td>{order.company || 'Legado'}</td><td><Badge tone="warning">{order.status || 'creado'}</Badge></td><td>{money.format(order.total)}</td></tr>)}</tbody></table></div> : <Empty text="Todavía no hay pedidos visibles para esta cuenta." />}</section>{canWrite && <section className="card form-card"><p className="eyebrow">Operación comercial</p><h2>Nuevo pedido</h2><form onSubmit={submit}><label>Cliente<input value={customer} onChange={e => setCustomer(e.target.value)} required maxLength="120" placeholder="Razón social o contacto" /></label><label>Referencia<input value={reference} onChange={e => setReference(e.target.value)} maxLength="80" placeholder="OC o referencia interna" /></label><label>Total (S/)<input value={total} onChange={e => setTotal(e.target.value)} required type="number" min="0" step="0.01" placeholder="0.00" /></label><button className="primary" disabled={sending}>{sending ? 'Confirmando…' : 'Crear pedido'}</button></form></section>}</div>
}

function Operations({ outbox, azure, onRetry }) { return <section className="card"><div className="card-title"><div><p className="eyebrow">Confiabilidad de integración</p><h2>Eventos hacia WMS Azure</h2></div><Badge tone={azure?.status === 'connected' ? 'success' : 'warning'}>{azure?.status || 'sin dato'}</Badge></div><p className="muted">Un pedido nunca se revierte por una falla remota: el evento queda en outbox, se audita y solo Operaciones puede solicitar un reintento.</p>{outbox.length ? <div className="table-wrap"><table><thead><tr><th>Evento</th><th>Pedido</th><th>Estado</th><th>Intentos</th><th>Acción</th></tr></thead><tbody>{outbox.map(event => <tr key={event.event_id}><td className="mono">{event.event_id}</td><td>#{event.order_id}</td><td><Badge tone={event.status === 'delivered' ? 'success' : 'warning'}>{event.status}</Badge></td><td>{event.attempts}</td><td>{event.status !== 'delivered' && <button className="secondary" onClick={() => onRetry(event.event_id)}>Reintentar</button>}</td></tr>)}</tbody></table></div> : <Empty text="No hay eventos pendientes o entregados todavía." />}</section> }

function Users({ users, companies, onCreated }) {
  const [form, setForm] = React.useState({ username: '', password: '', role: 'customer', company_id: '' })
  const [saving, setSaving] = React.useState(false)
  async function submit(event) {
    event.preventDefault(); setSaving(true)
    try {
      await api('/api/admin/users', { method: 'POST', body: JSON.stringify({ ...form, company_id: Number(form.company_id) }) })
      setForm({ username: '', password: '', role: 'customer', company_id: '' })
      await onCreated('Usuario creado con el rol y la empresa asignados.')
    } catch (reason) { await onCreated(reason.message) } finally { setSaving(false) }
  }
  return <div className="content-grid"><section className="card"><div className="card-title"><div><p className="eyebrow">Gobierno de identidad</p><h2>Usuarios y roles</h2></div><Badge>{users.length} cuentas</Badge></div><div className="table-wrap"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Empresa</th><th>Estado</th></tr></thead><tbody>{users.map(item => <tr key={item.id}><td>{item.username}</td><td>{roleLabels[item.role]}</td><td>{item.company}</td><td><Badge tone={item.active ? 'success' : 'danger'}>{item.active ? 'activo' : 'bloqueado'}</Badge></td></tr>)}</tbody></table></div></section><section className="card form-card"><p className="eyebrow">Provisionamiento</p><h2>Nueva cuenta</h2><form onSubmit={submit}><label>Usuario<input value={form.username} onChange={event => setForm({ ...form, username: event.target.value })} required /></label><label>Contraseña temporal<input type="password" value={form.password} minLength="12" onChange={event => setForm({ ...form, password: event.target.value })} required /></label><label>Empresa<select value={form.company_id} onChange={event => setForm({ ...form, company_id: event.target.value })} required><option value="">Selecciona una empresa</option>{companies.map(company => <option value={company.id} key={company.id}>{company.name}</option>)}</select></label><label>Rol<select value={form.role} onChange={event => setForm({ ...form, role: event.target.value })}>{Object.entries(roleLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label><button className="primary" disabled={saving}>{saving ? 'Creando…' : 'Crear cuenta'}</button></form></section></div>
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

function Portal({ user, onLogout, onSessionExpired }) {
  const [view, setView] = React.useState('dashboard'), [health, setHealth] = React.useState({ status: 'consultando' }), [dashboard, setDashboard] = React.useState(null), [orders, setOrders] = React.useState([]), [outbox, setOutbox] = React.useState([]), [azure, setAzure] = React.useState(null), [users, setUsers] = React.useState([]), [companies, setCompanies] = React.useState([]), [audit, setAudit] = React.useState([]), [notice, setNotice] = React.useState(''), [lastRefresh, setLastRefresh] = React.useState('—')
  const isOps = opsRoles.has(user.role), isAdmin = user.role === 'admin', canWrite = writeRoles.has(user.role)
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
    const optionalResults = await Promise.allSettled(optionalSpecs.map(([, path]) => api(path)))
    optionalResults.forEach((result, index) => {
      const [key] = optionalSpecs[index]
      if (result.status === 'fulfilled') {
        if (key === 'outbox') setOutbox(result.value)
        if (key === 'azure') setAzure(result.value)
        if (key === 'users') setUsers(result.value)
        if (key === 'companies') setCompanies(result.value)
        if (key === 'audit') setAudit(result.value)
        return
      }
      const reason = result.reason
      if (key === 'azure') setAzure({ status: 'unavailable', error: reason.message })
      if (key === 'outbox') setOutbox([])
      if (key === 'users') setUsers([])
      if (key === 'companies') setCompanies([])
      if (key === 'audit') setAudit([])
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
  }, [isAdmin, isOps, onSessionExpired, user.role])
  React.useEffect(() => { refresh().catch(reason => setNotice(reason.message)) }, [refresh])
  async function signOut() { await api('/api/auth/logout', { method: 'POST' }); onLogout() }
  async function retry(eventId) { try { const result = await api(`/api/outbox/${eventId}/retry`, { method: 'POST' }); setNotice(result.status === 'delivered' ? 'Evento entregado al WMS Azure.' : 'El evento continúa pendiente; quedó registrado para reintento.'); await refresh() } catch (reason) { setNotice(reason.message) } }
  const navigation = [['dashboard', 'Resumen'], ['orders', 'Pedidos'], ...(isOps ? [['operations', 'Integración WMS']] : []), ...(isAdmin ? [['users', 'Usuarios'], ['companies', 'Empresas']] : []), ...(['admin', 'operations', 'auditor'].includes(user.role) ? [['audit', 'Auditoría']] : [])]
  return <div className="app-shell"><aside className="sidebar"><div className="logo"><span>T</span><div><strong>Tangamandapio</strong><small>Portal B2B</small></div></div><div className="identity"><span className="avatar">{user.username.slice(0, 1).toUpperCase()}</span><div><strong>{user.username}</strong><small>{roleLabels[user.role]} · {user.company}</small></div></div><nav>{navigation.map(([key, label]) => <button key={key} className={view === key ? 'active' : ''} onClick={() => setView(key)}>{label}</button>)}</nav><div className="sidebar-foot"><button onClick={refresh}>Actualizar datos</button><button onClick={signOut}>Cerrar sesión</button></div></aside><main className="workspace"><header className="topbar"><div><p className="eyebrow">Centro de operaciones</p><h1>{view === 'dashboard' ? 'Resumen operativo' : navigation.find(item => item[0] === view)?.[1]}</h1></div><div className="topbar-meta"><Badge tone={health.status === 'ok' ? 'success' : 'danger'}>AWS: {health.status || 'sin dato'}</Badge><span>Actualizado {lastRefresh}</span></div></header>{notice && <p className="alert">{notice}</p>}{view === 'dashboard' && <Dashboard dashboard={dashboard} health={health} azure={azure} isOps={isOps} />}{view === 'orders' && <Orders orders={orders} canWrite={canWrite} onCreated={async message => { setNotice(message); await refresh() }} />}{view === 'operations' && <Operations outbox={outbox} azure={azure} onRetry={retry} />}{view === 'users' && <Users users={users} companies={companies} onCreated={async message => { setNotice(message); await refresh() }} />}{view === 'companies' && <Companies companies={companies} onCreated={async message => { setNotice(message); await refresh() }} />}{view === 'audit' && <Audit entries={audit} />}</main></div>
}

function App() { const [session, setSession] = React.useState(null), [loading, setLoading] = React.useState(true); const restore = React.useCallback(async () => { try { const data = await api('/api/auth/session'); setSession(data.authenticated ? data.user : null) } finally { setLoading(false) } }, []); const expireSession = React.useCallback(() => setSession(null), []); React.useEffect(() => { restore() }, [restore]); if (loading) return <main className="loading">Cargando portal protegido…</main>; return session ? <Portal user={session} onLogout={expireSession} onSessionExpired={expireSession} /> : <Login onAuthenticated={restore} /> }
createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
