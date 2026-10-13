import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { InventoryOverview } from '../api/types'
import { useApiData } from '../hooks/useApiData'
import { CHART_AXIS_COLOR, CHART_GRID_COLOR, CHART_TOOLTIP_STYLE, Card, DataBadge, ErrorState, LoadingState, StatTile } from '../components/common'

// Status/severity colors - matches index.css's --critical/--high/--medium/--low
// tokens (and the badge colors) exactly, so the pie and the badges never disagree.
const PRIORITY_COLORS: Record<string, string> = {
  critical: '#a8321f',
  high: '#b5661a',
  medium: '#93720a',
  low: '#3f7d4c',
}

// Categorical identity palette (dataviz skill, validated against this app's warm
// paper card surface #fffefb) - fixed slot order, never reassigned per-render.
const CHART_CATEGORICAL = ['#2f6f6b', '#b5472a', '#4a6fa0', '#93720a', '#7a5c8e', '#5c7a3f']

export function OverviewPage() {
  const { data, error, loading } = useApiData<InventoryOverview>(() => api.get('/api/v1/assets/overview'))

  if (loading) return <LoadingState label="Loading inventory overview…" />
  if (error) return <ErrorState error={error} />
  if (!data) return null

  if (data.total_assets === 0) {
    return (
      <Card title="Executive Overview">
        <p>No cryptographic assets discovered yet. Trigger a scan from the Cryptographic Inventory page.</p>
      </Card>
    )
  }

  const priorityData = Object.entries(data.priority_distribution).map(([priority, count]) => ({ priority, count }))
  const algoData = Object.entries(data.algorithm_distribution)
    .sort((a, b) => b[1] - a[1])
    .map(([algorithm_id, count]) => ({ algorithm_id, count }))
  const statusData = Object.entries(data.migration_status_distribution).map(([status, count]) => ({ status, count }))

  return (
    <div className="page">
      <div className="page-header">
        <h1>Executive Overview</h1>
        <DataBadge kind="real" />
      </div>

      <div className="stat-grid">
        <StatTile label="Total cryptographic assets" value={data.total_assets} />
        <StatTile label="Legacy public-key assets" value={data.legacy_public_key_assets} tone="high" />
        <StatTile label="Critical-priority assets" value={data.critical_risk_assets} tone="critical" />
        <StatTile label="High-priority assets" value={data.high_risk_assets} tone="high" />
        <StatTile label="PQC-migrated assets" value={data.pqc_migrated_assets} />
        <StatTile label="Hybrid assets" value={data.hybrid_assets} />
      </div>

      <div className="grid-2">
        <Card title="Migration priority distribution">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={priorityData}
                dataKey="count"
                nameKey="priority"
                outerRadius={90}
                label={(e: any) => `${e.priority}: ${e.count}`}
              >
                {priorityData.map((entry) => (
                  <Cell key={entry.priority} fill={PRIORITY_COLORS[entry.priority] ?? '#94a3b8'} />
                ))}
              </Pie>
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Migration status distribution">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={statusData}
                dataKey="count"
                nameKey="status"
                outerRadius={90}
                label={(e: any) => `${e.status}: ${e.count}`}
              >
                {statusData.map((entry, i) => (
                  <Cell key={entry.status} fill={CHART_CATEGORICAL[i % CHART_CATEGORICAL.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Algorithm distribution across discovered assets">
        <ResponsiveContainer width="100%" height={Math.max(220, algoData.length * 32)}>
          <BarChart data={algoData} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} horizontal={false} />
            <XAxis type="number" allowDecimals={false} stroke={CHART_AXIS_COLOR} tick={{ fill: CHART_AXIS_COLOR, fontSize: 11.5 }} />
            <YAxis type="category" dataKey="algorithm_id" width={210} tick={{ fontSize: 12, fill: '#211e19' }} stroke={CHART_GRID_COLOR} />
            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: 'rgba(28,25,20,0.05)' }} />
            <Bar dataKey="count" fill={CHART_CATEGORICAL[0]} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
