import api from '../api/api.ts'
import type { Stats, StatsPeriodPreset } from '../types/stats.ts'

export async function getStats(period: StatsPeriodPreset = 'all'): Promise<Stats> {
  const res = await api.get('/stats/', {
    params: period === 'all' ? {} : { period },
  })
  return res.data as Stats
}

export function streamStats(
  period: StatsPeriodPreset,
  onData: (stats: Stats) => void,
  onError?: (err: Event) => void,
): () => void {
  const q = period === 'all' ? '' : `?period=${encodeURIComponent(period)}`
  const es = new EventSource(`${import.meta.env.BASE_URL}api/stats/stream${q}`)

  es.onmessage = (event) => {
    try {
      onData(JSON.parse(event.data) as Stats)
    } catch (e) {
      console.error('Failed to parse stats event', e)
    }
  }

  es.onerror = (err) => {
    console.error('Stats SSE error', err)
    onError?.(err)
  }

  return () => es.close()
}
