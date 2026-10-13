import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { RiskAssessment } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, LoadingState, PriorityBadge } from '../components/common'

export function RiskPage() {
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<RiskAssessment[]>(() => api.get('/api/v1/risk'))
  const [running, setRunning] = useState<string | null>(null)

  async function assessAll(method: 'ml_model' | 'rule_baseline') {
    setRunning(method)
    try {
      await api.post('/api/v1/risk/assess-all', { method })
      reload()
    } finally {
      setRunning(null)
    }
  }

  if (loading) return <LoadingState label="Loading risk assessments…" />
  if (error) return <ErrorState error={error} />

  return (
    <div className="page">
      <div className="page-header">
        <h1>Quantum Risk / AI Risk Explanation</h1>
        {canWrite(role) && (
          <div className="btn-row">
            <button className="btn btn-primary" onClick={() => assessAll('ml_model')} disabled={running !== null}>
              {running === 'ml_model' ? 'Assessing…' : 'Assess all (ML model)'}
            </button>
            <button className="btn btn-ghost" onClick={() => assessAll('rule_baseline')} disabled={running !== null}>
              {running === 'rule_baseline' ? 'Assessing…' : 'Assess all (rule baseline)'}
            </button>
          </div>
        )}
      </div>

      <div className="state-box state-info">
        The ML risk model (LogReg/RandomForest/XGBoost, see Model Registry) is trained on a documented SYNTHETIC
        dataset (synthetic_crypto_inventory) — it is not fit to real organizational incident data. Scores here
        reflect that synthetic ground truth, not a validated real-world risk probability.
      </div>

      {!data || data.length === 0 ? (
        <EmptyState>No risk assessments yet. Run an assessment above (requires analyst/admin role).</EmptyState>
      ) : (
        <Card>
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Priority</th>
                <th>Risk score</th>
                <th>Confidence</th>
                <th>Method</th>
                <th>Top factor</th>
                <th>Assessed</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/inventory/${r.asset_id}`}>{r.asset_id.slice(0, 8)}…</Link>
                  </td>
                  <td>
                    <PriorityBadge priority={r.priority} />
                  </td>
                  <td>{r.risk_score.toFixed(3)}</td>
                  <td>{(r.confidence * 100).toFixed(0)}%</td>
                  <td>{r.method}</td>
                  <td>{r.factors[0]?.feature_name ?? '—'}</td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
