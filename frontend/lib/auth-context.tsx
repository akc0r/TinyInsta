"use client"

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import type Keycloak from "keycloak-js"

import { initKeycloak } from "@/lib/keycloak"

type AuthState = {
  ready: boolean
  authenticated: boolean
  username?: string
  userId?: string
  getToken: () => string | undefined
  login: () => void
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [kc, setKc] = useState<Keycloak | null>(null)
  const [ready, setReady] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    const { kc, ready } = initKeycloak()
    ready
      .then((auth) => {
        setKc(kc)
        setAuthenticated(auth)
        setReady(true)
      })
      .catch(() => setReady(true))
  }, [])

  const value: AuthState = {
    ready,
    authenticated,
    username: kc?.tokenParsed?.preferred_username as string | undefined,
    userId: kc?.tokenParsed?.sub,
    getToken: () => kc?.token,
    login: () => kc?.login(),
    logout: () => kc?.logout({ redirectUri: window.location.origin }),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>")
  return ctx
}
