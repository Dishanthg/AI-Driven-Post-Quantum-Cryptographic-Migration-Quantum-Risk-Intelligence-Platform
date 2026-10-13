import type { CSSProperties, ReactNode } from 'react'
import { ApiError } from '../api/client'

// Shared Recharts <Tooltip contentStyle={CHART_TOOLTIP_STYLE} /> so every chart's
// hover tooltip matches the dark theme instead of Recharts' default white box.
export const CHART_TOOLTIP_STYLE: CSSProperties = {
  background: '#fffefb',
  border: '1px solid #ddd6c7',
  borderRadius: 6,
  fontSize: 12.5,
  color: '#211e19',
  boxShadow: '2px 2px 0 rgba(28,25,20,0.09)',
}
export const CHART_TOOLTIP_LABEL_STYLE: CSSProperties = { color: '#5c5648', marginBottom: 4, fontWeight: 600 }
export const CHART_AXIS_COLOR = '#8a8371'
export const CHART_GRID_COLOR = '#ddd6c7'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <div className="state-box state-loading">{label}</div>
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : String(error)
  return <div className="state-box state-error">Request failed: {message}</div>
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state-box state-empty">{children}</div>
}

export function DataBadge({ kind }: { kind: 'real' | 'synthetic' | 'simulated' }) {
  const label = { real: 'REAL DATA', synthetic: 'SYNTHETIC DATA', simulated: 'SIMULATION' }[kind]
  return <span className={`badge badge-${kind}`}>{label}</span>
}

export function PriorityBadge({ priority }: { priority: string }) {
  return <span className={`badge badge-priority-${priority}`}>{priority.toUpperCase()}</span>
}

export function HardwareBadge({ isRealHardware }: { isRealHardware: boolean }) {
  return isRealHardware ? (
    <span className="badge badge-hw-real">REAL QUANTUM HARDWARE</span>
  ) : (
    <span className="badge badge-hw-sim">SIMULATOR — not real quantum hardware</span>
  )
}

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-header">
          {title && <h3>{title}</h3>}
          {actions}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  )
}

export function StatTile({ label, value, tone }: { label: string; value: ReactNode; tone?: 'critical' | 'high' | 'neutral' }) {
  return (
    <div className={`stat-tile ${tone ? `stat-tile-${tone}` : ''}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
