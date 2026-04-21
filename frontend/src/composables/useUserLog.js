import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_GET_USER_ALL, API_GET_LOG_USER } from '../api/paths'
import { exportTableToFormat } from '../assets/js/function-all'

export function useUserLog() {
    const route = useRoute()
    const authStore = useAuthStore()

    const searchQuery = ref('')
    let searchTimeout = null
    let userFilterTimeout = null

    const exportOpen = ref(false)
    const exportWrap = ref(null)
    
    const perPageOptions = [50, 100, 500, 1000]
    const perPage = ref(50)
    const currentPage = ref(1)
    
    const filters = reactive({ name: '', action: '', start_date: '', end_date: '' })
    const userOptions = ref([])
    const actionOptions = ref([
        { label: 'All Actions', value: 'all' },
        { label: 'Change User Status', value: 'Change User Status' },
        { label: 'Create Columns', value: 'Create Columns' },
        { label: 'Create Config Group', value: 'Create Config Group' },
        { label: 'Create Config Team', value: 'Create Config Team' },
        { label: 'Create Custom Role', value: 'Create Custom Role' },
        { label: 'Create Favorite', value: 'Create Favorite' },
        { label: 'Created User', value: 'Created User' },
        { label: 'Delete Config Group', value: 'Delete Config Group' },
        { label: 'Delete Config Team', value: 'Delete Config Team' },
        { label: 'Delete Custom Role', value: 'Delete Custom Role' },
        { label: 'Delete Favorite', value: 'Delete Favorite' },
        { label: 'Delete User', value: 'Delete User' },
        { label: 'Download', value: 'Download' },
        { label: 'Edit Favorite', value: 'Edit Favorite' },
        { label: 'Login', value: 'Login' },
        { label: 'Play audio', value: 'Play audio' },
        { label: 'Save file', value: 'Save file' },
        { label: 'Update Config Group', value: 'Update Config Group' },
        { label: 'Update Config Team', value: 'Update Config Team' },
        { label: 'Update Custom Role', value: 'Update Custom Role' },
        { label: 'Update Favorite Search', value: 'Update Favorite Search' },
        { label: 'Update User', value: 'Update User' },
    ])

    const startInput = ref(null)
    const endInput = ref(null)
    const searchInputRef = ref(null)

    const perWrap = ref(null)
    const perDropdownOpen = ref(false)

    const records = ref([])
    const totalItems = ref(0)
    const loading = ref(false)
    const expanded = ref(new Set())

    // download modal state (used by export flows)
    const downloading = ref(false)
    const downloadProgress = ref(0) // percent 0-100
    const downloadSpeed = ref('0 MB/s')
    const downloadRemaining = ref('')

    const columns = [
        { key: 'index', label: '#', isIndex: true},
        { key: 'username', label: 'Username' },
        { key: 'full_name', label: 'Full Name' },
        { key: 'action', label: 'Action' },
        { key: 'status', label: 'Status' },
        { key: 'detail', label: 'Description', tooltip: true },
        { key: 'ip_address', label: 'IP Address'},
        { key: 'timestamp', label: 'Timestamp' },
        { key: 'client_type', label: 'Client type'}
    ]

    const type = computed(() => {
        const p = route.path || ''
        if (p === '/logs/system') return 'system'
        if (p === '/logs/audit') return 'audit'
        if (p === '/logs/ticket-history') return 'ticket'
        return 'user'
    })

    const cardTitle = computed(() => {
        const p = route.path || ''
        if (p === '/logs/system') return 'System log'
        if (p === '/logs/audit') return 'Audit log'
        if (p === '/logs/ticket-history') return 'Ticket History'
        return 'User Logs'
    })

    const requiredPermission = computed(() => {
        const p = route.path || ''
        if (p === '/logs/system') return 'System Log'
        if (p === '/logs/audit') return 'Audit Log'
        if (p === '/logs/ticket-history') return 'Ticket History'
        return 'User Logs'
    })

    const requiredExportPermission = computed(() => {
        const p = route.path || ''
        if (p === '/logs/system') return 'Save As System Log'
        if (p === '/logs/audit') return 'Save As Audit Log'
        if (p === '/logs/ticket-history') return 'Save As Ticket History'
        return 'Save As User Logs'
    })

    const canView = computed(() => authStore.hasPermission(requiredPermission.value))

    const canExport = computed(() => authStore.hasPermission(requiredExportPermission.value))

    const toggleExport = () => {
        if (!canExport.value) return
        exportOpen.value = !exportOpen.value
    }

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

            if (filters.name && filters.name !== 'all') params.set('name', filters.name)
            if (filters.action && filters.action !== 'all') params.set('action', filters.action)
            if (filters.start_date) params.set('start_date', filters.start_date)
            if (filters.end_date) params.set('end_date', filters.end_date)

            const res = await fetch(`${API_GET_LOG_USER(type.value)}?${params.toString()}`, { credentials: 'include' })
            if (!res.ok) throw new Error('Failed to fetch')
            const json = await res.json()
            records.value = json.data || json.user_management || []
            totalItems.value = json.recordsFiltered ?? json.recordsTotal ?? (Array.isArray(records.value) ? records.value.length : 0)
        } catch (e) {
            console.error('fetchData error', e)
        } finally {
            loading.value = false
        }
    }

    const fetchUsers = async () => {
        if (!canView.value) return
        try {
            const params = new URLSearchParams()
            params.set('draw', 1)
            params.set('start', 0)
            params.set('length', 1000)
            params.set('type', type.value)
            if (filters.action && filters.action !== 'all') params.set('action', filters.action)
            if (filters.start_date) params.set('start_date', filters.start_date)
            if (filters.end_date) params.set('end_date', filters.end_date)
            const res = await fetch(`${API_GET_USER_ALL()}?${params.toString()}`, { credentials: 'include' })
            if (!res.ok) throw new Error('Failed to fetch users')
            const json = await res.json()
            const list = json.data || []
            const opts = [{ label: 'All Users', value: 'all' }]
            for (const p of list) {
                const u = p.user ? p.user : p
                const uname = u?.username || ''
                const fullname = `${u?.first_name || ''} ${u?.last_name || ''}`.trim()
                const label = fullname ? `${uname} (${fullname})` : uname
                opts.push({ label, value: uname })
            }
            userOptions.value = opts
        } catch (e) {
            console.error('fetchUsers error', e)
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

    const onRowEdit = (row) => { console.log('edit row', row) }
    const onRowDelete = (row) => { console.log('delete row', row) }

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
                        filters.name = ''
                        filters.action = ''
                        filters.start_date = ''
                        filters.end_date = ''
                        sortColumn.value = ''
                        sortDirection.value = ''
                        startInput.value._flatpickrInstance.clear()
                        endInput.value._flatpickrInstance.clear()

                        if (startInput.value && startInput.value._flatpickrInstance) {
                            startInput.value._flatpickrInstance.clear()
                        }
                        if (endInput.value && endInput.value._flatpickrInstance) {
                            endInput.value._flatpickrInstance.clear()
                        }

                        currentPage.value = 1
                        fetchUsers()
                        fetchData()
                } catch (e) {
                        console.error('resetFilters error', e)
                }
        }

        const onExportFormat = async (formatOrFormats) => {
            if (!canExport.value) return
            let formats = []
            if (typeof formatOrFormats === 'string') formats = [formatOrFormats]
            else if (Array.isArray(formatOrFormats)) formats = formatOrFormats
            else formats = []

            if (formats.length === 0) return

            // rows to export (no voice selection on this page)
            const rowsToExport = paginatedRecords.value || []
            const exportColumns = (columns || []).filter(c => c && c.key !== 'checked')
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

    watch(filters, () => {
        if (userFilterTimeout) clearTimeout(userFilterTimeout)
        userFilterTimeout = setTimeout(() => {
            fetchUsers()
            currentPage.value = 1
            fetchData()
            userFilterTimeout = null
        }, 350)
    }, { deep: true })

    onMounted(() => {
        registerRequest(fetchData())
        fetchUsers()
        document.addEventListener('click', onDocClick)
    })

    onBeforeUnmount(() => {
        document.removeEventListener('click', onDocClick)
    })

    const exportSelections = reactive({ pdf: false, excel: false, csv: false})

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

    const sortColumn = ref('')
    const sortDirection = ref('')

    const onSortChange = ({ column, direction }) => {
        sortColumn.value = column
        sortDirection.value = direction
        fetchData()
    }

    const state = {
        authStore,
        searchQuery,
        exportOpen,
        exportWrap,
        perPageOptions,
        perPage,
        currentPage,
        filters,
        userOptions,
        actionOptions,
        startInput,
        endInput,
        searchInputRef,
        perWrap,
        perDropdownOpen,
        records,
        totalItems,
        loading,
        expanded,
        columns,
        type,
        cardTitle,
        requiredPermission,
        canView,
        totalPages,
        startIndex,
        paginatedRecords,
        exportSelections,
        canExport,
        downloading,
        downloadProgress,
        downloadSpeed,
        sortColumn,
        sortDirection,
        downloadRemaining
    }

    const actions = {
        onTyping,
        setPerPage,
        changePage,
        onRowEdit,
        onRowDelete,
        clearSearchQuery,
        resetFilters,
        toggleExport,
        onExportFormat,
        fetchData,
        fetchUsers,
        confirmExport,
        cancelExport,
        onSortChange,
    }

    return {
        ...state,
        ...actions
    }
}
