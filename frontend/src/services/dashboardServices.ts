import api from '../api/api.ts'
import type { Stats, StatsPeriodPreset } from '../types/stats.ts'
import type { RunState } from '../types/workflowRun.ts'

export async function getStats(period: StatsPeriodPreset = 'all'): Promise<Stats> {
  const res = await api.get('/stats/', {
    params: period === 'all' ? {} : { period },
  })
  return res.data as Stats
}

const STREAM_RETRY_MS = 5000

export function streamStats(
  period: StatsPeriodPreset,
  runsState: RunState | null,
  onData: (stats: Stats) => void,
  onError?: (err: Event) => void,
): () => void {
  const params = new URLSearchParams()
  if (period !== 'all') params.set('period', period)
  if (runsState) params.set('runs_state', runsState)
  const qs = params.toString()
  const url = `${import.meta.env.BASE_URL}api/stats/stream${qs ? `?${qs}` : ''}`

  let es: EventSource
  let retryTimer: number | undefined

  const connect = () => {
    es = new EventSource(url)

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
      // EventSource retries network drops itself, but gives up for good on an HTTP error
      // response (e.g. a 502 while the backend restarts), so reconnect manually then.
      if (es.readyState === EventSource.CLOSED) {
        retryTimer = window.setTimeout(connect, STREAM_RETRY_MS)
      }
    }
  }

  connect()

  return () => {
    window.clearTimeout(retryTimer)
    es.close()
  }
}
