import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useAuthStore } from './stores/auth.store.js'
import App from './App.vue'
import router from './router'
import { loadRuntimeConfig } from './api/runtimeConfig'
import { ensureCsrf } from './api/csrf'

//JS
import './assets/js/flatpickr.min.js'
import './assets/js/jquery-3.6.0.min.js'

import flatpickrDirective from './directives/flatpickr.js'
import flatrangepickrDirective from './directives/flatrangepickr.js'
import hasValueDirective from './directives/hasValue.js'
import numberOnlyDirective from './directives/numberOnly.js'

// css
import './assets/css/base.css'
import './assets/css/bootstrap.min.css'
import './assets/css/components.css'
import './assets/css/all.min.css'
import './assets/css/flatpickr.min.css'
import './assets/css/datatable.css'




;(async () => {
	await loadRuntimeConfig()
	const app = createApp(App)
	const pinia = createPinia()
	app.use(pinia)
	app.use(router)
	app.directive('flatpickr', flatpickrDirective)
	app.directive('flatrangepickr', flatrangepickrDirective)
	app.directive('has-value', hasValueDirective)
	app.directive('number-only', numberOnlyDirective)
	// fetch permissions on startup if user present
	try {
		const auth = useAuthStore()
		if (auth.user) await auth.fetchPermissions()
	} catch (e) {
		console.error('Error fetching permissions on startup', e)
	}

	// ensure CSRF token is available for subsequent POST requests
	try {
		await ensureCsrf()
	} catch (e) {
		console.warn('ensureCsrf failed on startup', e)
	}

	app.mount('#app')
})()