import { ref } from 'vue'
import { useAuthStore } from '../stores/auth.store'

let ws = null
let connected = ref(false)

export function useNotifications() {
  const authStore = useAuthStore()

  const setup = () => {
    try {
      if (ws) return
      const loc = window.location
      const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${proto}//${loc.host}/ws/notifications/`

      ws = new WebSocket(wsUrl)
      ws.onopen = () => { connected.value = true }
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data)
          if (!data) return
          if (data.type === 'force_logout') {
            try {
              const now = Date.now()
              const last = (authStore && authStore.lastLoginAt) ? authStore.lastLoginAt : 0
              const lastVal = (typeof last === 'function') ? last() : last
              // ignore force_logout if within 5 seconds of a successful login to avoid race
              if (lastVal && (now - lastVal) < 5000) {
                console.debug('Ignored force_logout due to recent login')
                return
              }
              authStore.logout()
            } catch (e) { console.warn('force_logout handler failed', e) }
            return
          }
          // other message types can be handled by components subscribing to events
        } catch (e) { /* ignore malformed */ }
      }
      ws.onclose = () => {
        connected.value = false
        ws = null
        setTimeout(setup, 5000)
      }
      ws.onerror = () => { try { ws.close() } catch (e) {} }
    } catch (e) {
      console.warn('useNotifications.setup failed', e)
    }
  }

  const stop = () => {
    try { if (ws) { ws.close(); ws = null } } catch (e) {}
    connected.value = false
  }

  return { setup, stop, connected }
}

export function initNotifications() {
  // convenience for one-off initialization
  const n = useNotifications()
  n.setup()
  return n
}
