import { defineStore } from 'pinia'
import { ref } from 'vue'
import { API_LOGIN, API_HOME_INDEX } from '../api/paths'
import { ensureCsrf, setCsrfToken } from '../api/csrf'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
	// Initialize state from localStorage to enable persistence
	const user = ref(JSON.parse(localStorage.getItem('user')))
	const token = ref(localStorage.getItem('token'))
    const permissions = ref(JSON.parse(localStorage.getItem('permissions') || '[]'))

	function setUser(payload) {
		user.value = payload
		if (payload) {
			localStorage.setItem('user', JSON.stringify(payload))
		} else {
			localStorage.removeItem('user')
		}
	}

	function setToken(t) {
		token.value = t
		if (t) {
			localStorage.setItem('token', t)
		} else {
			localStorage.removeItem('token')
		}
	}

	function clear() {
		// Clear from both state and localStorage
		setUser(null)
		setToken(null)
	}

	function logout() {
		clear()
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
				logout()
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

	return { user, token, permissions, setUser, setToken, clear, logout, fullName, login, fetchPermissions, hasPermission, roleName }
})
