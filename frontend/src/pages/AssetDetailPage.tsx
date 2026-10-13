import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, api } from '../api/client'
import type { AssetDetail, MigrationPlan, PQCRecommendation, RiskAssessment } from '../api/types'
import { Card, ErrorState, LoadingState, PriorityBadge } from '../components/common'

interface DetailState {
  asset: AssetDetail | null
  risk: RiskAssessment | null
  recommendations: PQCRecommendation[]
  migrations: MigrationPlan[]
}

export function AssetDetailPage() {
  const { assetId } = useParams<{ assetId: string }>()
  const [state, setState] = useState<DetailState | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!assetId) return
    setLoading(true)
    setError(null)
    Promise.all([
      api.get<AssetDetail>(`/api/v1/assets/${assetId}`),
      api.get<RiskAssessment>(`/api/v1/risk/asset/${assetId}/latest`).catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e))),
      api.get<PQCRecommendation[]>(`/api/v1/recommendations?asset_id=${assetId}`),
      api.get<MigrationPlan[]>(`/api/v1/migrations?asset_id=${assetId}`),
    ])
      .then(([asset, risk, recommendations, migrations]) => setState({ asset, risk, recommendations, migrations }))
      .catch(setError)
      .finally(() => setLoading(false))
  }, [assetId])

  if (loading) return <LoadingState label="Loading asset detail…" />
  if (error) return <ErrorState error={error} />
  if (!state?.asset) return null

  const { asset, risk, recommendations, migrations } = state

  return (
    <div className="page">
      <div className="page-header">
        <h1>{asset.hostname}</h1>
        <Link className="btn btn-ghost" to="/inventory">
          ← Back to inventory
        </Link>
      </div>

      <div className="grid-2">
        <Card title="Configuration">
          <dl className="kv-list">
            <dt>Application</dt>
            <dd>
              {asset.application.name} ({asset.application.business_unit}, importance: {asset.application.business_importance})
            </dd>
            <dt>Algorithm</dt>
            <dd>
              <code>{asset.algorithm_id}</code> ({asset.key_size_bits} bits)
            </dd>
            <dt>Usage / protocol</dt>
            <dd>
              {asset.usage_type} / {asset.protocol}
            </dd>
            <dt>Environment</dt>
            <dd>{asset.environment}</dd>
            <dt>Internet exposure</dt>
            <dd>{asset.internet_exposure ? 'Internet-facing' : 'Internal only'}</dd>
            <dt>Data sensitivity / lifetime</dt>
            <dd>
              {asset.data_sensitivity}, {asset.data_lifetime_years} years
            </dd>
            <dt>Criticality</dt>
            <dd>
              <PriorityBadge priority={asset.asset_criticality} />
            </dd>
            <dt>Migration complexity</dt>
            <dd>{asset.migration_complexity}</dd>
            <dt>Status</dt>
            <dd>{asset.current_status}</dd>
            <dt>Discovery source</dt>
            <dd>
              <code>{asset.discovery_source}</code>
            </dd>
          </dl>
          {asset.certificates.length > 0 && (
            <>
              <h4>Certificates</h4>
              <ul>
                {asset.certificates.map((c) => (
                  <li key={c.id}>
                    {c.subject} — signed with <code>{c.signature_algorithm_id}</code>, valid {c.not_before} → {c.not_after}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card title="Quantum risk assessment">
          {risk ? (
            <>
              <dl className="kv-list">
                <dt>Priority</dt>
                <dd>
                  <PriorityBadge priority={risk.priority} />
                </dd>
                <dt>Risk score</dt>
                <dd>{risk.risk_score.toFixed(4)}</dd>
                <dt>Confidence</dt>
                <dd>{(risk.confidence * 100).toFixed(1)}%</dd>
                <dt>Method</dt>
                <dd>{risk.method}</dd>
              </dl>
              {risk.factors.length > 0 && (
                <>
                  <h4>Top contributing factors (SHAP)</h4>
                  <ul className="factor-list">
                    {risk.factors.map((f) => (
                      <li key={f.feature_name}>
                        <span>{f.feature_name}</span>
                        <span className={f.contribution >= 0 ? 'factor-positive' : 'factor-negative'}>{f.contribution.toFixed(3)}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p>No risk assessment yet for this asset. Trigger one from the Quantum Risk page.</p>
          )}
        </Card>
      </div>

      <Card title="PQC recommendations">
        {recommendations.length === 0 ? (
          <p>No recommendation generated yet.</p>
        ) : (
          recommendations.map((rec) => (
            <div key={rec.id} className="recommendation-block">
              <p>
                <strong>Strategy:</strong> {rec.strategy}
                {rec.target_algorithm_id && (
                  <>
                    {' '}
                    → <code>{rec.target_algorithm_id}</code>
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
            </div>
          ))
        )}
      </Card>

      <Card title="Migration plans">
        {migrations.length === 0 ? (
          <p>No migration plan yet for this asset.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Target</th>
                <th>Priority</th>
                <th>Est. effort (h)</th>
                <th>Compatibility risk</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {migrations.map((plan) => (
                <tr key={plan.id}>
                  <td>
                    <code>{plan.target_algorithm_id}</code>
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
        )}
      </Card>
    </div>
  )
}
