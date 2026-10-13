import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Asset, ScanResult } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { useAuth, canWrite } from '../auth/AuthContext'
import { Card, EmptyState, ErrorState, LoadingState, PriorityBadge } from '../components/common'

export function InventoryPage() {
  const { role } = useAuth()
  const { data, error, loading, reload } = useApiData<Asset[]>(() => api.get('/api/v1/assets'))
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [filter, setFilter] = useState('')

  const filtered = useMemo(() => {
    if (!data) return []
    const q = filter.trim().toLowerCase()
    if (!q) return data
    return data.filter((a) => `${a.hostname} ${a.algorithm_id} ${a.asset_criticality} ${a.current_status}`.toLowerCase().includes(q))
  }, [data, filter])

  async function runScan() {
    setScanning(true)
    try {
      const result = await api.post<ScanResult>('/api/v1/assets/scan')
      setScanResult(result)
      reload()
    } finally {
      setScanning(false)
    }
  }

  if (loading) return <LoadingState label="Loading cryptographic inventory…" />
  if (error) return <ErrorState error={error} />

  return (
    <div className="page">
      <div className="page-header">
        <h1>Cryptographic Inventory</h1>
        {canWrite(role) && (
          <button className="btn btn-primary" onClick={runScan} disabled={scanning}>
            {scanning ? 'Scanning enterprise_lab/configs…' : 'Run discovery scan'}
          </button>
        )}
      </div>

      {scanResult && (
        <div className="state-box state-info">
          Scanned {scanResult.files_scanned} config files across {scanResult.applications_seen} applications from{' '}
          <code>{scanResult.source_dir}</code>: {scanResult.assets_created} created, {scanResult.assets_updated} updated
          {scanResult.errors.length > 0 && `, ${scanResult.errors.length} errors`}.
        </div>
      )}

      <input className="text-input" placeholder="Filter by hostname, algorithm, criticality, status…" value={filter} onChange={(e) => setFilter(e.target.value)} />

      {!data || data.length === 0 ? (
        <EmptyState>No assets discovered yet. Run a discovery scan against the sample enterprise lab configs.</EmptyState>
      ) : (
        <Card>
          <table className="data-table">
            <thead>
              <tr>
                <th>Hostname</th>
                <th>Environment</th>
                <th>Algorithm</th>
                <th>Usage</th>
                <th>Criticality</th>
                <th>Exposure</th>
                <th>Migration status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((asset) => (
                <tr key={asset.id}>
                  <td>
                    <Link to={`/inventory/${asset.id}`}>{asset.hostname}</Link>
                  </td>
                  <td>{asset.environment}</td>
                  <td>
                    <code>{asset.algorithm_id}</code>
                  </td>
                  <td>{asset.usage_type}</td>
                  <td>
                    <PriorityBadge priority={asset.asset_criticality} />
                  </td>
                  <td>{asset.internet_exposure ? 'Internet-facing' : 'Internal'}</td>
                  <td>{asset.current_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="table-footer">
            {filtered.length} of {data.length} assets
          </p>
        </Card>
      )}
    </div>
  )
}
