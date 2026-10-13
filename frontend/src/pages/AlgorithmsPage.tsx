import { useState } from 'react'
import { api } from '../api/client'
import type { Algorithm, ThreatEntry } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { Card, ErrorState, LoadingState } from '../components/common'

const CLASSIFICATION_LABEL: Record<string, string> = {
  classical_pk: 'Classical public-key',
  classical_sym: 'Classical symmetric',
  hash: 'Hash function',
  pqc_kem: 'Post-quantum KEM',
  pqc_sig: 'Post-quantum signature',
  hybrid: 'Hybrid classical + PQC',
}

export function AlgorithmsPage() {
  const { data, error, loading } = useApiData<Algorithm[]>(() => api.get('/api/v1/algorithms'))
  const [selected, setSelected] = useState<string | null>(null)
  const [threat, setThreat] = useState<ThreatEntry | null>(null)
  const [threatLoading, setThreatLoading] = useState(false)

  async function selectAlgorithm(id: string) {
    setSelected(id)
    setThreat(null)
    setThreatLoading(true)
    try {
      const t = await api.get<ThreatEntry>(`/api/v1/algorithms/${id}/threat`)
      setThreat(t)
    } finally {
      setThreatLoading(false)
    }
  }

  if (loading) return <LoadingState label="Loading algorithm registry…" />
  if (error) return <ErrorState error={error} />
  if (!data) return null

  return (
    <div className="page">
      <h1>Algorithm Explorer</h1>
      <div className="grid-2">
        <Card title="Algorithm registry">
          <table className="data-table">
            <thead>
              <tr>
                <th>Algorithm</th>
                <th>Classification</th>
                <th>Quantum vulnerability</th>
                <th>Standard</th>
              </tr>
            </thead>
            <tbody>
              {data.map((algo) => (
                <tr key={algo.id} className={selected === algo.id ? 'row-selected' : ''} onClick={() => selectAlgorithm(algo.id)}>
                  <td>
                    <code>{algo.id}</code>
                  </td>
                  <td>{CLASSIFICATION_LABEL[algo.classification] ?? algo.classification}</td>
                  <td>{algo.quantum_vulnerability}</td>
                  <td>{algo.standard_ref}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title={selected ? `Quantum threat model — ${selected}` : 'Select an algorithm'}>
          {!selected && <p>Click a row to view its quantum threat model entry.</p>}
          {threatLoading && <LoadingState label="Loading threat model…" />}
          {threat && (
            <dl className="kv-list">
              <dt>Attack model</dt>
              <dd>{threat.attack_model}</dd>
              <dt>Classical security assumption</dt>
              <dd>{threat.classical_security_assumption}</dd>
              <dt>Theoretical quantum complexity</dt>
              <dd>{threat.theoretical_quantum_complexity}</dd>
              <dt>Practical constraint</dt>
              <dd>{threat.practical_constraint}</dd>
              <dt>Current limitation</dt>
              <dd>{threat.current_limitation}</dd>
              <dt>Plain-language explanation</dt>
              <dd>{threat.plain_language_explanation}</dd>
            </dl>
          )}
        </Card>
      </div>
    </div>
  )
}
