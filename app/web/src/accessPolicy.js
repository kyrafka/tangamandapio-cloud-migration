export const roleLabels = Object.freeze({
  customer: 'Cliente B2B',
  sales: 'Comercial',
  warehouse: 'Operador WMS',
  operations: 'Operaciones TI',
  admin: 'Administrador',
  auditor: 'Auditor',
})

export const internalRoles = new Set(['sales', 'warehouse', 'operations', 'admin', 'auditor'])
export const opsRoles = new Set(['operations', 'admin', 'auditor', 'warehouse'])
export const writeRoles = new Set(['customer', 'sales', 'admin'])

export function hasErpAccess(permissions) {
  return Array.isArray(permissions) && permissions.length > 0
}

export function createPortalNavigation(role) {
  const isOperations = opsRoles.has(role)
  const isAdmin = role === 'admin'
  const hasInternalErp = internalRoles.has(role)

  return [
    ['dashboard', 'Resumen'],
    ['orders', 'Pedidos'],
    ...(isOperations ? [['operations', 'Integración WMS']] : []),
    ...(hasInternalErp ? [['erp', 'ERP y correo']] : []),
    ...(isAdmin ? [['administration', 'Administración']] : []),
    ...(['operations', 'auditor', 'admin'].includes(role) ? [['audit', 'Auditoría']] : []),
    ['account', 'Mi cuenta'],
  ]
}
