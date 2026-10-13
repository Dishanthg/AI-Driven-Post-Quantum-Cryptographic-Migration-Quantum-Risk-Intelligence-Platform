import { useState } from 'react'
import { api, ApiError } from '../api/client'
import type { GroverRunResult, QuantumRunSummary, ShorRunResult } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, HardwareBadge, LoadingState } from '../components/common'

function GroverLab({ onRan }: { onRan: () => void }) {
  const [nQubits, setNQubits] = useState(4)
  const [markedState, setMarkedState] = useState(5)
  const [shots, setShots] = useState(2048)
  const [result, setResult] = useState<GroverRunResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function run() {
    setRunning(true)
    setError(null)
    try {
      const res = await api.post<GroverRunResult>('/api/v1/quantum/grover/run', {
        n_qubits: nQubits,
        marked_states: [markedState],
        shots,
        seed: 42,
      })
      setResult(res)
      onRan()
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card title="Grover search lab">
      <div className="form-row">
        <label>
          Qubits (search register)
          <input type="number" min={2} max={16} value={nQubits} onChange={(e) => setNQubits(Number(e.target.value))} />
        </label>
        <label>
          Marked state (index)
          <input type="number" min={0} value={markedState} onChange={(e) => setMarkedState(Number(e.target.value))} />
        </label>
        <label>
          Shots
          <input type="number" min={1} max={8192} value={shots} onChange={(e) => setShots(Number(e.target.value))} />
        </label>
        <button className="btn btn-primary" onClick={run} disabled={running}>
          {running ? 'Running circuit…' : 'Run Grover search'}
        </button>
      </div>
      {!!error && <ErrorState error={error} />}
      {result && (
        <div className="quantum-result">
          <HardwareBadge isRealHardware={false} />
          <dl className="kv-list">
            <dt>Search space size</dt>
            <dd>{result.search_space_size}</dd>
            <dt>Iterations used / optimal</dt>
            <dd>
              {result.iterations_used} / {result.iterations_theoretical_optimal}
            </dd>
            <dt>Circuit depth</dt>
            <dd>{result.circuit_depth}</dd>
            <dt>Success probability</dt>
            <dd>{(result.success_probability * 100).toFixed(2)}%</dd>
            <dt>Runtime</dt>
            <dd>{result.runtime_seconds.toFixed(4)}s</dd>
          </dl>
          <p className="caveat">{result.caveat}</p>
        </div>
      )}
    </Card>
  )
}

function ShorLab({ onRan }: { onRan: () => void }) {
  const [n, setN] = useState(15)
  const [result, setResult] = useState<ShorRunResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function run() {
    setRunning(true)
    setError(null)
    try {
      const res = await api.post<ShorRunResult>('/api/v1/quantum/shor/run', { N: n, counting_qubits: 8, shots: 2048, seed: 42 })
      setResult(res)
      onRan()
    } catch (err) {
      setError(err instanceof ApiError ? err : err)
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card title="Shor factoring lab">
      <div className="form-row">
        <label>
          N (composite to factor — small values only, hard-capped server-side)
          <input type="number" min={4} value={n} onChange={(e) => setN(Number(e.target.value))} />
        </label>
        <button className="btn btn-primary" onClick={run} disabled={running}>
          {running ? 'Running QPE circuit…' : 'Run Shor factoring'}
        </button>
      </div>
      {!!error && <ErrorState error={error} />}
      {result && (
        <div className="quantum-result">
          <HardwareBadge isRealHardware={false} />
          <dl className="kv-list">
            <dt>N</dt>
            <dd>{result.N}</dd>
            <dt>Total qubits (target + counting)</dt>
            <dd>{result.total_qubits}</dd>
            <dt>Circuit depth</dt>
            <dd>{result.circuit_depth}</dd>
            <dt>Period found</dt>
            <dd>{result.period_found ?? 'not found'}</dd>
            <dt>Factors</dt>
            <dd>{result.factors ? `${result.factors[0]} × ${result.factors[1]}` : 'not found'}</dd>
            <dt>Success</dt>
            <dd>{result.success ? 'yes' : 'no'}</dd>
            <dt>Runtime</dt>
            <dd>{result.runtime_seconds.toFixed(4)}s</dd>
          </dl>
          <p className="caveat">{result.caveat}</p>
        </div>
      )}
    </Card>
  )
}

export function QuantumLabPage() {
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<QuantumRunSummary[]>(() => api.get('/api/v1/quantum/runs'))

  return (
    <div className="page">
      <div className="page-header">
        <h1>Quantum Algorithm Lab</h1>
        <HardwareBadge isRealHardware={false} />
      </div>
      <div className="state-box state-info">
        All runs on this page execute on Qiskit Aer (a classical quantum-circuit simulator), hard-capped at a small
        qubit count. They demonstrate the theoretical mechanics of Grover's and Shor's algorithms and do NOT break
        real cryptographic keys — see the caveat printed with each result.
      </div>

      {canWrite(role) ? (
        <div className="grid-2">
          <GroverLab onRan={reload} />
          <ShorLab onRan={reload} />
        </div>
      ) : (
        <div className="state-box state-info">Viewer role can see run history below; analyst/admin role is required to launch new runs.</div>
      )}

      <Card title="Run history">
        {loading && <LoadingState label="Loading run history…" />}
        {!!error && <ErrorState error={error} />}
        {data && data.length === 0 && <EmptyState>No quantum runs recorded yet.</EmptyState>}
        {data && data.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Backend</th>
                <th>Qubits</th>
                <th>Circuit depth</th>
                <th>Shots</th>
                <th>Success probability</th>
                <th>Hardware</th>
                <th>Run at</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id}>
                  <td>{r.backend}</td>
                  <td>{r.qubits}</td>
                  <td>{r.circuit_depth}</td>
                  <td>{r.shots}</td>
                  <td>{(r.success_probability * 100).toFixed(2)}%</td>
                  <td>
                    <HardwareBadge isRealHardware={r.is_real_hardware} />
                  </td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
