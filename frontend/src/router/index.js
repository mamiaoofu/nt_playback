import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Role from '../views/Role.vue'
import { useAuthStore } from '../stores/auth.store'
import { ensureCsrf } from '../api/csrf'

const routes = [
	{ path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
	{ path: '/', name: 'Home', component: Home, meta: { permission: 'Audio Recording' } },
	{ path: '/user-management', name: 'UserManagement', component: () => import('../views/UserManagement.vue'), meta: { permission: 'User Management' } },
	{ path: '/configuration/role', name: 'role', component: Role },
	{ path: '/configuration/role', name: 'role', component: Role, meta: { permission: 'Access Role & Permissions' } },
	{ path: '/configuration/group', name: 'Group', component: () => import('../views/GroupAndTeam.vue'), meta: { permission: 'Access Group & Team' } },
	{ path: '/configuration/users', name: 'Users', component: () => import('../views/Users.vue') },
	{ path: '/user-management/add', name: 'AddUser', component: () => import('../views/AddUser.vue'), meta: { permission: 'Add User' } },
	{ path: '/user-management/edit/:id', name: 'EditUser', component: () => import('../views/EditUser.vue'), meta: { permission: 'Edit User' } },
	{ path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue') },
	{ path: '/logs/system', name: 'SystemLogs', component: () => import('../views/UserLog.vue'), meta: { permission: 'System Logs' } },
	{ path: '/logs/audit', name: 'AuditLogs', component: () => import('../views/UserLog.vue'), meta: { permission: 'Audit Logs' } },
	{ path: '/setting/column/audio-record', name: 'SettingColumnAudioRecord', component: () => import('../views/SetColumnAudioRecord.vue') },
	{ path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue') },
	{ path: '/ticket-history', name: 'TicketHistory', component: () => import('../views/TicketHistory.vue'), meta: { permission: 'Ticket History' } },
	{ path: '/ticket-management', name: 'TicketManagement', component: () => import('../views/FileShareManagement.vue'), meta: { permission: 'File Share Management' } },
	{ path: '/delegate-management', name: 'DelegateManagement', component: () => import('../views/FileShareManagement.vue'), meta: { permission: 'File Share Management' } },



    { path: '/denied', name: 'Denied', component: () => import('../views/Denied.vue') },
	{ path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFound.vue') },

]

const router = createRouter({
	history: createWebHistory(),
	routes,
})

router.beforeEach(async (to, from, next) => {
	const authStore = useAuthStore()
	const isAuthenticated = !!authStore.token

	if (to.name !== 'Login' && !isAuthenticated) {
		return next({ name: 'Login' })
	}
	if (to.name === 'Login' && isAuthenticated) {
		return next({ name: 'Home' })
	}

	// Ensure CSRF token is present for authenticated users on every navigation/refresh
	if (isAuthenticated) {
		// CSRF is fetched at app startup or after login and cached; no-op here
	}

	const required = to.meta && to.meta.permission
	if (required) {
		// ensure permissions are fetched (in case page reload)
		if (!authStore.permissions || authStore.permissions.length === 0) {
			try { await authStore.fetchPermissions() } catch (e) { /* ignore */ }
		}
		if (!authStore.hasPermission(required)) {
			return next({ name: 'Denied' })
		}
	}

	return next()
})

export default router
