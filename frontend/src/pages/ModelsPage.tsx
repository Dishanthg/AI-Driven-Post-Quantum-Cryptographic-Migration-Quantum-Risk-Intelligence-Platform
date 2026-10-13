import { api } from '../api/client'
import type { ModelVersion } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { Card, DataBadge, EmptyState, ErrorState, LoadingState } from '../components/common'

export function ModelsPage() {
  const { data, error, loading } = useApiData<ModelVersion[]>(() => api.get('/api/v1/models'))

  if (loading) return <LoadingState label="Loading model registry…" />
  if (error) return <ErrorState error={error} />

  return (
    <div className="page">
      <div className="page-header">
        <h1>Model Registry</h1>
        <DataBadge kind="synthetic" />
      </div>
      <div className="state-box state-info">
        Every version below is a real, executed training run against the documented SYNTHETIC
        synthetic_crypto_inventory dataset — metrics are read straight from the stored evaluation output, never
        entered by hand.
      </div>

      {!data || data.length === 0 ? (
        <EmptyState>No model versions registered yet. Train one with `make train`.</EmptyState>
      ) : (
        data.map((m) => (
          <Card key={m.id} title={`${m.algorithm} — v${m.version}`} actions={m.is_active ? <span className="badge badge-priority-low">ACTIVE</span> : undefined}>
            <dl className="kv-list">
              <dt>Dataset</dt>
              <dd>{m.dataset_ref}</dd>
              <dt>Random seed</dt>
              <dd>{m.random_seed}</dd>
              <dt>Artifact path</dt>
              <dd>
                <code>{m.artifact_path}</code>
              </dd>
            </dl>
            <pre className="json-block">{JSON.stringify(m.metrics_json, null, 2)}</pre>
          </Card>
        ))
      )}
    </div>
  )
}
