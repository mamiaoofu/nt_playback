import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useRouter } from 'vue-router'
import { showToast } from '../assets/js/function-all'
import { API_CHANGE_PASSWORD } from '../api/paths'
import { getCsrfToken } from '../api/csrf'

export function useLogin() {
  const router = useRouter()
  const authStore = useAuthStore()

  const passwordVisible = ref(false)
  const form = reactive({
    username: '',
    password: '',
    rememberMe: false
  })

  const handleLogin = async () => {
    const success = await authStore.login(form.username, form.password)
    if (success) {
      // persist or remove saved credentials based on rememberMe
      try {
        if (form.rememberMe) {
          localStorage.setItem('remember_credentials', JSON.stringify({ username: form.username, password: form.password }))
        } else {
          localStorage.removeItem('remember_credentials')
        }
      } catch (e) { }
      
      if (authStore.passwordResetRequired) {
        try { showToast('Please change your password for security.', 'warning') } catch (e) { }
      } else {
        try { showToast(`Welcome! ${authStore.user?.username || ''}`, 'success') } catch (e) { }
        router.push('/')
      }
    } else {
      try { showToast('Login failed. Please check your username and password.', 'error') } catch (e) { }
    }
  }

  // --- Password Force Reset logic ---
  const submitting = ref(false)
  const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
  const passwordError = ref('')
  const showOldPass = ref(false)
  const showNewPass = ref(false)
  const showConfirmPass = ref(false)
  const errors = reactive({ password: false, confirmPassword: false })

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
    if (passwordForm.confirm_password && String(passwordForm.confirm_password).trim() !== '') {
      if (val !== passwordForm.confirm_password) {
        errors.confirmPassword = 'Passwords do not match'
        passwordError.value = 'Passwords do not match'
      } else {
        errors.confirmPassword = false
        passwordError.value = ''
      }
    }
  })

  watch(() => passwordForm.confirm_password, (val) => {
    if (!val || String(val).trim() === '') { errors.confirmPassword = false; passwordError.value = ''; return }
    if (passwordForm.new_password !== val) {
      errors.confirmPassword = 'Passwords do not match'
      passwordError.value = 'Passwords do not match'
    } else {
      errors.confirmPassword = false
      passwordError.value = ''
    }
  })

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
        credentials: 'include',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken || '' 
        },
        body: JSON.stringify({
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password,
          confirm_password: passwordForm.confirm_password
        })
      })
      const json = await res.json()
      if (res.ok && json.status === 'success') {
        // Capture the new password before clearing the form
        const newPassword = passwordForm.new_password
        // Use username from authStore (persists across refresh) or form
        const username = authStore.user?.username || form.username
        
        // Clear the form
        passwordForm.old_password = ''
        passwordForm.new_password = ''
        passwordForm.confirm_password = ''
        
        // Re-login implicitly to get fresh tokens as backend invalidated the old ones
        const loginSuccess = await authStore.login(username, newPassword)
        if (loginSuccess && !authStore.passwordResetRequired) {
          showToast('Password changed successfully', 'success')
          router.push('/')
        } else {
          showToast('Failed to re-authenticate after password change', 'error')
        }
      } else {
        showToast(json.message || 'Failed to change password', 'error')
      }
    } catch (e) {
      console.error('Change password error', e)
      showToast('An error occurred', 'error')
    } finally { submitting.value = false }
  }

  onMounted(() => {
    try {
      const raw = localStorage.getItem('remember_credentials')
      if (raw) {
        const obj = JSON.parse(raw)
        if (obj && obj.username) form.username = obj.username
        if (obj && obj.password) form.password = obj.password
        form.rememberMe = true
      }
    } catch (e) { }
  })

  const state = {
    authStore,
    passwordVisible,
    form,
    submitting,
    passwordForm,
    passwordError,
    showOldPass,
    showNewPass,
    showConfirmPass,
    errors
  }

  const actions = {
    handleLogin,
    submitPasswordChange
  }

  return {
    ...state,
    ...actions
  }
}