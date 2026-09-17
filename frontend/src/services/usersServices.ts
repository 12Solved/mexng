import api from '../api/api.ts'
import type { User } from '../types/user.ts'

export async function getCurrentUser(): Promise<User> {
  const res = await api.get('/users/me')
  return res.data
}
