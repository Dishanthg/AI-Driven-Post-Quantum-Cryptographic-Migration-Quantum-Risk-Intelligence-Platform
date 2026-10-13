import { api, ApiError } from '../api/client'
import type { AuditLog } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, isAdmin } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, LoadingState } from '../components/common'

export function AuditPage() {
  const { role } = useAuth()
  const { data, error, loading } = useApiData<AuditLog[]>(() => api.get('/api/v1/audit'))

  if (!isAdmin(role)) {
    return (
      <div className="page">
        <h1>Audit Logs</h1>
        <div className="state-box state-error">Audit logs require the admin role. Current role: {role}.</div>
      </div>
    )
  }

  if (loading) return <LoadingState label="Loading audit logs…" />
  if (error) {
    if (error instanceof ApiError && error.status === 403) {
      return <ErrorState error={error} />
    }
    return <ErrorState error={error} />
  }

  return (
    <div className="page">
      <h1>Audit Logs</h1>
      {!data || data.length === 0 ? (
        <EmptyState>No audit entries yet. State-changing actions (scans, assessments, benchmarks, migrations, quantum runs) are recorded here as they happen.</EmptyState>
      ) : (
        <Card>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.id}>
                  <td>{new Date(entry.timestamp).toLocaleString()}</td>
                  <td>{entry.actor}</td>
                  <td>{entry.action}</td>
                  <td>
                    {entry.target_type}:{entry.target_id === '*' ? '*' : entry.target_id.slice(0, 8) + '…'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
