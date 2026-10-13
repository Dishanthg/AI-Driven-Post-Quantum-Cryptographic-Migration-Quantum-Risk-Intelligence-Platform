import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { BenchmarkSummary } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { CHART_AXIS_COLOR, CHART_GRID_COLOR, CHART_TOOLTIP_STYLE, Card, DataBadge, EmptyState, ErrorState, LoadingState } from '../components/common'

export function BenchmarksPage() {
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<BenchmarkSummary[]>(() => api.get('/api/v1/benchmarks/runs'))
  const [providerKey, setProviderKey] = useState('')
  const [operation, setOperation] = useState<'keygen' | 'kem' | 'signature'>('keygen')
  const [iterations, setIterations] = useState(30)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<unknown>(null)

  const knownProviderKeys = useMemo(() => {
    if (!data) return []
    return Array.from(new Set(data.map((r) => r.provider_key))).sort()
  }, [data])

  const chartData = useMemo(() => {
    if (!data) return []
    return data
      .slice()
      .reverse()
      .map((r) => ({
        label: `${r.provider_key}:${r.operation}`,
        mean_ms: r.mean_ms,
        errLow: r.mean_ms - r.ci95_low_ms,
        errHigh: r.ci95_high_ms - r.mean_ms,
      }))
  }, [data])

  async function runBenchmark() {
    if (!providerKey.trim()) return
    setRunning(true)
    setRunError(null)
    try {
      await api.post('/api/v1/benchmarks/run', { provider_key: providerKey.trim(), operation, iterations })
      reload()
    } catch (err) {
      setRunError(err)
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <LoadingState label="Loading benchmark history…" />
  if (error) return <ErrorState error={error} />

  return (
    <div className="page">
      <div className="page-header">
        <h1>Benchmark Lab</h1>
        <DataBadge kind="real" />
      </div>

      {canWrite(role) && (
        <Card title="Run a new benchmark">
          <div className="form-row">
            <label>
              Provider key
              <input
                className="text-input"
                placeholder="e.g. rsa2048, ecdsa_p256, ml_kem_768, ml_dsa_65"
                list="known-provider-keys"
                value={providerKey}
                onChange={(e) => setProviderKey(e.target.value)}
              />
              <datalist id="known-provider-keys">
                {knownProviderKeys.map((k) => (
                  <option key={k} value={k} />
                ))}
              </datalist>
            </label>
            <label>
              Operation
              <select value={operation} onChange={(e) => setOperation(e.target.value as typeof operation)}>
                <option value="keygen">keygen</option>
                <option value="kem">kem</option>
                <option value="signature">signature</option>
              </select>
            </label>
            <label>
              Iterations
              <input type="number" min={1} max={500} value={iterations} onChange={(e) => setIterations(Number(e.target.value))} />
            </label>
            <button className="btn btn-primary" onClick={runBenchmark} disabled={running}>
              {running ? 'Running (real timing loop)…' : 'Run'}
            </button>
          </div>
          {!!runError && <ErrorState error={runError} />}
        </Card>
      )}

      {!data || data.length === 0 ? (
        <EmptyState>No benchmark runs recorded yet. Run one above, or via `make benchmark`.</EmptyState>
      ) : (
        <>
          <Card title="Mean latency by algorithm/operation (ms, 95% CI)">
            <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 28)}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} horizontal={false} />
                <XAxis type="number" stroke={CHART_AXIS_COLOR} tick={{ fill: CHART_AXIS_COLOR, fontSize: 11.5 }} />
                <YAxis type="category" dataKey="label" width={180} tick={{ fontSize: 11.5, fill: '#211e19' }} stroke={CHART_GRID_COLOR} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: 'rgba(28,25,20,0.05)' }} />
                <Bar dataKey="mean_ms" fill="#2f6f6b" radius={[0, 4, 4, 0]}>
                  <ErrorBar dataKey="errHigh" width={4} strokeWidth={1.5} stroke="#7a5c8e" direction="x" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Raw benchmark runs">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Operation</th>
                  <th>Iterations</th>
                  <th>Mean (ms)</th>
                  <th>p95 (ms)</th>
                  <th>95% CI (ms)</th>
                  <th>Public key bytes</th>
                  <th>Ciphertext/sig bytes</th>
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i}>
                    <td>
                      <code>{r.provider_key}</code>
                    </td>
                    <td>{r.operation}</td>
                    <td>{r.iterations}</td>
                    <td>{r.mean_ms.toFixed(4)}</td>
                    <td>{r.p95_ms.toFixed(4)}</td>
                    <td>
                      [{r.ci95_low_ms.toFixed(4)}, {r.ci95_high_ms.toFixed(4)}]
                    </td>
                    <td>{r.public_key_bytes ?? '—'}</td>
                    <td>{r.ciphertext_or_signature_bytes ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  )
}
