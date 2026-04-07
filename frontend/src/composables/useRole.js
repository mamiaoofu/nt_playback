import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_INDEX_ROLE, API_DELETE_ROLE } from '../api/paths'
import { showToast, confirmDelete } from '../assets/js/function-all'
import { getCsrfToken } from '../api/csrf'

export function useRole() {
  const userPermissionOther = ref([])
  const authStore = useAuthStore()
  const loading = ref(true)
  const showBaseRoleModal = ref(false)
  const selectedBaseRoleId = ref(null)
  const selectedBaseRoleName = ref('')
  const selectedModalMode = ref('base')
  const searchQuery = ref('')

  const filteredRoles = computed(() => {
    const q = (searchQuery.value || '').toLowerCase().trim()
    if (!q) return userPermissionOther.value
    return userPermissionOther.value.filter(r => (r.name || '').toLowerCase().includes(q))
  })

  const fetchIndexRoles = async () => {
    const task = (async () => {
      loading.value = true
      try {
        const res = await fetch(API_INDEX_ROLE(), { credentials: 'include' })
        if (!res.ok) {
          console.error('Failed to fetch roles', res.status)
          return
        }
        const json = await res.json()
        userPermissionOther.value = Array.isArray(json.user_permission_other) ? json.user_permission_other : []
      } catch (e) {
        console.error('fetchIndexRoles error', e)
      }
      finally {
        loading.value = false
      }
    })()
    registerRequest(task)
    await task
  }

  function openEditRole(id, mode = 'base') {
    selectedBaseRoleId.value = id
    selectedModalMode.value = mode
    if (id === 1) selectedBaseRoleName.value = 'Edit Administrator'
    else if (id === 2) selectedBaseRoleName.value = 'Edit Auditor'
    else if (id === 3) selectedBaseRoleName.value = 'Edit Operator/Agent'
    else selectedBaseRoleName.value = 'Edit Role'
    showBaseRoleModal.value = true
  }

  function openCreateRole() {
    selectedBaseRoleId.value = null
    selectedBaseRoleName.value = 'Create New Role'
    selectedModalMode.value = 'create'
    showBaseRoleModal.value = true
  }

  async function deleteCustomRole(id) {
    try {
      if (!id) return
      const confirmed = await confirmDelete()
      if (!confirmed) return

      const csrfToken = getCsrfToken()
      const url = API_DELETE_ROLE(id)
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken || ''
        },
        body: JSON.stringify({ role_id: id })
      })
      const j = res.ok ? await res.json() : null
      if (res.ok && j && j.status === 'success') {
        showToast(j.message || 'Deleted successfully', 'success')
        try {
          const idx = (userPermissionOther.value || []).findIndex(r => String(r.id) === String(id))
          if (idx !== -1) userPermissionOther.value.splice(idx, 1)
        } catch (e) {
          console.warn('List removal failed', e)
        }
      } else {
        showToast((j && j.message) || 'Failed to delete role', 'error')
      }
    } catch (e) {
      console.error('deleteCustomRole error', e)
      showToast('Failed to delete role', 'error')
    }
  }

  function onRoleCreated(role) {
    try {
      if (!role || !role.id) return
      // Only add to custom roles list when creating a custom role
      if (selectedModalMode.value === 'create' || (role.type && role.type === 'role_other')) {
        userPermissionOther.value = [{ id: role.id, name: role.name, type: role.type || 'role_other' }].concat(userPermissionOther.value || [])
      }
    } catch (e) { console.error('onRoleCreated handler error', e) }
  }

  function onRoleUpdated(role) {
    try {
      if (!role || !role.id) return
      const idx = (userPermissionOther.value || []).findIndex(r => String(r.id) === String(role.id))
      if (idx !== -1) {
        const newList = [...userPermissionOther.value]
        const [item] = newList.splice(idx, 1)
        item.name = role.name
        newList.unshift(item)
        userPermissionOther.value = newList
      } else {
        // If this update isn't for an existing custom role, only add it
        // when it's a custom role (not a base role).
        if (selectedModalMode.value !== 'base' && (role.type ? role.type === 'role_other' : true)) {
          userPermissionOther.value = [{ id: role.id, name: role.name, type: role.type || 'role_other' }].concat(userPermissionOther.value || [])
        }
      }
    } catch (e) { console.error('onRoleUpdated handler error', e) }
  }

  onMounted(() => {
    fetchIndexRoles()
  })

  const state = {
    userPermissionOther,
    authStore,
    loading,
    showBaseRoleModal,
    selectedBaseRoleId,
    selectedBaseRoleName,
    selectedModalMode,
    searchQuery,
    filteredRoles
  }

  const actions = {
    fetchIndexRoles,
    openEditRole,
    openCreateRole,
    deleteCustomRole,
    onRoleCreated,
    onRoleUpdated
  }

  return {
    ...state,
    ...actions
  }
}