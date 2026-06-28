import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Role from '../views/Role.vue'
import { useAuthStore } from '../stores/auth.store'
import { PERMISSIONS } from '../stores/permissions.constants'
import { ensureCsrf } from '../api/csrf'

const routes = [
	{ path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
	{ path: '/', name: 'Home', component: Home, meta: { permission: PERMISSIONS.AUDIO_RECORDS_ACCESS } },
	{ path: '/user-management', name: 'UserManagement', component: () => import('../views/UserManagement.vue'), meta: { permission: PERMISSIONS.USER_MANAGEMENT_ACCESS } },
	{ path: '/configuration/role', name: 'role', component: Role },
	{ path: '/configuration/role', name: 'role', component: Role, meta: { permission: PERMISSIONS.ROLE_PERMISSIONS_ACCESS } },
	{ path: '/configuration/group', name: 'Group', component: () => import('../views/GroupAndTeam.vue'), meta: { permission: PERMISSIONS.GROUP_TEAM_ACCESS } },
	{ path: '/configuration/users', name: 'Users', component: () => import('../views/Users.vue') },
	{ path: '/user-management/add', name: 'AddUser', component: () => import('../views/AddUser.vue'), meta: { permission: PERMISSIONS.ADD_USER } },
	{ path: '/user-management/edit/:id', name: 'EditUser', component: () => import('../views/EditUser.vue'), meta: { permission: PERMISSIONS.EDIT_USER } },
	{ path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { permission: PERMISSIONS.USER_PROFILE_ACCESS } },
	{ path: '/system-tool/system-log', name: 'SystemLogs', component: () => import('../views/UserLog.vue'), meta: { permission: PERMISSIONS.SYSTEM_LOG_ACCESS } },
	{ path: '/logs/audit', name: 'AuditLogs', component: () => import('../views/UserLog.vue'), meta: { permission: PERMISSIONS.AUDIT_LOG_ACCESS } },
	{ path: '/setting/column/audio-record', name: 'SettingColumnAudioRecord', component: () => import('../views/SetColumnAudioRecord.vue') },
	{ path: '/logs/ticket-history', name: 'TicketHistory', component: () => import('../views/TicketHistory.vue'), meta: { permission: PERMISSIONS.TICKET_HISTORY_ACCESS } },
	{ path: '/ticket-management', name: 'TicketManagement', component: () => import('../views/FileShareManagement.vue'), meta: { permission: PERMISSIONS.TICKET_MANAGEMENT_ACCESS } },
	{ path: '/delegate-management', name: 'DelegateManagement', component: () => import('../views/FileShareManagement.vue'), meta: { permission: PERMISSIONS.DELEGATE_MANAGEMENT_ACCESS } },
	{ path: '/system-tool/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
	{ path: '/system-tool/active-directory', name: 'ActiveDirectoryConfig', component: () => import('../views/ActiveDirectoryConfig.vue') },
	{ path: '/system-tool/network-share', name: 'NetworkShareConfig', component: () => import('../views/NetworkShareConfig.vue') },
	{ path: '/system-tool/mail-settings', name: 'MailSettingsConfig', component: () => import('../views/MailSettingsConfig.vue') },
	{ path: '/system-tool/retention', name: 'RetentionConfig', component: () => import('../views/RetentionConfig.vue') },
	// { path: '/system-tool/nice-player', name: 'NicePlayerConfig', component: () => import('../views/NicePlayerConfig.vue') },
	{ path: '/system-tool/data-retention/create', name: 'CreateRetention', component: () => import('../views/DataRetention/CreateRetention.vue') },
	{ path: '/system-tool/data-retention/tasks', redirect: '/system-tool/data-retention/create' },
	{ path: '/system-tool/data-retention/logs', name: 'LogRetention', component: () => import('../views/DataRetention/LogRetention.vue') },
    { path: '/denied', name: 'Denied', component: () => import('../views/Denied.vue') },
	{ path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFound.vue') },
]

const router = createRouter({
	history: createWebHistory(),
	routes,
})

router.beforeEach(async (to, from, next) => {
	const authStore = useAuthStore()

	// Wait for the initial restore-from-cookie attempt to finish so that a page
	// reload doesn't falsely redirect to Login before the token is recovered.
	try { await authStore.waitReady() } catch (e) {}

	// If password reset is required, force user to stay on login page to change password
	if (authStore.passwordResetRequired && to.name !== 'Login') {
		return next({ name: 'Login' })
	}

	const isAuthenticated = !!authStore.token

	if (to.name !== 'Login' && !isAuthenticated) {
		return next({ name: 'Login' })
	}
	if (to.name === 'Login' && isAuthenticated) {
		if (!authStore.passwordResetRequired) {
			if (authStore.user?.is_superuser) {
				return next({ name: 'Dashboard' })
			}
			return next({ name: 'Home' })
		}
	}

	if (to.name === 'Dashboard' && !authStore.user?.is_superuser) {
		return next({ name: 'Denied' })
	}

	if (to.name === 'Profile' && authStore.isTicket && authStore.isTicket()) {
		return next({ name: 'Home' })
	}

	// If authenticated, ensure the store has at least the user ID and permissions 
	// (critical for pages like Profile or those with permission requirements)
	if (isAuthenticated) {
		const needsPermissions = to.meta && to.meta.permission
		const missingUserId = !authStore.user?.id
		const missingPermissions = !authStore.permissions || authStore.permissions.length === 0

		console.log('RouterGuard: Route:', to.name, 'needsPermissions:', needsPermissions, 'missingUserId:', missingUserId, 'missingPermissions:', missingPermissions)

		if (missingUserId || (needsPermissions && missingPermissions)) {
			try {
				console.log('RouterGuard: fetching permissions...')
				await authStore.fetchPermissions()
				console.log('RouterGuard: fetched user:', authStore.user, 'permissions:', authStore.permissions)
			} catch (e) {
				console.error('Failed to load user info/permissions in router:', e)
			}
		}

		if (needsPermissions && !authStore.hasPermission(needsPermissions)) {
			const allowHomeByDelegateFiles =
				to.name === 'Home' &&
				needsPermissions === PERMISSIONS.AUDIO_RECORDS_ACCESS &&
				authStore.hasPermission(PERMISSIONS.DELEGATE_FILES)

			console.log('RouterGuard: access check failed. allowHomeByDelegateFiles:', allowHomeByDelegateFiles)

			if (!allowHomeByDelegateFiles) {
				console.log('RouterGuard: redirecting to Denied')
				return next({ name: 'Denied' })
			}
		}
	}

	return next()
})

export default router
