import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Readiness } from '../types/domain'

export function useReadiness() {
  const [data, setData] = useState<Readiness | null>(null)
  const [connected, setConnected] = useState(true)

  useEffect(() => {
    let active = true
    let timer: number | undefined
    const poll = async () => {
      try {
        const next = await api.readiness()
        if (!active) return
        setData(next)
        setConnected(true)
        if (!next.completed) timer = window.setTimeout(poll, 450)
      } catch {
        if (!active) return
        setConnected(false)
        timer = window.setTimeout(poll, 800)
      }
    }
    poll()
    return () => { active = false; window.clearTimeout(timer) }
  }, [])

  return { data, connected }
}

