import type { ReactElement } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { InventoryPage } from './pages/InventoryPage'
import { AssetDetailPage } from './pages/AssetDetailPage'
import { AlgorithmsPage } from './pages/AlgorithmsPage'
import { RiskPage } from './pages/RiskPage'
import { RecommendationsPage } from './pages/RecommendationsPage'
import { MigrationsPage } from './pages/MigrationsPage'
import { MigrationPlanDetailPage } from './pages/MigrationPlanDetailPage'
import { BenchmarksPage } from './pages/BenchmarksPage'
import { QuantumLabPage } from './pages/QuantumLabPage'
import { AgilityDemoPage } from './pages/AgilityDemoPage'
import { ModelsPage } from './pages/ModelsPage'
import { AuditPage } from './pages/AuditPage'
import { HealthPage } from './pages/HealthPage'

function RequireAuth({ children }: { children: ReactElement }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<OverviewPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/inventory/:assetId" element={<AssetDetailPage />} />
        <Route path="/algorithms" element={<AlgorithmsPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/migrations" element={<MigrationsPage />} />
        <Route path="/migrations/:planId" element={<MigrationPlanDetailPage />} />
        <Route path="/benchmarks" element={<BenchmarksPage />} />
        <Route path="/quantum-lab" element={<QuantumLabPage />} />
        <Route path="/agility" element={<AgilityDemoPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/health" element={<HealthPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
