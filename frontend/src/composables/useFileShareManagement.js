import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_GET_USER_TICKET,API_FILE_SHARE_MANAGEMENT_CHANGE_STATUS, API_GEN_FORM_TICKET } from '../api/paths'
import { getCsrfToken } from '../api/csrf'
import { showToast } from '../assets/js/function-all'
import { exportTableToFormat } from '../assets/js/function-all'

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
        { key: 'create_at', label: 'Created Date' },
        { key: 'start_date', label: 'Start Date' },
        { key: 'exprie_date', label: 'Exprie Date' },
        { key: 'files_audio', label: 'Files Audio', tooltip: true, labelKey: 'files_audio_label' },
    ]

    const columns = computed(() => {
        const cols = [...baseColumns]
        // If we're on the delegate page, show "Delegate ID" instead of "Ticket ID"
        if (typeUrl.value === 'delegate') {
            for (const c of cols) {
                if (c && c.key === 'code') {
                    c.label = 'Delegate ID'
                    break
                }
            }
        }
        if (typeUrl.value === 'ticket') cols.push({ key: 'limit_access_time', label: 'Limit Access Time' }, { key: 'status', label: 'Status' }, { key: 'action', label: 'Action' })
        if (typeUrl.value === 'delegate') cols.push({ key: 'status', label: 'Status' })
        return cols
    })

    const type = computed(() => {
        if (typeUrl.value === 'delegate') return 'delegate'
        if (typeUrl.value === 'ticket') return 'file_share'
        return 'unknown'
    })

    const requiredPermission = computed(() => {
        if (typeUrl.value === 'delegate') return 'Delegate Management'
        if (typeUrl.value === 'ticket') return 'Ticket Management'
        return 'Unknown Permission'
    })

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
            if (filters.end_date) params.set('end_date', filters.end_date)
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
                // Only populate ticketOptions and createdByOptions once (on initial load).
                // If either is already populated with more than the default option,
                // skip rebuilding that specific list to avoid overwriting a user selection.
                if (!ticketOptions.value || ticketOptions.value.length <= 1) {
                    ticketOptions.value = tOpts
                }
                if (!createdByOptions.value || createdByOptions.value.length <= 1) {
                    createdByOptions.value = cOpts
                }
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
            filters.end_date = ''
            filters.status = []
            filters.files_audio = []
            sortColumn.value = ''
            sortDirection.value = ''
            startInput.value._flatpickrInstance.clear()
            endInput.value._flatpickrInstance.clear()

            if (startInput.value) {
                startInput.value._flatpickrInstance.clear()
            }
            if (endInput.value) {
                endInput.value._flatpickrInstance.clear()
            }

            // Also clear search input and any pending search timeout
            searchQuery.value = ''
            if (searchTimeout) { clearTimeout(searchTimeout); searchTimeout = null }

            currentPage.value = 1
            fetchData()
            // focus search input after DOM updates
            nextTick(() => {
                if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') searchInputRef.value.focus()
            })
        } catch (e) {
            console.error('resetFilters error', e)
        }
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

    const pageTitle = computed(() => {
        if (typeUrl.value === 'ticket') return 'Ticket Management'
        if (typeUrl.value === 'delegate') return 'Delegate Management'
        return 'Ticket History'
    })

    const exportSelections = reactive({ pdf: false, excel: false, csv: false})
    const canExport = computed(() => authStore.hasPermission('Export Recordings'))

    const resetExportSelections = () => {
        exportSelections.pdf = false
        exportSelections.excel = false
        exportSelections.csv = false
    }

    const confirmExport = async () => {
        const picks = []
        if (exportSelections.pdf) picks.push('pdf')
        if (exportSelections.excel) picks.push('excel')
        if (exportSelections.csv) picks.push('csv')
        exportOpen.value = false
        await onExportFormat(picks)
        resetExportSelections()
    }

    const cancelExport = () => {
        resetExportSelections()
        exportOpen.value = false
    }

    const toggleExport = () => {
        exportOpen.value = !exportOpen.value
    }

    const cardTitle = computed(() => {
        const p = route.path || ''
        if (p === '/ticket-management') return 'Ticket Management'
        if (p === '/delegate-management') return 'Delegate Management'
        return 'File Share'
    })

    const downloading = ref(false)
    const downloadProgress = ref(0) // percent 0-100
    const downloadSpeed = ref('0 MB/s')
    const downloadRemaining = ref('')

    const onExportFormat = async (formatOrFormats) => {
        if (!canExport.value) return
        let formats = []
        if (typeof formatOrFormats === 'string') formats = [formatOrFormats]
        else if (Array.isArray(formatOrFormats)) formats = formatOrFormats
        else formats = []

        if (formats.length === 0) return

        // rows to export (no voice selection on this page)
        const rowsToExport = paginatedRecords.value || []
        const exportColumns = (baseColumns || []).filter(c => c && c.key !== 'checked')
        // only create a ZIP when multiple formats requested
        const multipleOutput = (formats.length > 1)

        // timestamp helper for filenames: Audio recordYYYYmmddHHMMSS
        const fmtTimestamp = (d) => {
            const yy = d.getFullYear()
            const mm = String(d.getMonth() + 1).padStart(2, '0')
            const dd = String(d.getDate()).padStart(2, '0')
            const hh = String(d.getHours()).padStart(2, '0')
            const mi = String(d.getMinutes()).padStart(2, '0')
            const ss = String(d.getSeconds()).padStart(2, '0')
            return `${yy}${mm}${dd}${hh}${mi}${ss}`
        }
        const timestampForName = fmtTimestamp(new Date())

        // progress helpers
        let startTime = 0
        let totalBytes = 0
        let completedTasks = 0
        const totalTasks = formats.length || 1
        const markTaskDone = (bytes) => {
            try {
                completedTasks += 1
                if (bytes && typeof bytes === 'number') totalBytes += bytes
                const pct = Math.round((completedTasks / totalTasks) * 100)
                downloadProgress.value = Math.min(100, pct)
                const elapsed = Math.max(0.001, (Date.now() - startTime) / 1000)
                const speed = totalBytes / elapsed // bytes/sec
                const mbps = speed / (1024 * 1024)
                if (isFinite(mbps)) downloadSpeed.value = `${mbps.toFixed(1)} MB/s`
                const avgPerTask = elapsed / completedTasks
                const remainSec = Math.max(0, Math.round(avgPerTask * (totalTasks - completedTasks)))
                const mm = String(Math.floor(remainSec / 60)).padStart(2, '0')
                const ss = String(remainSec % 60).padStart(2, '0')
                downloadRemaining.value = `${mm}:${ss} min.`
            } catch (e) { console.warn('markTaskDone failed', e) }
        }

        const finishDownloading = (minDisplayMs = 3000) => {
            try {
                const elapsed = Math.max(0, Date.now() - startTime)
                const wait = Math.max(0, minDisplayMs - elapsed)
                setTimeout(() => {
                    try {
                        const pct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 100
                        downloadProgress.value = Math.min(100, Math.max(0, pct))
                        downloadRemaining.value = ''
                        downloadSpeed.value = downloadSpeed.value || '0.0 MB/s'
                        downloading.value = false
                    } catch (e) { /* ignore */ }
                }, wait)
            } catch (e) { console.warn('finishDownloading failed', e) }
        }

        try {
            // initialize UI
            downloading.value = true
            downloadProgress.value = 0
            downloadSpeed.value = '0 MB/s'
            downloadRemaining.value = ''
            startTime = Date.now()

            // when multipleOutput, try to package into a ZIP
            if (multipleOutput) {
                try {
                    try {
                        await import('../assets/js/jszip.min.js')
                    } catch (e) { /* ignore, try window.JSZip */ }

                    if (window.JSZip) {
                        const zip = new window.JSZip()
                        let anyFailed = false
                        for (const fmt of formats) {
                            try {
                                const res = await exportTableToFormat(fmt, cardTitle.value, {
                                    rows: rowsToExport || [],
                                    columns: exportColumns,
                                    startIndex: startIndex.value || 0,
                                    fileNamePrefix: cardTitle.value,
                                    returnBlob: true
                                })
                                if (res && res.blob) {
                                    const extMap = { excel: 'xls', csv: 'csv', pdf: 'pdf' }
                                    const ext = extMap[fmt] || fmt
                                    const name = res.fileName || `${cardTitle.value} ${timestampForName}.${ext}`
                                    zip.file(name, res.blob)
                                    try { markTaskDone(res.blob.size) } catch (e) {}
                                } else {
                                    anyFailed = true
                                    try { markTaskDone() } catch (e) {}
                                }
                            } catch (e) {
                                anyFailed = true
                                console.error('non-voice export into zip failed', e)
                                try { markTaskDone() } catch (er) {}
                            }
                        }
                        const zipBlob = await zip.generateAsync({ type: 'blob' })
                        const zipName = `${cardTitle.value} ${timestampForName}.zip`
                        const a = document.createElement('a')
                        a.href = URL.createObjectURL(zipBlob)
                        a.download = zipName
                        document.body.appendChild(a)
                        a.click()
                        a.remove()
                        setTimeout(() => URL.revokeObjectURL(a.href), 3000)
                        if (anyFailed) try { showToast('Some exports failed while creating ZIP', 'warning') } catch (e) {}
                        finishDownloading()
                        return
                    }
                } catch (e) {
                    console.error('ZIP creation for non-voice failed', e)
                }
                // fall through to individual downloads if JSZip not available
            }

            // per-format downloads
            for (const fmt of formats) {
                try {
                    const res = await exportTableToFormat(fmt, cardTitle.value, {
                        rows: rowsToExport || [],
                        columns: exportColumns,
                        startIndex: startIndex.value || 0,
                        fileNamePrefix: cardTitle.value,
                        returnBlob: true
                    })
                    if (res && res.blob) {
                        try {
                            const url = URL.createObjectURL(res.blob)
                            const a = document.createElement('a')
                            a.href = url
                            a.download = res.fileName || `${cardTitle.value} ${timestampForName}`
                            document.body.appendChild(a)
                            a.click()
                            a.remove()
                            setTimeout(() => URL.revokeObjectURL(url), 3000)
                        } catch (e) { console.warn('trigger blob download failed', e) }
                        try { markTaskDone(res.blob.size) } catch (e) {}
                    } else {
                        try { markTaskDone() } catch (e) {}
                    }
                } catch (e) {
                    console.error('non-voice export failed', fmt, e)
                    try { if (typeof showToast === 'function') showToast(`Export ${fmt} failed`, 'error') } catch (er) {}
                }
            }

            finishDownloading()
            return
        } catch (err) {
            console.error('onExportFormat error', err)
            try { if (typeof showToast === 'function') showToast('Export failed', 'error') } catch (e) {}
        }
        finally {
            try { if (downloading.value) { finishDownloading() } } catch (e) {}
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
        typeUrl,
        pageTitle,
        exportSelections,
        canExport,
        downloadProgress,
        downloadSpeed,
        downloadRemaining,
        downloading
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
        toggleUserStatus,
        confirmExport,
        cancelExport,
    }

    return {
        ...state,
        ...actions
    }
}
