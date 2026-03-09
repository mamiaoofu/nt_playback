import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_GET_USER_TICKET,API_FILE_SHARE_MANAGEMENT_CHANGE_STATUS, API_GEN_FORM_TICKET } from '../api/paths'
import { getCsrfToken } from '../api/csrf'
import { showToast } from '../assets/js/function-all'

export function useFileShareManagement() {
    const authStore = useAuthStore()
    const route = useRoute()

    const searchQuery = ref('')
    let searchTimeout = null
    let userFilterTimeout = null

    const exportOpen = ref(false)
    const exportWrap = ref(null)

    const perPageOptions = [50, 100, 500, 1000]
    const perPage = ref(50)
    const currentPage = ref(1)

    const filters = reactive({
        ticketID: [],
        full_name: [],
        action: [],
        createdBy: '',
        start_date: '',
        exprie_date: '',
        status: [],
        files_audio: []
    })

    const startInput = ref(null)
    const endInput = ref(null)
    const searchInputRef = ref(null)

    const perWrap = ref(null)
    const perDropdownOpen = ref(false)

    const records = ref([])
    const totalItems = ref(0)
    const loading = ref(false)
    const ticketOptions = ref([])
    const createdByOptions = ref([])
    // modal state for recent ticket resend
    const recentModalOpen = ref(false)
    const recentResultData = ref({})
    const recentResultType = ref('')
    
    const sortColumn = ref('')
    const sortDirection = ref('')

    const baseColumns = [
        { key: 'index', label: '#', isIndex: true },
        { key: 'code', label: 'Ticket ID' },
        { key: 'email', label: 'Email', tooltip: true, labelKey: 'email_label' },
        { key: 'create_by', label: 'Created By' },
        { key: 'start_date', label: 'Start Date' },
        { key: 'exprie_date', label: 'Exprie Date' },
        { key: 'files_audio', label: 'Files Audio', tooltip: true, labelKey: 'files_audio_label' },
        { key: 'status', label: 'Status' }
    ]

    const columns = computed(() => {
        const cols = [...baseColumns]
        if (typeUrl.value === 'ticket') cols.push({ key: 'action', label: 'Action' })
        return cols
    })

    const type = computed(() => 'ticket')
    const requiredPermission = computed(() => 'Ticket History')

    const canView = computed(() => authStore.hasPermission(requiredPermission.value))
    const totalPages = computed(() => Math.max(1, Math.ceil(totalItems.value / perPage.value)))
    const startIndex = computed(() => (currentPage.value - 1) * perPage.value)
    const paginatedRecords = computed(() => records.value)

    const fetchData = async () => {
        loading.value = true
        try {
            if (!canView.value) {
                loading.value = false
                records.value = []
                totalItems.value = 0
                return
            }
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

            if (filters.ticketID && filters.ticketID !== 'all' && Array.isArray(filters.ticketID) && filters.ticketID.length > 0) params.set('ticket_id', filters.ticketID.join(','))
            if (filters.full_name && filters.full_name !== 'all' && Array.isArray(filters.full_name) && filters.full_name.length > 0) params.set('full_name', filters.full_name.join(','))
            if (filters.action && filters.action !== 'all' && Array.isArray(filters.action) && filters.action.length > 0) params.set('action', filters.action.join(','))
            if (filters.createdBy) params.set('create_by', filters.createdBy)
            if (filters.start_date) params.set('start_date', filters.start_date)
            if (filters.exprie_date) params.set('end_date', filters.exprie_date)
            if (filters.status && filters.status !== 'all' && Array.isArray(filters.status) && filters.status.length > 0) params.set('status', filters.status.join(','))
            if (filters.files_audio && filters.files_audio !== 'all' && Array.isArray(filters.files_audio) && filters.files_audio.length > 0) params.set('files_audio', filters.files_audio.join(','))

            const res = await fetch(`${API_GET_USER_TICKET(typeUrl.value)}?${params.toString()}`, { credentials: 'include' })
            if (!res.ok) throw new Error('Failed to fetch')
            const json = await res.json()
            records.value = json.data || json.user_management || []
            // normalize tooltip & label for files and email
            try {
                if (Array.isArray(records.value)) {
                    records.value = records.value.map(r => {
                        const out = { ...r }

                        // Files audio: backend returns comma-separated names or may be empty
                        const rawFiles = (r.files_audio || '')
                        let fileList = []
                        if (Array.isArray(rawFiles)) fileList = rawFiles
                        else if (typeof rawFiles === 'string') {
                            // split by comma, then trim
                            fileList = rawFiles.split(',').map(s => s.trim()).filter(Boolean)
                        }
                        const fcount = fileList.length
                        if (fcount === 0 && rawFiles && typeof rawFiles === 'object') {
                            // fallback if server returned object-like
                            try { fileList = JSON.parse(String(rawFiles)) } catch (e) { }
                        }
                        const filesTooltip = fcount > 1 ? ('File name:\n' + fileList.map(x => `- ${x}`).join('\n')) : (fileList[0] || '')
                        out.files_audio = filesTooltip
                        out.files_audio_label = `Files Audio (${fcount})`

                        // Email: may be stored like {"a","b"} or comma-separated
                        const rawEmail = r.email || ''
                        let emailList = []
                        if (Array.isArray(rawEmail)) emailList = rawEmail
                        else if (typeof rawEmail === 'string') {
                            // remove surrounding braces and quotes then split
                            const cleaned = rawEmail.replace(/[{}"]+/g, '')
                            emailList = cleaned.split(/[,;\n\r]+/).map(s => s.trim()).filter(Boolean)
                        }
                        const ecount = emailList.length
                        const emailTooltip = ecount > 1 ? ('Email:\n' + emailList.map(x => `- ${x}`).join('\n')) : (emailList[0] || rawEmail || '')
                        out.email = emailTooltip
                        out.email_label = ecount >= 1 ? `Email (${ecount})` : '-'

                        return out
                    })
                }
            } catch (e) { console.error('normalize tooltip error', e) }

            // Build ticketOptions and createdByOptions from returned records
            try {
                const ticketSet = new Set()
                const creatorSet = new Set()
                const tOpts = [{ label: 'All Tickets', value: 'all' }]
                const cOpts = [{ label: 'All Create', value: 'all' }]
                if (Array.isArray(records.value)) {
                    for (const r of records.value) {
                        const code = r.code || r.id || ''
                        if (code && !ticketSet.has(code)) {
                            ticketSet.add(code)
                            tOpts.push({ label: String(code), value: code })
                        }

                        const creatorRaw = r.create_by || r.create_by || ''
                        let creatorVal = ''
                        if (creatorRaw && typeof creatorRaw === 'object') {
                            creatorVal = creatorRaw.username || `${creatorRaw.first_name || ''} ${creatorRaw.last_name || ''}`.trim() || JSON.stringify(creatorRaw)
                        } else {
                            creatorVal = String(creatorRaw || '')
                        }
                        if (creatorVal && !creatorSet.has(creatorVal)) {
                            creatorSet.add(creatorVal)
                            cOpts.push({ label: creatorVal, value: creatorVal })
                        }
                    }
                }
                ticketOptions.value = tOpts
                createdByOptions.value = cOpts
            } catch (e) {
                console.error('build options error', e)
            }
            totalItems.value = json.recordsFiltered ?? json.recordsTotal ?? (Array.isArray(records.value) ? records.value.length : 0)
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
        if (perWrap.value && !perWrap.value.contains(e.target)) perDropdownOpen.value = false
        if (exportWrap.value && !exportWrap.value.contains(e.target)) exportOpen.value = false
    }

    const clearSearchQuery = () => {
        searchQuery.value = ''
        if (searchTimeout) { clearTimeout(searchTimeout); searchTimeout = null }
        currentPage.value = 1
        fetchData()
        nextTick(() => {
            if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') searchInputRef.value.focus()
        })
    }

    const resetFilters = () => {
        try {
            filters.ticketID = []
            filters.full_name = []
            filters.action = []
            filters.createdBy = ''
            filters.start_date = ''
            filters.exprie_date = ''
            filters.status = []
            filters.files_audio = []

            if (startInput.value && startInput.value._flatpickrInstance) {
                startInput.value._flatpickrInstance.clear()
            }
            if (endInput.value && endInput.value._flatpickrInstance) {
                endInput.value._flatpickrInstance.clear()
            }

            currentPage.value = 1
            fetchData()
        } catch (e) {
            console.error('resetFilters error', e)
        }
    }
    
    const toggleExport = () => {
        exportOpen.value = !exportOpen.value
    }
    
    const onSortChange = ({ column, direction }) => {
        sortColumn.value = column
        sortDirection.value = direction
        fetchData()
    }
    
    const onRowDelete = (row) => {
        console.log('Delete row', row)
    }

    watch(filters, () => {
        if (userFilterTimeout) clearTimeout(userFilterTimeout)
        userFilterTimeout = setTimeout(() => {
            currentPage.value = 1
            fetchData()
            userFilterTimeout = null
        }, 350)
    }, { deep: true })

    onMounted(() => {
        registerRequest(fetchData())
        document.addEventListener('click', onDocClick)
    })

    onBeforeUnmount(() => {
        document.removeEventListener('click', onDocClick)
    })

    const typeUrl = computed(() => {
        const p = route.path || ''
        if (p === '/ticket-management') return 'ticket'
        if (p === '/delegate-management') return 'delegate'
        return 'type_url_not_found'
    })
    

    async function toggleUserStatus(userId, fileShareId) {
        if (!authStore.hasPermission('Change Status')) return showToast('Access Denied', 'error')
        // Prefer locating the record by fileShareId (row.id) to avoid matching
        // other rows that share the same user_id (common for delegate rows).
        let rec = null
        if (fileShareId) {
            rec = records.value.find(r => r && (String(r.id) === String(fileShareId)))
        }
        // fallback: try to find by userId if fileShareId not provided or not found
        if (!rec && userId) {
            rec = records.value.find(r => {
                if (!r) return false
                if (r.user_id && String(r.user_id) === String(userId)) return true
                if (r.id && String(r.id) === String(userId)) return true
                if (r.user && (r.user.id && String(r.user.id) === String(userId) || r.user.user_id && String(r.user.user_id) === String(userId))) return true
                return false
            })
        }
        if (!rec) return
        const current = !!rec.status
        rec.status = !current
        try {
            const csrfToken = getCsrfToken()
            const body = new URLSearchParams({ user_file_id: String(fileShareId || '') })
            const res = await fetch(API_FILE_SHARE_MANAGEMENT_CHANGE_STATUS(userId, typeUrl.value), {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': csrfToken || '',
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: body.toString()
            })
            const json = await res.json()
            if (!res.ok || json.status === 'error') {
                rec.status = current
                console.error('change status failed', json)
            } else {
                showToast(json.message, 'success')
            }
        } catch (e) {
            rec.status = current
            console.error('toggleUserStatus fetch error', e)
        }
    }

    async function resendTicket(user_file_id, user_id) {
        if (!authStore.hasPermission('Ticket History')) return showToast('Access Denied', 'error')
        try {
            const csrfToken = getCsrfToken()
            const body = new URLSearchParams({ user_file_id: String(user_file_id || ''), user_id: String(user_id || '') })
            const res = await fetch(API_GEN_FORM_TICKET(), {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': csrfToken || '',
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: body.toString()
            })
            const json = await res.json()
            if (!res.ok || json.status === 'error') {
                showToast(json.message || 'Failed to generate ticket', 'error')
                console.error('resendTicket failed', json)
                return
            }
            // expected: { code, password, start_at, expire_at }
            recentResultData.value = json
            recentResultType.value = 'ticket'
            recentModalOpen.value = true
        } catch (e) {
            console.error('resendTicket error', e)
            showToast('Failed to generate ticket', 'error')
        }
    }

    const state = {
        authStore,
        recentModalOpen,
        recentResultData,
        recentResultType,
        searchQuery,
        exportOpen,
        exportWrap,
        perPageOptions,
        perPage,
        currentPage,
        filters,
        ticketOptions,
        createdByOptions,
        startInput,
        endInput,
        searchInputRef,
        perWrap,
        perDropdownOpen,
        records,
        totalItems,
        loading,
        columns,
        requiredPermission,
        canView,
        totalPages,
        startIndex,
        paginatedRecords,
        type,
        sortColumn,
        sortDirection,
        typeUrl
    }

    const actions = {
        onTyping,
        resendTicket,
        setPerPage,
        changePage,
        clearSearchQuery,
        resetFilters,
        fetchData,
        toggleExport,
        onSortChange,
        onRowDelete,
        toggleUserStatus
    }

    return {
        ...state,
        ...actions
    }
}
