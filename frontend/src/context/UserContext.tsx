import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getCurrentUser } from '../services/usersServices.ts'
import type { User } from '../types/user.ts'

interface UserContextValue {
  user: User | null
  loading: boolean
  error: unknown
}

const UserContext = createContext<UserContextValue>({ user: null, loading: true, error: null })

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  return (
    <UserContext.Provider value={{ user, loading, error }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  return useContext(UserContext)
}
