/**
 * Whether the server can be reached — decided by trying, not by asking.
 *
 * `navigator.onLine` is true on any Wi-Fi, including one with no route to
 * the house, and on mobile data outside it. To this app that is offline. So
 * the flag is driven by what actually happens: a network failure marks us
 * offline, a successful response marks us online, and while offline a small
 * probe of /health keeps trying so the queue can drain the moment the
 * server is back — without waiting for a browser event that may never come.
 */

import { onlineManager } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'

const PROBE_INTERVAL_MS = 5_000
const PROBE_TIMEOUT_MS = 3_000

let probeTimer: number | null = null

async function probe(): Promise<boolean> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS)
  try {
    const response = await fetch('/health', { cache: 'no-store', signal: controller.signal })
    return response.ok
  } catch {
    return false
  } finally {
    window.clearTimeout(timeout)
  }
}

function startProbing(): void {
  if (probeTimer !== null) return
  probeTimer = window.setInterval(() => {
    void probe().then((ok) => {
      if (ok) markOnline()
    })
  }, PROBE_INTERVAL_MS)
}

function stopProbing(): void {
  if (probeTimer === null) return
  window.clearInterval(probeTimer)
  probeTimer = null
}

export function markOffline(): void {
  if (onlineManager.isOnline()) onlineManager.setOnline(false)
  startProbing()
}

export function markOnline(): void {
  stopProbing()
  if (!onlineManager.isOnline()) onlineManager.setOnline(true)
}

/**
 * Wire the manager to the browser's own events as a hint, then let request
 * outcomes correct it. A browser "online" event triggers an immediate probe
 * rather than being believed outright.
 */
export function installConnectivity(): void {
  onlineManager.setEventListener((setOnline) => {
    const onOnline = () => {
      void probe().then((ok) => {
        if (ok) {
          stopProbing()
          setOnline(true)
        } else {
          startProbing()
        }
      })
    }
    const onOffline = () => {
      setOnline(false)
      startProbing()
    }
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  })

  // The very first thing: is the server there right now?
  void probe().then((ok) => (ok ? markOnline() : markOffline()))
}

export function useIsOnline(): boolean {
  return useSyncExternalStore(
    (callback) => onlineManager.subscribe(callback),
    () => onlineManager.isOnline(),
  )
}
