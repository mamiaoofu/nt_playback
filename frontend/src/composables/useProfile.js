import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { API_GET_USER_PROFILE, API_CHANGE_PASSWORD } from '../api/paths'
import { getCsrfToken } from '../api/csrf'
import { showToast, notify } from '../assets/js/function-all'

export function useProfile() {
    const authStore = useAuthStore()
    const activeTab = ref('personal')
    const loading = ref(false)
    const submitting = ref(false)
    const userProfile = ref({})

    // Password form state
    const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
    const passwordError = ref('')
    const showOldPass = ref(false)
    const showNewPass = ref(false)
    const showConfirmPass = ref(false)

    // validation state
    const errors = reactive({ password: false, confirmPassword: false })
    const hasError = ref(false)

    // watch new password for length and update confirm match
    watch(() => passwordForm.new_password, (val) => {
        if (!val || String(val).trim() === '') {
            errors.password = false
        } else if (String(val).length < 8) {
            errors.password = 'Password must be at least 8 characters long'
        } else if (!/^[\x21-\x7E]+$/.test(String(val))) {
            errors.password = 'Password must contain only English letters and special characters'
        } else {
            errors.password = false
        }
        // also validate confirm when present
        if (passwordForm.confirm_password && String(passwordForm.confirm_password).trim() !== '') {
            if (val !== passwordForm.confirm_password) {
                errors.confirmPassword = 'Passwords do not match'
                passwordError.value = 'Passwords do not match'
            } else {
                errors.confirmPassword = false
                passwordError.value = ''
            }
        }
        hasError.value = !!(errors.password || errors.confirmPassword)
    })

    // watch confirm password for match
    watch(() => passwordForm.confirm_password, (val) => {
        if (!val || String(val).trim() === '') { errors.confirmPassword = false; passwordError.value = ''; hasError.value = !!errors.password; return }
        if (passwordForm.new_password !== val) {
            errors.confirmPassword = 'Passwords do not match'
            passwordError.value = 'Passwords do not match'
        } else {
            errors.confirmPassword = false
            passwordError.value = ''
        }
        hasError.value = !!(errors.password || errors.confirmPassword)
    })

    async function fetchProfile() {
        const userId = authStore.user?.id
        if (!userId) return
        loading.value = true
        try {
            const res = await fetch(API_GET_USER_PROFILE(userId), { credentials: 'include' })
            if (res.ok) {
                const json = await res.json()
                const up = json.user_profile || {}
                const u = up.user || {}
                const team = up.team || {}
                const group = team.user_group || {}
                const role = json.selected_role_type || 'User'
                const db_name = (up.team.maindatabase_name || []).join(', ');

                userProfile.value = {
                    username: u.username || '',
                    first_name: u.first_name || '',
                    last_name: u.last_name || '',
                    email: u.email || '',
                    phone: up.phone || '',
                    group_name: group.group_name || '',
                    team_name: team.name || '',
                    role: role,
                    db_name: db_name
                }
            }
        } catch (e) { console.error('Fetch profile error', e) } finally { loading.value = false }
    }

    async function submitPasswordChange() {
        passwordError.value = ''
        if (passwordForm.new_password !== passwordForm.confirm_password) {
            passwordError.value = 'New passwords do not match.'
            return
        }
        if (passwordForm.new_password.length < 8) {
            passwordError.value = 'Password must be at least 8 characters.'
            return
        }
        submitting.value = true
        try {
            const csrfToken = getCsrfToken()
            const res = await fetch(API_CHANGE_PASSWORD(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
                body: JSON.stringify({
                    old_password: passwordForm.old_password,
                    new_password: passwordForm.new_password,
                    confirm_password: passwordForm.confirm_password
                })
            })
            const json = await res.json()
            if (res.ok && json.status === 'success') {
                passwordForm.old_password = ''; passwordForm.new_password = ''; passwordForm.confirm_password = ''
                await notify('Password changed successfully', 'Please log in again with your new password', 'success')
                authStore.logout()
            } else {
                showToast(json.message || 'Failed to change password', 'error')
            }
        } catch (e) {
            console.error('Change password error', e)
            showToast('An error occurred', 'error')
        } finally { submitting.value = false }
    }

    onMounted(() => { fetchProfile() })

    const state = {
        authStore,
        activeTab,
        loading,
        submitting,
        userProfile,
        passwordForm,
        passwordError,
        showOldPass,
        showNewPass,
        showConfirmPass,
        errors,
        hasError
    }

    const actions = {
        fetchProfile,
        submitPasswordChange
    }

    return {
        ...state,
        ...actions
    }
}