import { reactive, ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_AUDIO_LIST, API_HOME_INDEX, API_LOG_PLAY_AUDIO, API_GET_CREDENTIALS, API_LOG_SAVE_FILE, API_GET_COLUMN_AUDIO_RECORD, getApiBase,API_PROXY_AUDIO,API_CHECK_FILE_SHARE, API_PLAY_AUDIO } from '../api/paths'
import { getCsrfToken } from '../api/csrf'
import '../assets/js/jspdf.umd.min.js'
import '../assets/js/jspdf.plugin.autotable.min.js'
import '../assets/js/jszip.min.js'
import { exportTableToFormat, showToast } from '../assets/js/function-all'

export function useHome() {
  const authStore = useAuthStore()

  const filters = reactive({
    databaseServer: '',
    from: '',
    to: '',
    duration: '',
    fileName: '',
    callDirection: '',
    customerNumber: '',
    agent: '',
    extension: '',
    fullName: '',
    customField: '',
    file_share: '',
    is_ticket: ''
  })

  const searchQuery = ref('')
  const searchInputRef = ref(null)
  let searchTimeout = null

  const perPageOptions = [50, 100, 500, 1000]
  const perPage = ref(50)
  const currentPage = ref(1)
  const perDropdownOpen = ref(false)
  const perDropdownUp = ref(false)
  const mainDbOptions = ref([])
  const favoriteSearchAll = ref([])
  const agentOptions = ref([{ label: 'All', value: 'all' }])
  const callDirectionOptions = [
    { label: 'All', value: 'All' },
    { label: 'Internal', value: 'Internal' },
    { label: 'Inbound', value: 'Inbound' },
    { label: 'Outbound', value: 'Outbound' }
  ]

  const perWrap = ref(null)
  const fromInput = ref(null)
  const toInput = ref(null)
  const durationInput = ref(null)
  const exportWrap = ref(null)
  const exportOpen = ref(false)
  const exportSelections = reactive({ pdf: false, excel: false, csv: false, voice: false })
  const recentWrap = ref(null)
  const recentOpen = ref(false)
  const recentList = ref([])
  const showFavoriteModal = ref(false)
  const showAudioModal = ref(false)
  const audioSrc = ref('')
  const audioMetadata = reactive({ fileName: '', duration: '', customerNumber: '', extension: '', agent: '', callDirection: '', from: '', to: '' })
  
  const processedSaveLogs = new Set()
  let saveLogsInterval = null
  // file-share notification (WebSocket-only; polling removed)
  const showFileShareNotification = ref(false)
  let fileShareWs = null

  const records = ref([])
  const totalItems = ref(0)
  const loading = ref(false)

  // download modal state
  const downloading = ref(false)
  const downloadProgress = ref(0) // percent 0-100
  const downloadSpeed = ref('0 MB/s')
  const downloadRemaining = ref('')

  const sortColumn = ref('')
  const sortDirection = ref('')

  const defaultColumns = [
    { key: 'checked', label: '', sortable: false, width: '1%' },
    { key: 'index', label: '#', isIndex: true},
    { key: 'main_db', label: 'Database Server' },
    { key: 'start_datetime', label: 'Start Date & Time' },
    { key: 'end_datetime', label: 'End Date & Time' },
    { key: 'duration', label: 'Duration' },
    { key: 'file_name', label: 'File Name', tooltip: true },
    { key: 'call_direction', label: 'Call Direction' },
    { key: 'customer_number', label: 'Customer Number' },
    { key: 'extension', label: 'Extension' },
    { key: 'agent', label: 'Agent' },
    { key: 'full_name', label: 'Full Name' },
    { key: 'custom_field_1', label: 'Custom Field' }
  ]

  const columns = ref([...defaultColumns])

  // when viewing delegated/file_share results, inject the share-specific columns
  watch(() => filters.file_share, (v) => {
    try {
      if (v === 'true') {
        if (!columns.value.find(c => c.key === 'created_by')) {
          const baseCols = defaultColumns.filter(c => c.key !== 'checked')
          columns.value = [
            ...baseCols,
            { key: 'delegate_id', label: 'Delegate ID' },
            { key: 'start_date', label: 'Start Date' },
            { key: 'expire_at', label: 'Expire Date' },
            { key: 'created_by', label: 'Created by' },
            { key: 'download', label: 'Download', sortable: false },
          ]
        }
      } else {
        // only revert to default when ticket mode is not active
        if (filters.is_ticket !== 'true') {
          // revert to default columns (fetchActiveColumns may override later)
          columns.value = [...defaultColumns]
        }
      }
    } catch (e) {
      console.error('update columns for file_share error', e)
    }
  })

  // when viewing ticket results, inject the same share-specific columns
  watch(() => filters.is_ticket, (v) => {
    try {
      if (v === 'true') {
        if (!columns.value.find(c => c.key === 'created_by')) {
          const baseCols = defaultColumns.filter(c => c.key !== 'checked')
          columns.value = [
            ...baseCols,
            { key: 'ticket_id', label: 'Ticket ID' },
            { key: 'start_date', label: 'Start Date' },
            { key: 'expire_at', label: 'Expire Date' },
            { key: 'created_by', label: 'Created by' },
            { key: 'download', label: 'Download', sortable: false }
          ]
        }
      } else {
        // only revert to default when file_share mode is not active
        if (filters.file_share !== 'true') {
          columns.value = [...defaultColumns]
        }
      }
    } catch (e) {
      console.error('update columns for is_ticket error', e)
    }
  })

  // selection state for file sharing (keyed map to avoid duplicates across pages)
  const _selectedFilesMap = ref({})
  const selectedFiles = computed(() => Object.values(_selectedFilesMap.value || {}))
  const selectedCount = computed(() => Object.keys(_selectedFilesMap.value || {}).length)

  function _makeKey(row) {
    const fid = row.file_id ?? row.id ?? row.fileId
    if (fid !== undefined && fid !== null && fid !== '') return String(fid)
    // fallback composite key when no id available — include multiple fields to avoid accidental collisions
    const parts = [row.file_name || '', (row.start_datetime ?? row.startDatetime ?? row.start) || '', row.customer_number ?? row.customerNumber ?? '', row.extension ?? '']
    return parts.join('::')
  }

  function toggleRowSelection(row) {
    if (!row) return
    const key = _makeKey(row)
    if (Object.prototype.hasOwnProperty.call(_selectedFilesMap.value, key)) {
      try { const copy = { ..._selectedFilesMap.value }; delete copy[key]; _selectedFilesMap.value = copy } catch (e) {}
      row.checked = false
    } else {
      // store the full row object for exports so exported files contain all available fields
      const entry = { ...(row || {}) }
      // ensure a stable file_id exists on the stored entry
      entry.file_id = entry.file_id ?? entry.id ?? entry.fileId ?? key
      _selectedFilesMap.value = { ..._selectedFilesMap.value, [key]: entry }
      row.checked = true
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

  function clearSearchQuery() {
    searchQuery.value = ''
    if (searchTimeout) { clearTimeout(searchTimeout); searchTimeout = null }
    currentPage.value = 1
    fetchData()
    nextTick(() => {
      if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') searchInputRef.value.focus()
    })
  }

  const fetchIndexHome = async () => {
    const task = (async () => {
      try {
        const res = await fetch(API_HOME_INDEX(), { credentials: 'include' })
        if (!res.ok) return
        const json = await res.json()
        const mdb = json.main_db || []
        const mopts = []

        for (const m of mdb) {
          const mlabal = m.database_name
          const mvalue = m.id
          mopts.push({ label: mlabal, value: mvalue })
        }
        mainDbOptions.value = mopts

        const agents = json.agent || []
        const aopts = [{ label: 'All', value: 'all' }]
        for (const a of agents) {
          const name = `${a.first_name || ''} ${a.last_name || ''}`.trim()
          const alabel = a.agent_code ? `${a.agent_code} - ${name}` : name
          const avalue = a.id
          aopts.push({ label: alabel, value: avalue })
        }
        agentOptions.value = aopts
        
        favoriteSearchAll.value = json.favorite_search_all || []
      } catch (err) {
        console.error('fetchIndexHome error', err)
      }
    })()
    registerRequest(task)
    await task
  }

  const setPerPage = (opt) => {
    perPage.value = opt
    perDropdownOpen.value = false
  }

  const onDocClick = (e) => {
    if (perWrap.value && !perWrap.value.contains(e.target)) perDropdownOpen.value = false
    if (exportWrap.value && !exportWrap.value.contains(e.target)) exportOpen.value = false
    if (recentWrap.value && !recentWrap.value.contains(e.target)) recentOpen.value = false
  }

  const toggleRecent = () => {
    recentOpen.value = !recentOpen.value
  }

  const applyRecent = async (r) => {
    // helper to finish downloading UI, guaranteeing minimum display time
    const finishDownloading = () => {
      try {
        const minMs = 30000
        const elapsed = Math.max(0, Date.now() - startTime)
        const wait = Math.max(0, minMs - elapsed)
        downloadProgress.value = 100
        setTimeout(() => { downloading.value = false }, wait)
      } catch (e) { downloading.value = false }
    }

    try {
      const raw = typeof r.raw_data === 'string' ? JSON.parse(r.raw_data || '{}') : (r.raw_data || null)
      if (raw) {
        const keyMap = {
          database_name: 'databaseServer',
          start_date: 'from',
          end_date: 'to',
          file_name: 'fileName',
          duration: 'duration',
          customer: 'customerNumber',
          agent: 'agent',
          call_direction: 'callDirection',
          extension: 'extension',
          full_name: 'fullName',
          custom_field: 'customField'
        }
        for (const [rawKey, val] of Object.entries(raw)){
          const target = keyMap[rawKey]
          if (target && Object.prototype.hasOwnProperty.call(filters, target)){
            filters[target] = val
          }
        }

        try {
          if (filters.callDirection) {
            const v = String(filters.callDirection)
            const found = callDirectionOptions.find(o => String(o.value).toLowerCase() === v.toLowerCase() || String(o.label).toLowerCase() === v.toLowerCase())
            if (found) filters.callDirection = found.value
          }
        } catch (e) {}

        try {
          const parseDate = (s) => {
            if (!s) return null
            const t = String(s).replace(' ', 'T')
            const d = new Date(t)
            return isNaN(d.getTime()) ? null : d
          }
          const fromDate = parseDate(filters.from)
          const toDate = parseDate(filters.to)

          if (fromInput.value) {
            const inst = fromInput.value._flatpickrInstance
            if (inst && typeof inst.setDate === 'function') {
              if (fromDate) inst.setDate(fromDate, true)
              else inst.clear()
            } else {
              fromInput.value.value = filters.from || ''
            }
          }
          if (toInput.value) {
            const inst2 = toInput.value._flatpickrInstance
            if (inst2 && typeof inst2.setDate === 'function') {
              if (toDate) inst2.setDate(toDate, true)
              else inst2.clear()
            } else {
              toInput.value.value = filters.to || ''
            }
          }
        } catch (e) { console.warn('applyRecent update inputs failed', e) }

        await fetchData()
      }
    } catch (err) {
      console.error('applyRecent error', err)
    } finally {
      recentOpen.value = false
    }
  }

  const applyRecentRange = async (rangeKey) => {
    try {
      const now = new Date()
      let fromDate = null
      let toDate = null
      if (rangeKey === 'latest') {
        fromDate = null
        toDate = null
      } else if (rangeKey === '1h') {
        fromDate = new Date(now.getTime() - 1 * 60 * 60 * 1000)
        toDate = now
      } else if (rangeKey === '1d') {
        fromDate = new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000)
        toDate = now
      } else if (rangeKey === '1w') {
        fromDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        toDate = now
      } else if (rangeKey === '1m') {
        fromDate = new Date(now)
        fromDate.setMonth(fromDate.getMonth() - 1)
        toDate = now
      } else if (rangeKey === '1y') {
        fromDate = new Date(now)
        fromDate.setFullYear(fromDate.getFullYear() - 1)
        toDate = now
      }

      const pad = (n) => String(n).padStart(2, '0')
      const fmt = (d) => {
        if (!d) return ''
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
      }

      filters.from = fromDate ? fmt(fromDate) : ''
      filters.to = toDate ? fmt(toDate) : ''

      try {
        if (fromInput.value) {
          const inst = fromInput.value._flatpickrInstance
          if (inst && typeof inst.setDate === 'function') {
            if (fromDate) inst.setDate(fromDate, true)
            else inst.clear()
          } else {
            fromInput.value.value = filters.from
          }
        }
      } catch (e) { console.warn('update fromInput failed', e) }
      try {
        if (toInput.value) {
          const inst = toInput.value._flatpickrInstance
          if (inst && typeof inst.setDate === 'function') {
            if (toDate) inst.setDate(toDate, true)
            else inst.clear()
          } else {
            toInput.value.value = filters.to
          }
        }
      } catch (e) { console.warn('update toInput failed', e) }
      recentOpen.value = false
      await fetchData()

      try {
        const raw = {
          database_name: filters.databaseServer,
          start_date: filters.from,
          end_date: filters.to,
          file_name: filters.fileName,
          duration: filters.duration,
          customer: filters.customerNumber,
          agent_id: filters.agent,
          agent: filters.agent,
          call_direction: filters.callDirection,
          extension: filters.extension,
          full_name: filters.fullName,
          custom_field: filters.customField,
          search: searchQuery.value
        }
        pushRecent({ raw_data: raw, created_at: new Date().toISOString() })
      } catch (e) {
        console.warn('save recent range failed', e)
      }
    } catch (err) {
      console.error('applyRecentRange error', err)
      recentOpen.value = false
    }
  }

  const applyLatestRecent = async () => {
    try {
      if (!recentList.value || recentList.value.length === 0) return
      const latest = recentList.value[0]
      await applyRecent(latest)
    } catch (err) {
      console.error('applyLatestRecent error', err)
    }
  }

  const canExport = computed(() => authStore.hasPermission('Save As Index'))
  const toggleExport = () => {
    if (!canExport.value) return
    exportOpen.value = !exportOpen.value
  }

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

      if (Array.isArray(filters.databaseServer)) {
        const vals = filters.databaseServer.filter(v => String(v).toLowerCase() !== 'all')
        if (vals.length) params.set('database_name', vals.join(','))
      } else if (filters.databaseServer && String(filters.databaseServer) !== 'all') {
        params.set('database_name', filters.databaseServer)
      }

      if (Array.isArray(filters.callDirection)) {
        const vals = filters.callDirection.filter(v => String(v).toLowerCase() !== 'all')
        if (vals.length) params.set('call_direction', vals.join(','))
      } else if (filters.callDirection && String(filters.callDirection).toLowerCase() !== 'all') {
        params.set('call_direction', filters.callDirection)
      }

      if (Array.isArray(filters.agent)) {
        const vals = filters.agent.filter(v => String(v).toLowerCase() !== 'all')
        if (vals.length) params.set('agent_id', vals.join(','))
      } else if (filters.agent && String(filters.agent) !== 'all') {
        params.set('agent_id', filters.agent)
      }
      if (filters.file_share === 'true') {
        params.set('file_share', 'true')
      }

      if (filters.from) params.set('start_date', filters.from)
      if (filters.to) params.set('end_date', filters.to)

      function norm(v){
        if (Array.isArray(v)) return v.join(',')
        if (v == null) return ''
        const s = String(v).trim()
        if (s.indexOf(',') === -1) return s
        return s.split(',').map(x => x.trim()).filter(Boolean).join(',')
      }

      const fn = norm(filters.fileName)
      if (fn) params.set('file_name', fn)
      const dur = norm(filters.duration)
      if (dur) params.set('duration', dur)
      const cust = norm(filters.customerNumber)
      if (cust) params.set('customer_number', cust)
      const ext = norm(filters.extension)
      if (ext) params.set('extension', ext)
      const full = norm(filters.fullName)
      if (full) params.set('full_name', full)
      const cf = norm(filters.customField)
      if (cf) params.set('custom_field', cf)

      const res = await fetch(`${API_AUDIO_LIST()}?${params.toString()}`, { credentials: 'include' })
      if (!res.ok) throw new Error('Failed to fetch')
      const json = await res.json()
      // sync server-provided flags into filters (use string 'true' for compatibility)
      try {
        if (typeof json.is_ticket !== 'undefined') {
          filters.is_ticket = json.is_ticket ? 'true' : ''
        }
        if (typeof json.file_share !== 'undefined') {
          filters.file_share = json.file_share ? 'true' : ''
        }
      } catch (e) { /* ignore */ }
      records.value = (json.data || []).map(r => {
        try {
          // if this row was previously selected (by key), preserve checked state
          const k = _makeKey(r)
          r.checked = !!(_selectedFilesMap.value && Object.prototype.hasOwnProperty.call(_selectedFilesMap.value, k))
        } catch (e) { r.checked = !!r.checked }
        return r
      })
      totalItems.value = json.recordsFiltered ?? json.recordsTotal ?? records.value.length
    } catch (e) {
      console.error('fetchData error', e)
    } finally {
      loading.value = false
    }
  }

  const totalPages = computed(() => Math.max(1, Math.ceil(totalItems.value / perPage.value)))
  const startIndex = computed(() => (currentPage.value - 1) * perPage.value)
  const paginatedRecords = computed(() => records.value)
  const selectAllChecked = computed(() => {
    const rows = paginatedRecords.value || []
    if (!rows || rows.length === 0) return false
    // consider a row checked if its key exists in the map
    return rows.every(r => {
      try {
        const k = _makeKey(r)
        return !!(_selectedFilesMap.value && Object.prototype.hasOwnProperty.call(_selectedFilesMap.value, k))
      } catch (e) { return !!r.checked }
    })
  })

  function toggleSelectAll() {
    const rows = paginatedRecords.value || []
    if (!rows || rows.length === 0) return
    const allChecked = rows.every(r => {
      try {
        const k = _makeKey(r)
        return !!(_selectedFilesMap.value && Object.prototype.hasOwnProperty.call(_selectedFilesMap.value, k))
      } catch (e) { return !!r.checked }
    })
    if (allChecked) {
      // uncheck visible rows and remove from map
      for (const r of rows) {
        try {
          const k = _makeKey(r)
          if (Object.prototype.hasOwnProperty.call(_selectedFilesMap.value, k)) {
            const copy = { ..._selectedFilesMap.value }
            delete copy[k]
            _selectedFilesMap.value = copy
          }
          r.checked = false
        } catch (e) {}
      }
    } else {
      // select visible rows (add to map)
      const copy = { ..._selectedFilesMap.value }
      for (const r of rows) {
        try {
          const k = _makeKey(r)
            if (!Object.prototype.hasOwnProperty.call(copy, k)) {
            // store full row data so exports include all fields for selected rows
            copy[k] = { ...(r || {}) }
            copy[k].file_id = copy[k].file_id ?? copy[k].id ?? copy[k].fileId ?? k
          }
          r.checked = true
        } catch (e) { /* ignore per-row errors */ }
      }
      _selectedFilesMap.value = copy
    }
  }
  const startItem = computed(() => totalItems.value === 0 ? 0 : startIndex.value + 1)
  const endItem = computed(() => Math.min(totalItems.value, startIndex.value + (records.value.length || 0)))

  const pagesToShow = computed(() => {
    const pages = []
    const total = totalPages.value
    if (total <= 6) {
      for (let i = 1; i <= total; i++) pages.push(i)
      return pages
    }
    const end = Math.min(5, total)
    for (let i = 1; i <= end; i++) pages.push(i)
    if (total > end + 1) pages.push('...')
    pages.push(total)
    return pages
  })

  const changePage = async (p) => { 
    if (p < 1) p = 1
    if (p > totalPages.value) p = totalPages.value
    currentPage.value = p
    await fetchData()
  }

  watch(perPage, () => {
    currentPage.value = 1
    fetchData()
  })

  const RECENT_KEY = 'home_recent_searches'

  const loadRecentFromStorage = () => {
    try {
      const raw = localStorage.getItem(RECENT_KEY)
      if (!raw) return
      const arr = JSON.parse(raw)
      if (Array.isArray(arr)) recentList.value = arr
    } catch (e) {
      console.error('loadRecentFromStorage error', e)
    }
  }

  const saveRecentToStorage = () => {
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(recentList.value.slice(0, 10)))
    } catch (e) {
      console.error('saveRecentToStorage error', e)
    }
  }

  const pushRecent = (item) => {
    try {
      const key = JSON.stringify(item.raw_data || {})
      recentList.value = recentList.value.filter(r => JSON.stringify(r.raw_data || {}) !== key)
      recentList.value.unshift(item)
      if (recentList.value.length > 10) recentList.value.pop()
      saveRecentToStorage()
    } catch (e) {
      console.error('pushRecent error', e)
    }
  }

  const onSearch = async () => {
    currentPage.value = 1
    if (searchTimeout) { clearTimeout(searchTimeout); searchTimeout = null }
    await fetchData()
    try {
      const raw = {
        database_name: filters.databaseServer,
        start_date: filters.from,
        end_date: filters.to,
        file_name: filters.fileName,
        duration: filters.duration,
        customer: filters.customerNumber,
        agent_id: filters.agent,
        agent: filters.agent,
        call_direction: filters.callDirection,
        extension: filters.extension,
        full_name: filters.fullName,
        custom_field: filters.customField,
        search: searchQuery.value
      }
      const item = { raw_data: raw, created_at: new Date().toISOString() }
      pushRecent(item)
    } catch (e) {
      console.error('onSearch save recent error', e)
    }
  }

  const onReset = async () => {
    // Reset all UI state to initial values (like a page reload), without reloading
    try {
      // Reset filter model
      filters.databaseServer = []
      filters.from = ''
      filters.to = ''
      filters.duration = []
      filters.fileName = ''
      filters.callDirection = []
      filters.customerNumber = ''
      filters.agent = []
      filters.fullName = ''
      filters.customField = ''
      filters.extension = ''
      filters.file_share = ''
      filters.is_ticket = ''

      // Reset UI state
      searchQuery.value = ''
      sortColumn.value = ''
      sortDirection.value = ''
      currentPage.value = 1
      perPage.value = 50

      // Clear selection and exported state
      _selectedFilesMap.value = {}
      resetExportSelections()
      exportOpen.value = false
      perDropdownOpen.value = false
      recentOpen.value = false

      // Restore default columns and clear records cache
      columns.value = [...defaultColumns]
      records.value = []
      totalItems.value = 0

      // Helper to clear flatpickr/input refs safely
      const _clearInput = (refEl) => {
        try {
          if (!refEl || !refEl.value) return
          const el = refEl.value
          if (typeof el._flatpickrDoClear === 'function') {
            try {
              // doClear handles To-input reset, el.value, target[key], and has-value
              // internally — no need to repeat those operations here.
              el._flatpickrDoClear()
              try { el.parentNode && el.parentNode.classList.remove('has-value') } catch (e) {}
            } catch (e) {}
            return
          }
          const inst = el._flatpickrInstance || el._flatpickrRangeInstance || el._flatpickr
          if (inst && typeof inst.clear === 'function') { inst.clear(); return }
          if ('value' in el) el.value = ''
        } catch (e) { /* ignore */ }
      }

      _clearInput(fromInput)
      _clearInput(toInput)
      _clearInput(durationInput)

      // Clear DOM-held input text and has-value classes
      try {
        const wrap = document.querySelector('.filter-card')
        if (wrap) {
          wrap.querySelectorAll('.input-group').forEach(g => {
            try {
              g.classList.remove('has-value')
              const inp = g.querySelector('input, textarea, select')
              if (inp) inp.value = ''
            } catch (e) {}
          })
        }
      } catch (e) {}

      await fetchData()
    } catch (err) {
      console.error('onReset error', err)
    }
  }

  async function applyFavorite(fav){
    try{
      const raw = typeof fav.raw_data === 'string' ? JSON.parse(fav.raw_data || '{}') : (fav.raw_data || {})
        const keyMap = {
          database_name: 'databaseServer',
          start_date: 'from',
          end_date: 'to',
          file_name: 'fileName',
          duration: 'duration',
          customer: 'customerNumber',
          agent: 'agent',
          call_direction: 'callDirection',
          extension: 'extension',
          full_name: 'fullName',
          custom_field: 'customField'
        }
        for (const [rawKey, val] of Object.entries(raw)){
          const target = keyMap[rawKey]
          if (target && Object.prototype.hasOwnProperty.call(filters, target)){
            filters[target] = val
          }
        }

        try {
          const multiFields = ['databaseServer', 'agent', 'callDirection']
          for (const mf of multiFields) {
            if (!Object.prototype.hasOwnProperty.call(filters, mf)) continue
            const cur = filters[mf]
            let vals = []
            if (cur == null || cur === '') vals = []
            else if (Array.isArray(cur)) vals = cur.slice()
            else if (typeof cur === 'string') {
              if (cur.indexOf(',') !== -1) vals = cur.split(',').map(x => x.trim()).filter(Boolean)
              else vals = [cur]
            } else {
              vals = [cur]
            }

            if (mf === 'databaseServer' || mf === 'agent') {
              vals = vals.map(x => { const s = String(x).trim(); return /^\d+$/.test(s) ? Number(s) : s })
            }
            if (mf === 'callDirection') {
              vals = vals.map(x => { const s = String(x || '').trim(); return s ? (s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()) : s })
            }
            filters[mf] = vals
          }

          if (Array.isArray(filters.callDirection)) {
            filters.callDirection = filters.callDirection.map(v => {
              const s = String(v || '')
              const found = callDirectionOptions.find(o => String(o.value).toLowerCase() === s.toLowerCase() || String(o.label).toLowerCase() === s.toLowerCase())
              return found ? found.value : v
            }).filter(Boolean)
          }
        } catch (e) {}

      showFavoriteModal.value = false
      await nextTick()

      const parseDate = (s) => {
        if (!s) return null
        const t = String(s).replace(' ', 'T')
        const d = new Date(t)
        return isNaN(d.getTime()) ? null : d
      }

      try {
        if (fromInput.value) {
          const inst = fromInput.value._flatpickrInstance || fromInput.value._flatpickr
          const d = parseDate(filters.from)
          if (inst && typeof inst.setDate === 'function') {
            if (d) inst.setDate(d, true)
            else inst.clear()
          } else {
            fromInput.value.value = filters.from || ''
          }
        }
      } catch (e) { console.warn('applyFavorite update fromInput failed', e) }
      try {
        if (toInput.value) {
          const inst2 = toInput.value._flatpickrInstance || toInput.value._flatpickr
          const d2 = parseDate(filters.to)
          if (inst2 && typeof inst2.setDate === 'function') {
            if (d2) inst2.setDate(d2, true)
            else inst2.clear()
          } else {
            toInput.value.value = filters.to || ''
          }
        }
      } catch (e) { console.warn('applyFavorite update toInput failed', e) }

      try {
        if (durationInput.value) {
          const inst3 = durationInput.value._flatpickrInstance || durationInput.value._flatpickr
          const dstrRaw = filters.duration ?? ''
          const dstr = String(dstrRaw).trim()

          // normalize duration into "start - end" when it's an array or comma-separated
          let normDur = dstr
          if (Array.isArray(dstrRaw)) {
            normDur = dstrRaw.map(x => String(x || '').trim()).filter(Boolean).join(' - ')
          } else if (dstr.indexOf(',') !== -1 && !dstr.includes(' - ')) {
            normDur = dstr.split(',').map(x => String(x || '').trim()).filter(Boolean).join(' - ')
          }
          // store normalized value back into filters so logs show the desired format
          try { filters.duration = normDur } catch (e) {}

          const dstrUsed = normDur

          const parseTimeToDate = (s) => {
            if (!s) return null
            const parts = String(s).split(':').map(x => parseInt(x, 10) || 0)
            const d = new Date()
            d.setHours(parts[0] || 0, parts[1] || 0, parts[2] || 0, 0)
            return d
          }

          if (inst3 && typeof inst3.setDate === 'function') {
            try {
              if (inst3.config) inst3.config.rangeSeparator = ' - '
            } catch (e) {}

            if (!dstrUsed) {
              inst3.clear()
            } else if (dstrUsed.includes(' - ')) {
              const [startStr, endStr] = dstrUsed.split(' - ').map(x => x.trim())
              const sd = parseTimeToDate(startStr)
              const ed = parseTimeToDate(endStr)
              if (sd && ed) {
                inst3.setDate([sd, ed], true)
                // ensure the input shows the desired separator after flatpickr updates it
                setTimeout(() => {
                  try { if (durationInput.value && 'value' in durationInput.value) durationInput.value.value = dstrUsed } catch (e) {}
                }, 50)
              } else if (sd) {
                inst3.setDate(sd, true)
                setTimeout(() => {
                  try { if (durationInput.value && 'value' in durationInput.value) durationInput.value.value = startStr } catch (e) {}
                }, 50)
              } else {
                inst3.clear()
              }
            } else if (dstrUsed.indexOf(':') !== -1) {
              const d = parseTimeToDate(dstrUsed)
              if (d) {
                inst3.setDate(d, true)
                setTimeout(() => {
                  try { if (durationInput.value && 'value' in durationInput.value) durationInput.value.value = dstrUsed } catch (e) {}
                }, 50)
              } else {
                inst3.clear()
              }
            } else {
              try { durationInput.value.value = dstrUsed } catch (e) {}
            }
          } else {
            try { durationInput.value.value = filters.duration || '' } catch (e) {}
          }

          // final safeguard: ensure filter and input remain identical (normalize commas -> ' - ')
          try {
            if (durationInput.value && 'value' in durationInput.value) {
              let val = String(durationInput.value.value || filters.duration || '')
              val = val.replace(/\s*,\s*/g, ' - ')
              filters.duration = val
              durationInput.value.value = val

              // If Flatpickr overwrites the input asynchronously, enforce normalization after it settles
              setTimeout(() => {
                try {
                  if (durationInput.value && 'value' in durationInput.value) {
                    let v2 = String(durationInput.value.value || '')
                    v2 = v2.replace(/\s*,\s*/g, ' - ')
                    if (v2 !== filters.duration) {
                      filters.duration = v2
                      durationInput.value.value = v2
                    }
                  }
                } catch (er) {}
              }, 200)
            }
          } catch (e) {}

          console.log('Applied duration filter', filters.duration, 'parsed as', durationInput.value.value)
        }
      } catch (e) { console.warn('applyFavorite update durationInput failed', e) }

      try {
        const wrap = document.querySelector('.filter-card')
        if (wrap) {
          const groups = wrap.querySelectorAll('.input-group')
          groups.forEach(g => {
            try {
              const input = g.querySelector('input, textarea, select')
              if (!input) return
              const val = input.value
              const has = val !== null && String(val).trim() !== ''
              g.classList.toggle('has-value', has)
            } catch (ign) {}
          })
        }
      } catch (e) { console.warn('applyFavorite sync has-value failed', e) }

      fetchData()
    }catch(e){
      console.error('applyFavorite parse error', e)
    }
  }

  function editFavorite(fav){
    try {
      if (!fav || !fav.id) return
      const idx = favoriteSearchAll.value.findIndex(x => String(x.id) === String(fav.id))
      if (idx === -1) {
        favoriteSearchAll.value.unshift(fav)
      } else {
        favoriteSearchAll.value[idx] = fav
      }
    } catch (e) {
      console.error('editFavorite update error', e)
    }
  }

  function deleteFavorite(id){
    try {
      if (!id) return
      favoriteSearchAll.value = favoriteSearchAll.value.filter(x => String(x.id) !== String(id))
    } catch (e) {
      console.error('deleteFavorite update error', e)
    }
  }

  const resetExportSelections = () => {
    exportSelections.pdf = false
    exportSelections.excel = false
    exportSelections.csv = false
    exportSelections.voice = false
  }

  const onExportFormat = async (formatOrFormats) => {
    if (!canExport.value) return
    let formats = []
    if (typeof formatOrFormats === 'string') formats = [formatOrFormats]
    else if (Array.isArray(formatOrFormats)) formats = formatOrFormats
    else formats = []

    // if voice is requested, ensure at least one row is selected
    const wantVoice = formats.indexOf('voice') !== -1
    const selected = selectedFiles.value || []
    const rowsToExport = (selected && selected.length > 0) ? selected : (paginatedRecords.value || [])
    const exportColumns = (columns.value || []).filter(c => c && c.key !== 'checked')
    if (wantVoice && (!selected || selected.length === 0)) {
      showToast('Please select a row to file audio', 'warning')
      return
    }

    // Determine whether to use folder-like prefix (best-effort)
    const multipleOutput = (selected && selected.length > 1) || (formats.length > 1)

    // fileTypeName used for non-audio exports
    let fileTypeName = 'audio-records_'
    const dateStr = new Date().toISOString().slice(0, 10)
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
    const rangeStart = (startIndex.value || 0) + 1
    const rangeEnd = (startIndex.value || 0) + (rowsToExport ? (rowsToExport.length || 0) : 0)

    // setup download progress helpers
    let startTime = 0
    let totalBytes = 0
    let completedTasks = 0
    const nonVoiceFormats = formats.filter(f => f !== 'voice')
    const totalTasks = nonVoiceFormats.length + (wantVoice ? Math.max(1, selected.length || 0) : 0) || 1
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

    // ensure the downloading modal stays visible at least `minDisplayMs`
    const finishDownloading = (minDisplayMs = 3000) => {
      try {
        const elapsed = Math.max(0, Date.now() - startTime)
        const wait = Math.max(0, minDisplayMs - elapsed)
        setTimeout(() => {
          try {
            // compute a sensible final percentage based on completed tasks
            try {
              const pct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 100
              downloadProgress.value = Math.min(100, Math.max(0, pct))
            } catch (e) {
              downloadProgress.value = Math.min(100, downloadProgress.value ?? 100)
            }
            downloadRemaining.value = ''
            downloadSpeed.value = downloadSpeed.value || '0.0 MB/s'
            downloading.value = false
          } catch (e) { /* ignore */ }
        }, wait)
      } catch (e) { console.warn('finishDownloading failed', e) }
    }

    try {
      // initialize downloading UI
      downloading.value = true
      downloadProgress.value = 0
      downloadSpeed.value = '0 MB/s'
      downloadRemaining.value = ''
      startTime = Date.now()
      // handle voice downloads (non-voice exports will be included in ZIP when possible)
      if (wantVoice) {
        const base = getApiBase().replace(/\/$/, '')
        const toDownloadUrl = (url) => `${url}${url.includes('?') ? '&' : '?'}download=1`
        const downloadFetchOptions = { credentials: 'include', headers: { 'X-Download-Intent': '1' } }

        // helper to load external script (JSZip) when needed
        const loadScript = (src, markerAttr) => new Promise((resolve, reject) => {
          try {
            if (window.JSZip) return resolve()
            if (document.querySelector(`script[${markerAttr}]`)) return resolve()
            const s = document.createElement('script')
            s.src = src
            s.setAttribute(markerAttr, '1')
            s.onload = () => resolve()
            s.onerror = () => reject(new Error('Failed to load script: ' + src))
            document.head.appendChild(s)
          } catch (e) { reject(e) }
        })

        // if multiple outputs (multiple formats or multiple selected files), package into a zip
        if (multipleOutput) {
          try {
            await import('../assets/js/jszip.min.js')
          } catch (e) {
            console.error('Failed to load local JSZip', e)
            showToast('Failed to prepare ZIP download (library load error)', 'error')
          }

          if (window.JSZip) {
            try {
              const zip = new window.JSZip()
              let anyFailed = false
              // include non-voice exports into zip when possible
              try {
                const nonVoice = formats.filter(f => f !== 'voice')
                for (const fmt of nonVoice) {
                  try {
                    const res = await exportTableToFormat(fmt, 'audio', {
                      rows: rowsToExport || [],
                      columns: exportColumns,
                      startIndex: startIndex.value || 0,
                      fileNamePrefix: 'audio-records',
                      returnBlob: true
                    })
                    if (res && res.blob && res.fileName) {
                      zip.file(res.fileName, res.blob)
                      try { markTaskDone(res.blob.size) } catch (e) {}
                    } else {
                      // fallback: trigger normal download for this format
                      anyFailed = true
                      const r2 = await exportTableToFormat(fmt, 'audio', {
                        rows: rowsToExport || [],
                        columns: exportColumns,
                        startIndex: startIndex.value || 0,
                        fileNamePrefix: 'audio-records'
                      })
                      try { if (r2 && r2.blob) markTaskDone(r2.blob.size); else markTaskDone() } catch (e) {}
                    }
                  } catch (e) {
                    anyFailed = true
                    console.error('nonVoice export into zip failed', e)
                    try { markTaskDone() } catch (er) {}
                  }
                }
              } catch (e) {
                console.error('including non-voice into zip failed', e)
              }
                for (const f of selected) {
                const fname = f.file_name || f.fileName || ''
                if (!fname) continue
                const fid = f.file_id || f.id || f.fileId
                const url = fid ? API_PLAY_AUDIO(fid) : API_PROXY_AUDIO(fname)
                try {
                  const resp = await fetch(toDownloadUrl(url), downloadFetchOptions)
                  if (!resp.ok) {
                    anyFailed = true
                    console.error('voice download failed', { url, status: resp.status, statusText: resp.statusText })
                    continue
                  }
                  const blob = await resp.blob()
                  // attempt to get filename from headers
                  let outName = fname
                  try {
                    const cd = resp.headers.get('content-disposition') || ''
                    const m = cd.match(/filename\*=UTF-8''(.+)$|filename="?([^;\n"]+)"?/)
                    if (m) outName = decodeURIComponent((m[1] || m[2] || '').trim()) || outName
                  } catch (e) {}
                  zip.file(outName, blob)
                  try { markTaskDone(blob.size) } catch (er) {}
                } catch (err) {
                  anyFailed = true
                  console.error('voice fetch failed for zip', err)
                  try { markTaskDone() } catch (er) {}
                }
              }
              const zipBlob = await zip.generateAsync({ type: 'blob' })
              const zipName = `Audio record${timestampForName}.zip`
              const a = document.createElement('a')
              a.href = URL.createObjectURL(zipBlob)
              a.download = zipName
              document.body.appendChild(a)
              a.click()
              a.remove()
              setTimeout(() => URL.revokeObjectURL(a.href), 3000)
              if (anyFailed) showToast('Some files failed to download into ZIP', 'warning')
            } catch (e) {
              console.error('ZIP creation failed', e)
              showToast('Failed to create ZIP', 'error')
            }
            return
          }
          // if JSZip not available, fall back to individual downloads
          // ensure non-voice formats are at least downloaded separately
          try {
            const nonVoiceFallback = formats.filter(f => f !== 'voice')
            for (const fmt of nonVoiceFallback) {
              try {
                const res = await exportTableToFormat(fmt, 'audio', {
                  rows: rowsToExport || [],
                  columns: exportColumns,
                  startIndex: startIndex.value || 0,
                  fileNamePrefix: 'audio-records'
                })
                try { if (res && res.blob) markTaskDone(res.blob.size); else markTaskDone() } catch (e) {}
              } catch (e) { console.error('nonVoice fallback export failed', e); try { markTaskDone() } catch (er) {} }
            }
          } catch (e) { console.error('nonVoice fallback loop failed', e) }
        }

        // ensure non-voice exports are handled even when voice is requested
        const nonVoice = formats.filter(f => f !== 'voice')
        if (nonVoice.length > 0) {
          try {
            for (const fmt of nonVoice) {
              try {
                const res = await exportTableToFormat(fmt, 'audio', {
                  rows: rowsToExport || [],
                  columns: exportColumns,
                  startIndex: startIndex.value || 0,
                  fileNamePrefix: 'audio-records',
                  returnBlob: true
                })
                if (res && res.blob) {
                  try {
                    const url = URL.createObjectURL(res.blob)
                    const a = document.createElement('a')
                    a.href = url
                    const extMap = { excel: 'xls', csv: 'csv', pdf: 'pdf' }
                    const ext = extMap[fmt] || fmt
                    a.download = res.fileName || `Audio record${timestampForName}.${ext}`
                    document.body.appendChild(a)
                    a.click()
                    a.remove()
                    setTimeout(() => URL.revokeObjectURL(url), 3000)
                  } catch (e) { console.warn('trigger blob download failed for nonVoice in voice flow', e) }
                  try { markTaskDone(res.blob.size) } catch (e) {}
                } else {
                  try { markTaskDone() } catch (e) {}
                }
              } catch (e) {
                console.error('non-voice export (voice flow) failed', fmt, e)
                try { markTaskDone() } catch (er) {}
              }
            }
          } catch (e) { console.error('processing nonVoice in voice flow failed', e) }
        }

        // fallback or single-file download behavior
        for (const f of selected) {
          const fname = f.file_name || f.fileName || ''
          if (!fname) continue
          const fid = f.file_id || f.id || f.fileId
          const url = fid ? API_PLAY_AUDIO(fid) : API_PROXY_AUDIO(fname)
          try {
            const resp = await fetch(toDownloadUrl(url), downloadFetchOptions)
            if (!resp.ok) {
              console.error('voice download failed', { url, status: resp.status, statusText: resp.statusText })
              showToast(`Failed to download ${fname} (status ${resp.status})`, 'error')
              continue
            }
            const blob = await resp.blob()
            let outName = fname
            try {
              const cd = resp.headers.get('content-disposition') || ''
              const m = cd.match(/filename\*=UTF-8''(.+)$|filename="?([^;\n"]+)"?/)
              if (m) outName = decodeURIComponent((m[1] || m[2] || '').trim()) || outName
            } catch (e) {}
            const safePrefix = (multipleOutput) ? (`Audio record${timestampForName}_`) : ''
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = safePrefix + outName
            document.body.appendChild(a)
            a.click()
            a.remove()
            setTimeout(() => URL.revokeObjectURL(a.href), 3000)
            try { markTaskDone(blob.size) } catch (er) {}
          } catch (err) {
            console.error('voice download error', err)
            showToast(`Failed to download ${fname}`, 'error')
            try { markTaskDone() } catch (er) {}
          }
        }
      }
      // If voice is not requested, handle non-voice exports directly
      if (!wantVoice) {
        try {
          // when multipleOutput (multiple formats or multiple rows), package non-voice exports into a ZIP
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
                    const res = await exportTableToFormat(fmt, 'audio', {
                      rows: rowsToExport || [],
                      columns: exportColumns,
                      startIndex: startIndex.value || 0,
                      fileNamePrefix: 'audio-records',
                      returnBlob: true
                    })
                    if (res && res.blob) {
                      const extMap = { excel: 'xls', csv: 'csv', pdf: 'pdf' }
                      const ext = extMap[fmt] || fmt
                      const name = res.fileName || `Audio record${timestampForName}.${ext}`
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
                const zipName = `Audio record${timestampForName}.zip`
                const a = document.createElement('a')
                a.href = URL.createObjectURL(zipBlob)
                a.download = zipName
                document.body.appendChild(a)
                a.click()
                a.remove()
                setTimeout(() => URL.revokeObjectURL(a.href), 3000)
                if (anyFailed) showToast('Some exports failed while creating ZIP', 'warning')
                finishDownloading()
                return
              }
            } catch (e) {
              console.error('ZIP creation for non-voice failed', e)
            }
            // if JSZip not available or failed, fall through to individual downloads
          }

          // per-format downloads (single-output case or JSZip fallback)
          for (const fmt of formats) {
            try {
              const res = await exportTableToFormat(fmt, 'audio', {
                rows: rowsToExport || [],
                columns: exportColumns,
                startIndex: startIndex.value || 0,
                fileNamePrefix: 'audio-records'
              })
              try { if (res && res.blob) markTaskDone(res.blob.size); else markTaskDone() } catch (e) {}
            } catch (e) {
              console.error('non-voice export failed', fmt, e)
              try { showToast(`Export ${fmt} failed`, 'error') } catch (er) {}
            }
          }
        } catch (e) {
          console.error('handle non-voice exports failed', e)
          try { showToast('Export failed', 'error') } catch (er) {}
        }
        // finish progress for non-voice-only flows (ensure min display time)
        finishDownloading()
        return
      }
    } catch (err) {
      console.error('onExportFormat error', err)
      showToast('Export failed', 'error')
    }
    finally {
      // ensure downloading is turned off after operations finish
      try {
        if (downloading.value) {
          finishDownloading()
        }
      } catch (e) {}
    }
  }

  const confirmExport = async () => {
    const picks = []
    if (exportSelections.pdf) picks.push('pdf')
    if (exportSelections.excel) picks.push('excel')
    if (exportSelections.csv) picks.push('csv')
    if (exportSelections.voice) picks.push('voice')
    if (picks.length === 0) {
      showToast('Please select an export format', 'warning')
      return
    }
    exportOpen.value = false
    await onExportFormat(picks)
    resetExportSelections()
  }

  const cancelExport = () => {
    resetExportSelections()
    exportOpen.value = false
  }

  const callDirectionClass = (dir) => {
    if (!dir) return 'bg-secondary'
    const key = String(dir).toLowerCase()
    if (key === 'internal') return 'badge-warning'
    if (key === 'inbound') return 'badge-success'
    if (key === 'outbound') return 'badge-primary'
    return 'bg-secondary'
  }

  const fetchActiveColumns = async () => {
    try {
      const res = await fetch(API_GET_COLUMN_AUDIO_RECORD() + '?active=true', { credentials: 'include' })
      if (!res.ok) return
      const json = await res.json()
      if (json.data && json.data.length > 0) {
        const activeConfig = json.data[0]
        let raw = activeConfig.raw_data
        let keys = []

        if (typeof raw === 'string') {
          if (raw.startsWith('{') && raw.endsWith('}')) {
            const content = raw.substring(1, raw.length - 1)
            if (content) {
              keys = content.split(',').map(s => s.trim().replace(/^"|"$/g, ''))
            }
          } else {
            try { keys = JSON.parse(raw) } catch (e) { console.warn('Parse raw_data failed', e) }
          }
        } else if (Array.isArray(raw)) {
          keys = raw
        }

        if (keys.length > 0) {
          const newCols = []
          // ensure checked column is present before index
          const checkedCol = defaultColumns.find(c => c.key === 'checked')
          if (checkedCol) newCols.push(checkedCol)
          newCols.push(defaultColumns.find(c => c.key === 'index'))
          keys.forEach(k => {
            const def = defaultColumns.find(c => c.key === k)
            if (def) newCols.push(def)
          })
          columns.value = newCols
        }
      }
    } catch (e) {
      console.error('fetchActiveColumns error', e)
    }
  }

  const onRowDblClick = async (row) => {
    if (!authStore.hasPermission('Playback Audio Records')) {
      showToast('Access Denied', 'error')
      return
    }
    if (!row) return
    const fileName = row.file_name || row.fileName || ''
    if (!fileName) return

    const ext = (fileName.split('.').pop() || '').toLowerCase()

    // The new API_PLAY_AUDIO endpoint handles transcoding for telephony codecs (G.711, etc.)
    // We now attempt in-browser playback for all standard audio extensions, 
    // and if the backend detects an incompatible codec, it will transcode to WAV on-the-fly.
    if (['wav','mp3','ogg','flac','m4a','aac','gsm'].includes(ext)) {
      try {
        const fileId = row.file_id || row.id || row.fileId
        if (!fileId) {
          console.warn('No fileId found for row, falling back to proxy by name', row)
          audioSrc.value = API_PROXY_AUDIO(fileName)
        } else {
          audioSrc.value = API_PLAY_AUDIO(fileId)
        }
        audioMetadata.fileName = fileName
        audioMetadata.duration = row.duration || ''
        audioMetadata.customerNumber = row.customer_number || row.customerNumber || ''
        audioMetadata.extension = row.extension || ''
        audioMetadata.agent = row.agent || ''
        audioMetadata.callDirection = row.call_direction || ''
        audioMetadata.from = row.from || row.start_datetime || ''
        audioMetadata.to = row.to || row.end_datetime || ''
        // set download flag for AudioPlayer: true/false or null when not provided
        if (typeof row.download === 'undefined') {
          audioMetadata.download = null
        } else {
          const v = row.download
          audioMetadata.download = (v === true)
        }
        showAudioModal.value = true
        const csrfToken = getCsrfToken()
        fetch(API_LOG_PLAY_AUDIO(), {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
          body: JSON.stringify({ status: 'success', detail: `Play audio file: ${audioMetadata.fileName}` })
        }).catch(() => {})
      } catch (e) {
        console.error('Failed to initiate in-browser playback', e)
      }
      return
    }

    const uncPath = `\\\\nichetel-niceplayer\\Users\\Administrator\\Desktop\\Music\\${fileName}`
    const url_check_local_server = 'http://127.0.0.1:54321/check'
    const url_get_credentials = API_GET_CREDENTIALS()
    const url_log_playback = API_LOG_PLAY_AUDIO()

    const sendLog = async (status, detail) => {
      const csrfToken = getCsrfToken()
      fetch(url_log_playback, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
        body: JSON.stringify({ status, detail })
      }).catch(err => console.error('Failed to send log:', err))
    }

    loading.value = true

    try {
      const checkResponse = await fetch(url_check_local_server)
      if (!checkResponse.ok) throw new Error('Local server responded with an error.')
      const checkData = await checkResponse.json()

      if (!checkData.installed) {
        try {
          showToast('The audio file cannot be played. Please contact support to install the software.', 'warning')
        } catch (e) {}
        sendLog('error', `FAIL_NOT_INSTALLED | NICE Player executable not found. File: ${uncPath}`)
        loading.value = false
        return
      }

      const credsResponse = await fetch(url_get_credentials, { credentials: 'include' })
      if (!credsResponse.ok) throw new Error(`Failed to get credentials from server. Status: ${credsResponse.status}`)
      const credentials = await credsResponse.json()
      if (credentials.error) throw new Error(`Server returned an error: ${credentials.error}`)

      const encodedPath = encodeURIComponent(uncPath)
      const encodedUser = encodeURIComponent(credentials.username || '')
      const encodedPass = encodeURIComponent(credentials.password || '')
      const protocolLink = `niceplayer://?path=${encodedPath}&user=${encodedUser}&pass=${encodedPass}`

      try {
        window.location.href = protocolLink

        let checkCount = 0
        const maxChecks = 60
        const pollInterval = setInterval(async () => {
          checkCount++
          try {
            const res = await fetch(url_check_local_server)
            const data = await res.json()
            if (data.running || checkCount >= maxChecks) {
              clearInterval(pollInterval)
              loading.value = false
              if (data.running) sendLog('success', `Play audio file: ${fileName}`)
              else {
                sendLog('warning', `Playback initiated but process not detected: ${uncPath}`)
                try { showToast('NICE Player cannot be opened. Some kind of error may have occurred.', 'warning') } catch (e) {}
              }
            }
          } catch (err) {
            if (checkCount >= maxChecks) {
              clearInterval(pollInterval)
              loading.value = false
            }
          }
        }, 500)
      } catch (e) {
        console.error('Error launching protocol:', e)
        try { showToast('NICE Player cannot be opened. Some kind of error may have occurred.', 'warning') } catch (er) {}
        sendLog('error', `FAIL_PLAYER_ERROR | Error launching protocol for file: ${uncPath}. Error: ${e.message}`)
              loading.value = false
      }

    } catch (error) {
      console.error('Playback process failed:', error)
      try {
        showToast('The audio file cannot be played. Please contact support to install the software.', 'warning')
      } catch (e) {}
      sendLog('error', `FAIL_SeekTrack_Connect_RUNNING | Could not connect to local SeekTrack Connect or another error occurred: ${error.message}. File: ${uncPath}`)
      loading.value = false
    }
  }

  async function pollSaveLogs() {
    const localUrl = 'http://127.0.0.1:54321/get_save_logs'
    const url_log_save_file = API_LOG_SAVE_FILE()
    try {
      const res = await fetch(localUrl)
      if (!res.ok) return
      const data = await res.json()
      if (!data || !Array.isArray(data.logs) || data.logs.length === 0) return

      for (const log of data.logs) {
        try {
          const key = `${log.timestamp || ''}|${log.file_path || log.path || ''}`
          if (processedSaveLogs.has(key)) continue
          processedSaveLogs.add(key)
          const detail = `Time: ${log.timestamp} | Path name: ${log.file_path || log.path || ''}`
          const csrfToken = getCsrfToken()
          fetch(url_log_save_file, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
            body: JSON.stringify({ detail })
          }).catch(err => console.warn('Failed to forward save-log', err))
        } catch (e) { console.warn('process log failed', e) }
      }
    } catch (e) {

    }
  }

  const onRowEdit = (row) => { console.log('edit row', row) }
  const onRowDelete = (row) => { console.log('delete row', row) }
  const onSortChange = ({ column, direction }) => {
    sortColumn.value = column
    sortDirection.value = direction
    fetchData()
  }

  onMounted(() => {
    fetchIndexHome()
    fetchActiveColumns()
    registerRequest(fetchData())
    loadRecentFromStorage()
    document.addEventListener('click', onDocClick)
    try {
      pollSaveLogs()
      // saveLogsInterval = setInterval(pollSaveLogs, 3000)
    } catch (e) { console.warn('start pollSaveLogs failed', e) }
    // file-share: WebSocket-only (server push). Polling removed.
    const checkFileShare = async () => {
      try {
        const res = await fetch(API_CHECK_FILE_SHARE(), { credentials: 'include' })
        if (!res.ok) {
          showFileShareNotification.value = false
          return
        }
        const j = await res.json()
        showFileShareNotification.value = !!(j && j.ok)
      } catch (err) {
        console.error('checkFileShare error', err)
        showFileShareNotification.value = false
      }
    }

    const setupWebSocket = () => {
      try {
        // Prefer same-origin websocket (works when frontend is reverse-proxied to backend)
        let wsUrl = null
        try {
          const loc = window.location
          const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:'
          wsUrl = `${proto}//${loc.host}/ws/notifications/`
        } catch (e) {
          const base = getApiBase().replace(/\/$/, '')
          wsUrl = base.replace(/^http/, 'ws') + '/ws/notifications/'
        }
        console.debug('Connecting FileShare WS ->', wsUrl)
        fileShareWs = new WebSocket(wsUrl)
        fileShareWs.onopen = () => {
          // connected
        }
        fileShareWs.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data)
            if (!data) return
            if (data.type === 'force_logout') {
              // Handled globally by useNotifications (with login-race guard);
              // ignore here to avoid double-trigger.
              return
            }
            if (data && (data.type === 'file_share' || data.type === 'file.share' || data.type === 'file_share')) {
              showFileShareNotification.value = !!data.ok
            }
          } catch (e) { /* ignore malformed */ }
        }
        fileShareWs.onclose = () => {
          showFileShareNotification.value = false
          // attempt a simple reconnect after a short delay
          setTimeout(() => {
            try { setupWebSocket() } catch (e) {}
          }, 5000)
        }
        fileShareWs.onerror = () => {
          try { fileShareWs.close() } catch (e) {}
        }
      } catch (e) {
        console.warn('setupWebSocket failed', e)
      }
    }

    try {
      // initial API check when Home is opened
      checkFileShare().catch(() => {})
      setupWebSocket()
    } catch (e) { console.warn('start fileShare mechanism failed', e) }
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', onDocClick)
    try { if (saveLogsInterval) clearInterval(saveLogsInterval) } catch (e) {}
    // polling removed; ensure websocket closed
    try { if (fileShareWs) { fileShareWs.close(); fileShareWs = null } } catch (e) {}
  })

  const showShareModal = ref(false)

  const openShare = () => { showShareModal.value = true }

  const onCreate = (payload) => { 
    // console.log('Share requested', payload) 
  }

  const state = {
    authStore,
    filters,
    searchQuery,
    searchInputRef,
    perPageOptions,
    perPage,
    currentPage,
    perDropdownOpen,
    perDropdownUp,
    mainDbOptions,
    favoriteSearchAll,
    agentOptions,
    callDirectionOptions,
    perWrap,
    fromInput,
    toInput,
    durationInput,
    exportWrap,
    exportOpen,
    exportSelections,
    recentWrap,
    recentOpen,
    recentList,
    showFavoriteModal,
    showAudioModal,
    audioSrc,
    audioMetadata,
    records,
    totalItems,
    loading,
    sortColumn,
    sortDirection,
    columns,
    canExport,
    totalPages,
    startIndex,
    paginatedRecords,
    startItem,
    endItem,
    pagesToShow,
    selectedFiles,
    selectedCount,
    selectAllChecked,
    showShareModal,
    showFileShareNotification,
    downloading,
    downloadProgress,
    downloadSpeed,
    downloadRemaining,
  }

  const actions = {
    onTyping,
    clearSearchQuery,
    setPerPage,
    toggleRecent,
    applyRecent,
    applyRecentRange,
    applyLatestRecent,
    toggleExport,
    confirmExport,
    cancelExport,
    changePage,
    onSearch,
    onReset,
    applyFavorite,
    editFavorite,
    deleteFavorite,
    onExportFormat,
    onRowDblClick,
    onRowEdit,
    onRowDelete,
    onSortChange,
    toggleRowSelection,
    toggleSelectAll,
    openShare,
    onCreate,
  }

  return {
    ...state,
    ...actions
  }
}
