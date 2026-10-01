import React, { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const currency = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' })

function App() {
  const [orders, setOrders] = React.useState([])
  const [health, setHealth] = React.useState({ status: 'consultando' })
  const [customer, setCustomer] = React.useState('')
  const [total, setTotal] = React.useState('')
  const [message, setMessage] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)

  const load = React.useCallback(async () => {
    const [healthResponse, ordersResponse] = await Promise.all([
      fetch('/health'), fetch('/api/orders')
    ])
    setHealth(await healthResponse.json())
    setOrders(await ordersResponse.json())
  }, [])

  React.useEffect(() => { load().catch(() => setHealth({ status: 'no disponible' })) }, [load])

  async function submit(event) {
    event.preventDefault()
    setSubmitting(true)
    setMessage('')
    try {
      const response = await fetch('/api/orders', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer, total: Number(total) })
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.error || 'No se pudo registrar el pedido')
      setCustomer('')
      setTotal('')
      setMessage(`Pedido #${body.id} registrado correctamente`)
      await load()
    } catch (error) {
      setMessage(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  return <main>
    <header>
      <p className="eyebrow">Tangamandapio S.A.C.</p>
      <h1>Portal de pedidos Cloud</h1>
      <p>Demostración de aplicación, base de datos y arquitectura escalable.</p>
    </header>
    <section className="status" aria-live="polite">
      <span className={health.status === 'ok' ? 'dot ok' : 'dot'}></span>
      Plataforma: <strong>{health.status || 'no disponible'}</strong>
      {health.database && <span> | Base de datos: {health.database}</span>}
    </section>
    <div className="grid">
      <section className="card">
        <h2>Registrar pedido</h2>
        <form onSubmit={submit}>
          <label>Cliente<input value={customer} maxLength="120" required onChange={e => setCustomer(e.target.value)} placeholder="Nombre del cliente" /></label>
          <label>Total (S/)<input value={total} type="number" min="0" step="0.01" required onChange={e => setTotal(e.target.value)} placeholder="0.00" /></label>
          <button disabled={submitting}>{submitting ? 'Registrando...' : 'Crear pedido'}</button>
        </form>
        {message && <p className="message">{message}</p>}
      </section>
      <section className="card">
        <h2>Pedidos recientes</h2>
        {orders.length === 0 ? <p>No hay pedidos todavía.</p> : <ul>{orders.map(order => <li key={order.id}><strong>#{order.id}</strong><span>{order.customer}</span><em>{currency.format(order.total)}</em></li>)}</ul>}
      </section>
    </div>
    <footer>V1 AWS: ALB, Auto Scaling, API Flask y PostgreSQL/RDS. Expansión multicloud en preparación.</footer>
  </main>
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
