import { defineStore } from 'pinia'
import { ref } from 'vue'
import { API_LOGIN, API_HOME_INDEX, API_LOGOUT } from '../api/paths'
import { ensureCsrf, setCsrfToken } from '../api/csrf'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
	// Keep session in memory only (no persistence across full page reload)
	const user = ref(null)
	const token = ref(null)
	const permissions = ref([])
	const lastLoginAt = ref(0)

	// Promise that resolves once the initial restore-from-refresh attempt finishes.
	// Router guard awaits this so it never redirects before we know if an
	// HttpOnly refresh cookie can recover the session.
	let _readyResolve = null
	const _readyPromise = new Promise(resolve => { _readyResolve = resolve })
	function waitReady() { return _readyPromise }

	// Tab-sync channel to notify other tabs when logout/login occurs
	let bc = null
	try {
		if ('BroadcastChannel' in window) {
			bc = new BroadcastChannel('nt_playback_auth')
			bc.onmessage = (ev) => {
				try {
					const data = ev.data || {}
					if (data.type === 'logout') {
						clear()
						try { router.push('/login') } catch (e) { window.location.href = '/login' }
					}
				} catch (e) {}
			}
		}
	} catch (e) {}

	function setUser(payload) {
		user.value = payload
		// memory-only; do not persist across reloads
	}

	function setToken(t) {
		token.value = t
		// memory-only
	}

	function clear() {
		// Clear from both state and localStorage
		setUser(null)
		setToken(null)
	}

	function logout() {
		// Immediately clear local state (remove access token from memory/localStorage)
		clear()
		// notify other tabs
		try { if (bc) bc.postMessage({ type: 'logout' }) } catch (e) {}

		// attempt server-side logout to blacklist refresh tokens and clear session
		try {
			// backend reads refresh from HttpOnly cookie if present; no need to send token in body
			fetch(API_LOGOUT(), {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({})
			}).catch(() => {})
		} catch (e) {}
		try { router.push('/login') } catch (e) { try { window.location.href = '/login' } catch (ee) {} }
	}

	function handleRedirectOrLoginNext(response) {
		try {
			if (!response) return false
			const status = response.status
			const type = response.type
			const url = response.url || ''
			const redirected = !!response.redirected
			if (type === 'opaqueredirect' || redirected || status === 301 || status === 302 || url.includes('/login/?next=')) {
				// Only clear local state + redirect; do NOT call the server logout
				// endpoint here, as that would send a WebSocket force_logout that
				// could kick an active session on another tab / a just-logged-in user.
				clear()
				try { router.push('/login') } catch (e) { try { window.location.href = '/login' } catch (ee) {} }
				return true
			}
		} catch (e) {}
		return false
	}

	const fullName = () => {
		if (!user.value) return null
		return user.value.username || null
	}

	const roleName = () => {
		if (!user.value) return null
		return user.value.role || null
	}

	async function login(username, password) {
		try {
			// Corrected URL to match the new backend endpoint at /login/
			const response = await fetch(API_LOGIN(), {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password })
			})

			if (handleRedirectOrLoginNext(response)) {
				return false
			}

			if (!response.ok) {
				throw new Error(`Login failed with status: ${response.status}`)
			}

			const data = await response.json()
			setToken(data.access)
			// record recent login time to avoid immediate force-logout races
			try { lastLoginAt.value = Date.now() } catch (e) {}
			// store whatever user info the login returned (may include id)
			if (data && data.username) setUser({ username: data.username, id: data.id || null, role: data.role || null })

			// Quick check: calling the home index may return 403 when the user
			// authenticates but lacks the required "Audio Recording" permission.
			// If we detect 403 here, route the user to the Denied page instead
			// of attempting to load Home (which would surface a 403/exception).
			try {
				const profileResp = await fetch(API_HOME_INDEX(), { credentials: 'include' })
					if (handleRedirectOrLoginNext(profileResp)) return false
				if (profileResp && profileResp.status === 403) {
					try { router.push({ name: 'Denied' }) } catch (e) { try { window.location.href = '/denied' } catch (ee) {} }
					return true
				}
			} catch (e) {
				// ignore network errors here; we'll continue to fetch permissions below
			}
			// ensure we have profile (id) and permissions
			// fetch permissions after login
			try { await fetchPermissions() } catch (e) { console.error('fetchPermissions', e) }

			// If backend returned csrfToken in the login response, cache it immediately
			if (data && data.csrfToken) {
				try { setCsrfToken(data.csrfToken) } catch (e) { console.warn('setCsrfToken failed', e) }
			} else {
				// fallback: attempt to fetch via ensureCsrf()
				try { await ensureCsrf() } catch (e) {}
			}
			return true
		} catch (error) {
			console.error('Login error:', error)
			clear()
			return false
		}
	}


	async function tryRestoreFromRefresh() {
		// Attempt to exchange HttpOnly refresh cookie for an access token.
		// Intentionally does NOT call fetchPermissions() here to avoid a race
		// where a background session check triggers handleRedirectOrLoginNext
		// while the user is in the middle of logging in.
		try {
			const resp = await fetch('/api/token/refresh_from_cookie/', { method: 'POST', credentials: 'include' })
			if (!resp.ok) {
				try { _readyResolve() } catch (e) {}
				return false
			}
			const data = await resp.json()
			if (data && data.access) {
				setToken(data.access)
				try { _readyResolve() } catch (e) {}
				return true
			}
		} catch (e) {}
		try { _readyResolve() } catch (e) {}
		return false
	}


	async function fetchPermissions() {
		try {
			// ensure we have user id by fetching home index (contains user_profile)
			try {
				const profileResp = await fetch(API_HOME_INDEX(), { credentials: 'include' })
				if (handleRedirectOrLoginNext(profileResp)) return
				if (profileResp.ok) {
					const pjson = await profileResp.json()
					if (pjson && pjson.user_profile) {
						const up = pjson.user_profile
						// merge id into user state
						if (up.id) {
							const current = user.value || {}
							setUser(Object.assign({}, current, { id: up.id, username: up.username }))
						}
					}
				}
			} catch (e) {
				console.error('fetch user profile failed', e)
			}

			const resp = await fetch('/api/my-permissions/', { credentials: 'include' })
			if (handleRedirectOrLoginNext(resp)) return
			if (!resp.ok) return
			const payload = await resp.json()
			const perms = payload.permissions || []
			permissions.value = perms
			localStorage.setItem('permissions', JSON.stringify(perms))
		} catch (e) {
			console.error('Error fetching permissions', e)
		}
	}

	function hasPermission(name) {
		// root user bypass
		try {
			if (user.value && user.value.id === 1) return true
		} catch (e) {}
		if (!permissions.value) return false
		return permissions.value.includes(name)
	}

	return { user, token, permissions, lastLoginAt, setUser, setToken, clear, logout, fullName, login, fetchPermissions, hasPermission, roleName, tryRestoreFromRefresh, waitReady }
})
