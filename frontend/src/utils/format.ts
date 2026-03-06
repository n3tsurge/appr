export function formatDate(iso: string): string {
  if (!iso) return '-'
  try {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export function formatRelative(iso: string): string {
  if (!iso) return '-'
  try {
    const now = Date.now()
    const then = new Date(iso).getTime()
    const diff = Math.floor((now - then) / 1000)

    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
    return formatDate(iso)
  } catch {
    return iso
  }
}

export function capitalize(s: string): string {
  if (!s) return ''
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ')
}

export function statusColor(status: string): string {
  const s = status?.toLowerCase()
  switch (s) {
    case 'active':
    case 'operational':
    case 'resolved':
    case 'healthy':
    case 'passing':
      return 'bg-green-100 text-green-800'
    case 'inactive':
    case 'deprecated':
    case 'retired':
      return 'bg-gray-100 text-gray-600'
    case 'degraded':
    case 'warning':
    case 'investigating':
      return 'bg-yellow-100 text-yellow-800'
    case 'outage':
    case 'critical':
    case 'failed':
      return 'bg-red-100 text-red-800'
    case 'maintenance':
    case 'scheduled':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

export function severityColor(severity: string): string {
  const s = severity?.toLowerCase()
  switch (s) {
    case 'critical':
      return 'bg-red-100 text-red-800'
    case 'major':
      return 'bg-orange-100 text-orange-800'
    case 'minor':
      return 'bg-yellow-100 text-yellow-800'
    case 'low':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}
