export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function getToken(): string | null {
  return localStorage.getItem('qs_token')
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('qs_token', token)
  else localStorage.removeItem('qs_token')
}

export function getRole(): string | null {
  return localStorage.getItem('qs_role')
}

export function setRole(role: string | null) {
  if (role) localStorage.setItem('qs_role', role)
  else localStorage.removeItem('qs_role')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (init?.body && !(init.body instanceof URLSearchParams)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(path, { ...init, headers })
  if (res.status === 401) {
    setToken(null)
    setRole(null)
    window.location.href = '/login'
    throw new ApiError(401, 'Not authenticated')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? JSON.stringify(body)
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
}

export async function login(username: string, password: string): Promise<{ access_token: string; role: string }> {
  const body = new URLSearchParams({ username, password })
  const res = await fetch('/api/v1/auth/token', { method: 'POST', body })
  if (!res.ok) {
    let detail = 'Login failed'
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail)
  }
  return res.json()
}
