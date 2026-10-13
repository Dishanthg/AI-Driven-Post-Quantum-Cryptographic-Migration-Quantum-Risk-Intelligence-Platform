import { api } from '../api/client'
import type { HealthStatus } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { Card, ErrorState, LoadingState } from '../components/common'

export function HealthPage() {
  const { data, error, loading, reload } = useApiData<HealthStatus>(() => api.get('/api/v1/health'))

  return (
    <div className="page">
      <div className="page-header">
        <h1>System Health</h1>
        <button className="btn btn-ghost" onClick={reload}>
          Refresh
        </button>
      </div>

      {loading && <LoadingState label="Checking backend health…" />}
      {!!error && <ErrorState error={error} />}
      {data && (
        <Card title={data.app_name}>
          <dl className="kv-list">
            <dt>Overall status</dt>
            <dd className={data.status === 'ok' ? 'status-ok' : 'status-degraded'}>{data.status}</dd>
            <dt>Database</dt>
            <dd>{data.database}</dd>
            <dt>Risk model artifacts</dt>
            <dd>{data.risk_model_artifacts}</dd>
            <dt>Environment</dt>
            <dd>{data.environment}</dd>
          </dl>
          <p>
            Prometheus metrics are exposed at <code>/metrics</code> (scraped by the <code>prometheus</code>{' '}
            docker-compose service; view via Grafana on port 3001).
          </p>
        </Card>
      )}
    </div>
  )
}
