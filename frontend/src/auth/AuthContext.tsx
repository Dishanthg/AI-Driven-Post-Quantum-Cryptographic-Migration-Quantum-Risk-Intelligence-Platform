import { createContext, useContext, useState, type ReactNode } from 'react'
import { getRole, login as apiLogin, setRole, setToken } from '../api/client'

interface AuthState {
  role: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<string | null>(getRole())

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password)
    setToken(res.access_token)
    setRole(res.role)
    setRoleState(res.role)
  }

  function logout() {
    setToken(null)
    setRole(null)
    setRoleState(null)
  }

  return (
    <AuthContext.Provider value={{ role, isAuthenticated: !!role, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function canWrite(role: string | null): boolean {
  return role === 'analyst' || role === 'admin'
}

export function isAdmin(role: string | null): boolean {
  return role === 'admin'
}
