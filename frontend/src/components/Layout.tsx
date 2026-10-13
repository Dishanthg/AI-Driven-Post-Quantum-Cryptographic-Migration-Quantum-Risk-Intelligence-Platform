import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/', label: 'Executive Overview', end: true },
  { to: '/inventory', label: 'Cryptographic Inventory' },
  { to: '/algorithms', label: 'Algorithm Explorer' },
  { to: '/risk', label: 'Quantum Risk / AI Explanation' },
  { to: '/recommendations', label: 'PQC Recommendations' },
  { to: '/migrations', label: 'Migration Planner' },
  { to: '/benchmarks', label: 'Benchmark Lab' },
  { to: '/quantum-lab', label: 'Quantum Algorithm Lab' },
  { to: '/agility', label: 'Crypto Agility Demo' },
  { to: '/models', label: 'Model Registry' },
  { to: '/audit', label: 'Audit Logs' },
  { to: '/health', label: 'System Health' },
]

export function Layout() {
  const { role, logout } = useAuth()
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">QS</span>
          <span className="brand-name">QuantumShield</span>
        </div>
        <nav>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="role-pill">role: {role}</div>
          <button className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
