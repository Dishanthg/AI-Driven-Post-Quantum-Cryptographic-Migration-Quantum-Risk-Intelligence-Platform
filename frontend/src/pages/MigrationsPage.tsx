import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { MigrationPlan } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, LoadingState, PriorityBadge } from '../components/common'

export function MigrationsPage() {
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<MigrationPlan[]>(() => api.get('/api/v1/migrations'))
  const [running, setRunning] = useState<string | null>(null)

  async function planAll() {
    setRunning('plan')
    try {
      await api.post('/api/v1/migrations/plan-all')
      reload()
    } finally {
      setRunning(null)
    }
  }

  async function simulateAll() {
    setRunning('simulate')
    try {
      await api.post('/api/v1/migrations/simulate-all')
      reload()
    } finally {
      setRunning(null)
    }
  }

  if (loading) return <LoadingState label="Loading migration plans…" />
  if (error) return <ErrorState error={error} />

  return (
    <div className="page">
      <div className="page-header">
        <h1>Migration Planner</h1>
        {canWrite(role) && (
          <div className="btn-row">
            <button className="btn btn-primary" onClick={planAll} disabled={running !== null}>
              {running === 'plan' ? 'Planning…' : 'Build plans for all recommendations'}
            </button>
            <button className="btn btn-ghost" onClick={simulateAll} disabled={running !== null}>
              {running === 'simulate' ? 'Simulating…' : 'Simulate all pending plans'}
            </button>
          </div>
        )}
      </div>

      {!data || data.length === 0 ? (
        <EmptyState>No migration plans yet. Generate PQC recommendations first, then build plans.</EmptyState>
      ) : (
        <Card>
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Current → Target</th>
                <th>Priority</th>
                <th>Est. effort (h)</th>
                <th>Compatibility risk</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((plan) => (
                <tr key={plan.id}>
                  <td>
                    <Link to={`/inventory/${plan.asset_id}`}>{plan.asset_id.slice(0, 8)}…</Link>
                  </td>
                  <td>
                    <code>{plan.current_algorithm_id}</code> → <code>{plan.target_algorithm_id}</code>
                  </td>
                  <td>
                    <PriorityBadge priority={plan.priority} />
                  </td>
                  <td>{plan.estimated_effort_hours.toFixed(1)}</td>
                  <td>{plan.compatibility_risk}</td>
                  <td>{plan.status}</td>
                  <td>
                    <Link to={`/migrations/${plan.id}`}>Details →</Link>
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
