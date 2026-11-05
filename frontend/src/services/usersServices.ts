import api from '../api/api.ts'
import type { User } from '../types/user.ts'

export async function getCurrentUser(): Promise<User> {
  const res = await api.get('/users/me')
  return res.data
}

export async function updateCurrentUserEmail(email: string | null): Promise<User> {
  const res = await api.patch('/users/me', { email })
  return res.data
}
