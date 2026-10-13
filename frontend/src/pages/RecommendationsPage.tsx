import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { PQCRecommendation } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, LoadingState } from '../components/common'

const STRATEGY_LABEL: Record<string, string> = {
  pqc_migration: 'PQC migration',
  hybrid_migration: 'Hybrid migration',
  deferred: 'Deferred migration',
  agility_prep: 'Crypto-agility preparation',
  manual_review: 'Manual review',
}

export function RecommendationsPage() {
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<PQCRecommendation[]>(() => api.get('/api/v1/recommendations'))
  const [running, setRunning] = useState(false)

  async function recommendAll() {
    setRunning(true)
    try {
      await api.post('/api/v1/recommendations/recommend-all')
      reload()
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <LoadingState label="Loading PQC recommendations…" />
  if (error) return <ErrorState error={error} />

  return (
    <div className="page">
      <div className="page-header">
        <h1>PQC Recommendations</h1>
        {canWrite(role) && (
          <button className="btn btn-primary" onClick={recommendAll} disabled={running}>
            {running ? 'Generating…' : 'Generate for all assessed assets'}
          </button>
        )}
      </div>

      {!data || data.length === 0 ? (
        <EmptyState>No recommendations yet. Assets need a risk assessment first (Quantum Risk page).</EmptyState>
      ) : (
        data.map((rec) => (
          <Card key={rec.id} title={STRATEGY_LABEL[rec.strategy] ?? rec.strategy}>
            <p>
              <Link to={`/inventory/${rec.asset_id}`}>Asset {rec.asset_id.slice(0, 8)}…</Link>
              {rec.target_algorithm_id && (
                <>
                  {' '}
                  → target <code>{rec.target_algorithm_id}</code>
                </>
              )}
            </p>
            <p>
              <strong>Rationale:</strong> {rec.rationale}
            </p>
            <p>
              <strong>Assumptions:</strong> {rec.assumptions}
            </p>
            <p>
              <strong>Trade-offs:</strong> {rec.tradeoffs}
            </p>
          </Card>
        ))
      )}
    </div>
  )
}
