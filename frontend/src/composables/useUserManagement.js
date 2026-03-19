import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_GET_USER, API_USER_MANAGEMENT_CHANGE_STATUS, API_DELETE_USER, API_RESET_PASSWORD } from '../api/paths'
import { showToast, confirmDelete, notify } from '../assets/js/function-all'
import { getCsrfToken } from '../api/csrf'

export function useUserManagement() {
    const router = useRouter()
    const authStore = useAuthStore()

    const searchQuery = ref('')
    const searchInputRef = ref(null)
    let searchTimeout = null

    // dropdown state used by the table per-page control
    const perWrap = ref(null)
    const perDropdownOpen = ref(false)

    const perPageOptions = [50, 100, 500, 1000]
    const perPage = ref(50)
    const currentPage = ref(1)
    const records = ref([])
    const totalItems = ref(0)
    const loading = ref(false)

    const sortColumn = ref('')
    const sortDirection = ref('')

    const expanded = ref(new Set())

    // tooltip state for database servers
    const dbTooltip = ref({ visible: false, items: [], style: null })
    const dbTooltipEl = ref(null)
    const dbTooltipPlacement = ref('top')
    let dbHideTimer = null
    const dbActiveEl = ref(null)

    const columns = [
        { key: 'index', label: '#', isIndex: true, sortable: false },
        { key: 'username', label: 'Username' },
        { key: 'full_name', label: 'Full Name' },
        { key: 'email', label: 'Email' },
        { key: 'role', label: 'Role' },
        { key: 'group', label: 'Group' },
        { key: 'team', label: 'Team' },
        { key: 'database_servers', label: 'Database Server' },
        { key: 'phone', label: 'Phone' },
        { key: 'status', label: 'Status' },
        { key: 'actions', label: 'Actions', isAction: true }
    ]

    const totalPages = computed(() => Math.max(1, Math.ceil(totalItems.value / perPage.value)))
    const startIndex = computed(() => (currentPage.value - 1) * perPage.value)
    const paginatedRecords = computed(() => records.value)

    const fetchData = async () => {
        loading.value = true
        try {
            const start = (currentPage.value - 1) * perPage.value
            const params = new URLSearchParams()
            params.set('draw', 1)
            params.set('start', start)
            params.set('length', perPage.value)
            params.set('search[value]', searchQuery.value || '')

            if (sortColumn.value && sortDirection.value) {
                params.set('sort[0][field]', sortColumn.value)
                params.set('sort[0][dir]', sortDirection.value)
            }

            const res = await fetch(`${API_GET_USER()}?${params.toString()}`, { credentials: 'include' })
            if (!res.ok) throw new Error('Failed to fetch')
            const json = await res.json()
            records.value = json.data || json.user_management || []
            totalItems.value = json.recordsFiltered ?? json.recordsTotal ?? (Array.isArray(records.value) ? records.value.length : 0)
            
            // If there's a pending user transferred from create/edit, promote or insert it
            try {
                const pu = (typeof window !== 'undefined' && window.__pending_user_for_user_management) || null
                if (pu) {
                    try {
                        const findIdx = (records.value || []).findIndex(r => {
                            const rid = r && r.user && r.user.id
                            const rname = r && (r.user ? r.user.username : r.username)
                            if (pu.id && rid) return String(rid) === String(pu.id)
                            return String(rname || '').toLowerCase() === String(pu.username || '').toLowerCase()
                        })
                        let entry = null
                        if (findIdx !== -1) {
                            entry = records.value.splice(findIdx, 1)[0]
                        } else {
                            entry = {
                                id: pu.id || null,
                                user: {
                                    id: pu.id || null,
                                    username: pu.username || '',
                                    first_name: pu.first_name || '',
                                    last_name: pu.last_name || '',
                                    email: pu.email || ''
                                },
                                team: null,
                                user_code: '',
                                phone: '',
                                create_at: null,
                                update_at: null,
                                is_active: true,
                                permission: pu.permission || '-',
                                database_servers: pu.database_servers || []
                            }
                            if (pu.mode === 'add' && typeof totalItems.value === 'number') totalItems.value = totalItems.value + 1
                        }
                        records.value = [entry].concat(records.value || [])
                    } catch (e) { console.error('apply pending user error', e) }
                    try { delete window.__pending_user_for_user_management } catch (e) {}
                }
            } catch (e) { console.error('pending user apply top-level error', e) }
        } catch (e) {
            console.error('fetchData error', e)
        } finally {
            loading.value = false
        }
    }

    const onTyping = () => {
        currentPage.value = 1
        if (searchTimeout) clearTimeout(searchTimeout)
        searchTimeout = setTimeout(() => {
            fetchData()
            searchTimeout = null
        }, 450)
    }

    function onSearch() {
        currentPage.value = 1
        if (searchTimeout) { clearTimeout(searchTimeout); searchTimeout = null }
        fetchData()
    }

    function clearSearchQuery() {
        searchQuery.value = ''
        sortColumn.value = ''
        sortDirection.value = ''
        if (searchTimeout) { clearTimeout(searchTimeout); searchTimeout = null }
        currentPage.value = 1
        fetchData()
        nextTick(() => {
            if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') searchInputRef.value.focus()
        })
    }

    const onSortChange = ({ column, direction }) => {
        sortColumn.value = column
        sortDirection.value = direction
        fetchData()
    }

    const setPerPage = (opt) => {
        perPage.value = opt
        perDropdownOpen.value = false
    }

    const changePage = async (p) => {
        if (p < 1) p = 1
        if (p > totalPages.value) p = totalPages.value
        currentPage.value = p
        await fetchData()
    }

    const onDocClick = (e) => {
        if (!perWrap.value) return
        if (!perWrap.value.contains(e.target)) perDropdownOpen.value = false
    }

    const onRowEdit = (row, actionId) => {
        const id = actionId ?? (row && row.user && row.user.id)
        if (!id) return
        if (!authStore.hasPermission('Edit User')) return router.push({ name: 'Denied' })
        router.push(`/user-management/edit/${id}`)
    }

    const onRowDelete = async (row, actionId) => {
        try {
            const userId = actionId ?? (row && row.user && row.user.id)
            if (!userId) return
            if (!authStore.hasPermission('Delete User')) return showToast('Access Denied', 'error')

            const confirmed = await confirmDelete('Are you sure?', "You won't be able to revert this!", 'Yes, delete')
            if (!confirmed) return

            const csrfToken = getCsrfToken()
            const res = await fetch(API_DELETE_USER(userId), {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
                body: JSON.stringify({ user_id: userId })
            })
            const j = res.ok ? await res.json() : null
            if (res.ok && j && (j.status === 'success' || j.status === 'ok')) {
                showToast(j.message || 'Deleted successfully', 'success')
                const idx = (records.value || []).findIndex(r => {
                    const id = r && r.user && r.user.id
                    return String(id) === String(userId) || String(r.id) === String(userId)
                })
                if (idx !== -1) records.value.splice(idx, 1)
                if (typeof totalItems.value === 'number' && totalItems.value > 0) totalItems.value = Math.max(0, totalItems.value - 1)
            } else {
                showToast((j && j.message) || 'Failed to delete user', 'error')
            }
        } catch (e) {
            console.error('onRowDelete error', e)
            showToast('Failed to delete user', 'error')
        }
    }

    const onRowReset = async (row, actionId) => {
        try {
            const userId = actionId ?? (row && row.user && row.user.id)
            if (!userId) return
            if (!authStore.hasPermission('Delete User')) return showToast('Access Denied', 'error')

            const confirmed = await confirmDelete('Are you sure?', "You won't be able to revert this!", 'Yes, reset')
            if (!confirmed) return

            const csrfToken = getCsrfToken()
            const res = await fetch(API_RESET_PASSWORD(userId), {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
                body: JSON.stringify({ user_id: userId })
            })
            const j = res.ok ? await res.json() : null
            if (res.ok && j && (j.status === 'success' || j.status === 'ok')) {
                notify('Success!', j.message)
            } else {
                showToast((j && j.message) || 'Failed to reset user', 'error')
            }
        } catch (e) {
            console.error('onRowReset error', e)
            showToast('Failed to reset user', 'error')
        }
    }

    function extractGroup(row) {
        if (!row) return ''
        if (Array.isArray(row.team) && row.team.length) {
            const t = row.team[0]
            return (t && ((t.user_group && (t.user_group.group_name || t.user_group)) || t.user_group)) || ''
        }
        if (row.team && row.team.user_group) return row.team.user_group.group_name || row.team.user_group || ''
        if (row.group_team && typeof row.group_team === 'string') {
            const first = row.group_team.split(',').map(s => s.trim()).filter(Boolean)[0] || ''
            if (!first) return ''
            if (first.includes(' / ')) return first.split(' / ')[0].trim()
            return ''
        }
        return ''
    }

    function extractTeam(row) {
        if (!row) return ''
        if (Array.isArray(row.team) && row.team.length) {
            const t = row.team[0]
            return (t && (t.name || t.team_name)) || ''
        }
        if (row.team && (row.team.name || row.team.team_name)) return row.team.name || row.team.team_name || ''
        if (row.group_team && typeof row.group_team === 'string') {
            const first = row.group_team.split(',').map(s => s.trim()).filter(Boolean)[0] || ''
            if (!first) return ''
            if (first.includes(' / ')) return first.split(' / ')[1]?.trim() || ''
            return first
        }
        return ''
    }

    function getDbList(row) {
        if (!row) return []
        if (Array.isArray(row.database_servers)) return row.database_servers
        if (!row.database_servers) return []
        if (typeof row.database_servers === 'string') {
            if (row.database_servers === 'ALL') return ['ALL']
            return row.database_servers.split(',').map(s => s.trim()).filter(Boolean)
        }
        return []
    }

    async function toggleUserStatus(userId, row) {
        if (!authStore.hasPermission('Change Status')) return showToast('Access Denied', 'error')
        if (!userId) return
        const rec = records.value.find(r => (r.user && r.user.id) === userId)
        if (!rec) return
        const current = !!rec.user.is_active
        rec.user.is_active = !current
        try {
            const csrfToken = getCsrfToken()
            const res = await fetch(API_USER_MANAGEMENT_CHANGE_STATUS(userId), {
                method: 'POST',
                credentials: 'include',
                headers: { 'X-CSRFToken': csrfToken || '', 'Accept': 'application/json' }
            })
            const json = await res.json()
            if (!res.ok || json.status === 'error') {
                rec.user.is_active = current
                console.error('change status failed', json)
            } else {
                showToast(json.message, 'success')
            }
        } catch (e) {
            rec.user.is_active = current
            console.error('toggleUserStatus fetch error', e)
        }
    }

    function showDbTooltip(e, row) {
        try {
            const items = getDbList(row)
            if (!items || items.length === 0) return
            if (dbHideTimer) { clearTimeout(dbHideTimer); dbHideTimer = null }
            try {
                const currentTarget = e.currentTarget
                if (dbActiveEl.value && dbActiveEl.value !== currentTarget) dbActiveEl.value.classList.remove('is-active-tooltip')
                dbActiveEl.value = currentTarget
                if (dbActiveEl.value && dbActiveEl.value.classList) dbActiveEl.value.classList.add('is-active-tooltip')
            } catch (err) { }
            dbTooltip.value.items = items
            dbTooltip.value.visible = true
            const rect = e.currentTarget.getBoundingClientRect()
            nextTick(() => {
                try {
                    const el = dbTooltipEl.value
                    if (!el) return
                    const tRect = el.getBoundingClientRect()
                    const spaceAbove = rect.top
                    const left = rect.left + rect.width / 2
                    let top
                    let transform
                    if (spaceAbove > tRect.height + 8) {
                        top = rect.top - 8
                        transform = 'translate(-50%, -100%)'
                        dbTooltipPlacement.value = 'top'
                    } else {
                        top = rect.bottom + 8
                        transform = 'translate(-50%, 0)'
                        dbTooltipPlacement.value = 'bottom'
                    }
                    dbTooltip.value.style = { position: 'fixed', left: `${left}px`, top: `${top}px`, transform, zIndex: 9999, maxWidth: '420px', whiteSpace: 'normal' }
                } catch (err) { console.error('db tooltip pos err', err) }
            })
        } catch (e) { console.error('showDbTooltip error', e) }
    }

    function hideDbTooltip() {
        if (dbHideTimer) clearTimeout(dbHideTimer)
        dbHideTimer = setTimeout(() => {
            dbTooltip.value.visible = false
            dbTooltip.value.items = []
            dbTooltip.value.style = null
            try { if (dbActiveEl.value && dbActiveEl.value.classList) dbActiveEl.value.classList.remove('is-active-tooltip') } catch (err) { }
            dbActiveEl.value = null
            dbHideTimer = null
        }, 120)
    }

    function cancelHideDb() { if (dbHideTimer) { clearTimeout(dbHideTimer); dbHideTimer = null } }

    function openCreateGroup() {}

    onMounted(() => {
        registerRequest(fetchData())
        try {
            const raw = localStorage.getItem('pending_toast')
            if (raw) {
                try {
                    const t = JSON.parse(raw)
                    if (t && t.message) showToast(t.message, t.type || 'success')
                } catch (e) { }
                try { localStorage.removeItem('pending_toast') } catch (e) {}
            }
        } catch (e) { }

        try {
            const rawUser = localStorage.getItem('pending_user')
            if (rawUser) {
                try {
                    const pu = JSON.parse(rawUser)
                    try { window.__pending_user_for_user_management = pu } catch (e) { }
                } catch (e) { }
                try { localStorage.removeItem('pending_user') } catch (e) {}
            }
        } catch (e) { }
        document.addEventListener('click', onDocClick)
    })

    onBeforeUnmount(() => {
        document.removeEventListener('click', onDocClick)
    })

    const state = {
        authStore,
        searchQuery,
        searchInputRef,
        perWrap,
        perDropdownOpen,
        perPageOptions,
        perPage,
        currentPage,
        records,
        totalItems,
        loading,
        sortColumn,
        sortDirection,
        expanded,
        dbTooltip,
        dbTooltipEl,
        dbTooltipPlacement,
        columns,
        totalPages,
        startIndex,
        paginatedRecords
    }

    const actions = {
        onTyping,
        onSearch,
        clearSearchQuery,
        onSortChange,
        setPerPage,
        changePage,
        onRowEdit,
        onRowDelete,
        onRowReset,
        extractGroup,
        extractTeam,
        getDbList,
        toggleUserStatus,
        showDbTooltip,
        hideDbTooltip,
        cancelHideDb,
        openCreateGroup
    }

    return {
        ...state,
        ...actions
    }
}