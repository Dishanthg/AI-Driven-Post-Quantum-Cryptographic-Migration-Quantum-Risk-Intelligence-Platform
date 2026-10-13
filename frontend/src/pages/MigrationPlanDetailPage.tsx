import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { MigrationPlan } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { Card, ErrorState, LoadingState, PriorityBadge } from '../components/common'

export function MigrationPlanDetailPage() {
  const { planId } = useParams<{ planId: string }>()
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<MigrationPlan>(() => api.get(`/api/v1/migrations/${planId}`), [planId])
  const [simulating, setSimulating] = useState(false)

  async function simulate() {
    setSimulating(true)
    try {
      await api.post(`/api/v1/migrations/${planId}/simulate`)
      reload()
    } finally {
      setSimulating(false)
    }
  }

  if (loading) return <LoadingState label="Loading migration plan…" />
  if (error) return <ErrorState error={error} />
  if (!data) return null

  const perf = data.performance_impact_json as Record<string, unknown>

  return (
    <div className="page">
      <div className="page-header">
        <h1>
          Migration: <code>{data.current_algorithm_id}</code> → <code>{data.target_algorithm_id}</code>
        </h1>
        <div className="btn-row">
          <Link className="btn btn-ghost" to="/migrations">
            ← Back to migrations
          </Link>
          {canWrite(role) && (
            <button className="btn btn-primary" onClick={simulate} disabled={simulating}>
              {simulating ? 'Simulating…' : 'Re-run simulation'}
            </button>
          )}
        </div>
      </div>

      <div className="grid-2">
        <Card title="Plan details">
          <dl className="kv-list">
            <dt>Priority</dt>
            <dd>
              <PriorityBadge priority={data.priority} />
            </dd>
            <dt>Status</dt>
            <dd>{data.status}</dd>
            <dt>Estimated effort</dt>
            <dd>{data.estimated_effort_hours.toFixed(1)} hours</dd>
            <dt>Compatibility risk</dt>
            <dd>{data.compatibility_risk}</dd>
            <dt>Owner</dt>
            <dd>{data.owner}</dd>
            <dt>Rollback strategy</dt>
            <dd>{data.rollback_strategy}</dd>
            <dt>Verification criteria</dt>
            <dd>{data.verification_criteria}</dd>
          </dl>
        </Card>

        <Card title="Simulated performance impact">
          {Object.keys(perf).length === 0 ? (
            <p>Not simulated yet.</p>
          ) : (
            <pre className="json-block">{JSON.stringify(perf, null, 2)}</pre>
          )}
        </Card>
      </div>

      <Card title="Migration steps">
        {data.steps.length === 0 ? (
          <p>No steps recorded.</p>
        ) : (
          <ol className="step-list">
            {data.steps
              .slice()
              .sort((a, b) => a.sequence - b.sequence)
              .map((step) => (
                <li key={step.id}>
                  <div className="step-head">
                    <strong>{step.stage}</strong> <span className="step-status">{step.status}</span>
                  </div>
                  <p>{step.description}</p>
                  {Object.keys(step.simulated_result_json).length > 0 && (
                    <pre className="json-block">{JSON.stringify(step.simulated_result_json, null, 2)}</pre>
                  )}
                </li>
              ))}
          </ol>
        )}
      </Card>
    </div>
  )
}
