import { defineStore } from 'pinia'
import { ref } from 'vue'
import { API_LICENSE_INFO } from '../api/paths'

export const useLicenseStore = defineStore('license', () => {
	const licenseId = ref(null)
	const customerName = ref(null)
	const expiryDate = ref(null)
	const maxMainDb = ref(null)
	const maxConcurrentUsers = ref(null)
	const activeUsers = ref(0)
	const allowedMenus = ref([])
	const configFlags = ref({})
	const loaded = ref(false)

	async function fetchLicenseInfo() {
		try {
			const res = await fetch(API_LICENSE_INFO(), { credentials: 'include' })
			if (!res.ok) {
				loaded.value = false
				return
			}
			const data = await res.json()
			licenseId.value = data.license_id || null
			customerName.value = data.customer_name || null
			expiryDate.value = data.expiry || null
			activeUsers.value = data.active_users || 0

			const features = data.features || {}
			maxMainDb.value = features.max_main_db || null
			maxConcurrentUsers.value = features.max_concurrent_users || null
			allowedMenus.value = features.allowed_menus || []
			configFlags.value = features.config_flags || {}
			loaded.value = true
		} catch {
			loaded.value = false
		}
	}

	function isMenuAllowed(menuName) {
		// If no menus specified in license, all menus are allowed
		if (!allowedMenus.value || allowedMenus.value.length === 0) return true
		return allowedMenus.value.includes(menuName)
	}

	function isConfigEnabled(flagName) {
		// If no flag specified, treat as enabled (not locked)
		if (!(flagName in configFlags.value)) return true
		return !!configFlags.value[flagName]
	}

	return {
		licenseId,
		customerName,
		expiryDate,
		maxMainDb,
		maxConcurrentUsers,
		activeUsers,
		allowedMenus,
		configFlags,
		loaded,
		fetchLicenseInfo,
		isMenuAllowed,
		isConfigEnabled,
	}
})
