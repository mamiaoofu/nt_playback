import { reactive, ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_AUDIO_LIST, API_HOME_INDEX, API_LOG_PLAY_AUDIO, API_GET_CREDENTIALS, API_LOG_SAVE_FILE, API_GET_COLUMN_AUDIO_RECORD, getApiBase, API_CREATE_FILE_SHARE } from '../api/paths'
import { ensureCsrf, getCsrfToken } from '../api/csrf'
import '../assets/js/jspdf.umd.min.js'
import '../assets/js/jspdf.plugin.autotable.min.js'
import { exportTableToFormat, getCookie, showToast } from '../assets/js/function-all'

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
    file_share: ''
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
  const recentWrap = ref(null)
  const recentOpen = ref(false)
  const recentList = ref([])
  const showFavoriteModal = ref(false)
  const showAudioModal = ref(false)
  const audioSrc = ref('')
  const audioMetadata = reactive({ fileName: '', duration: '', customerNumber: '', extension: '', agent: '', callDirection: '', from: '', to: '' })
  
  const processedSaveLogs = new Set()
  let saveLogsInterval = null

  const records = ref([])
  const totalItems = ref(0)
  const loading = ref(false)

  const sortColumn = ref('')
  const sortDirection = ref('')

  const defaultColumns = [
    { key: 'checked', label: '', sortable: false, width: '1%' },
    { key: 'index', label: '#', isIndex: true, sortable: false },
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
      const entry = {
        file_id: row.file_id ?? row.id ?? row.fileId ?? key,
        file_name: row.file_name ?? row.fileName ?? '',
        customer_number: row.customer_number ?? row.customerNumber ?? '',
        start_datetime: (row.start_datetime ?? row.startDatetime ?? row.start) || ''
      }
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

  const canExport = computed(() => authStore.hasPermission('Export Recordings'))
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
            copy[k] = {
              file_id: r.file_id ,
              file_name: r.file_name ,
              customer_number: r.customer_number ,
              start_datetime: (r.start_datetime ) 
            }
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
    try {
      filters.databaseServer = []
      filters.from = ''
      filters.to = ''
      filters.duration = ''
      filters.fileName = ''
      filters.callDirection = []
      filters.customerNumber = ''
      filters.agent = []
      filters.fullName = ''
      filters.customField = ''
      filters.extension = ''
      filters.file_share = ''
      sortColumn.value = ''
      sortDirection.value = ''
      searchQuery.value = ''
      currentPage.value = 1
      await nextTick()
      try {
        if (fromInput.value) {
          if (fromInput.value._flatpickr && typeof fromInput.value._flatpickr.clear === 'function') {
            fromInput.value._flatpickr.clear()
          } else {
            fromInput.value.value = ''
          }
        }
      } catch (e) { console.warn('clear fromInput failed', e) }
      try {
        if (toInput.value) {
          if (toInput.value._flatpickr && typeof toInput.value._flatpickr.clear === 'function') {
            toInput.value._flatpickr.clear()
          } else {
            toInput.value.value = ''
          }
        }
      } catch (e) { console.warn('clear toInput failed', e) }

      try {
        const wrap = document.querySelector('.filter-card')
        if (wrap) {
          const groups = wrap.querySelectorAll('.input-group')
          groups.forEach(g => {
            try {
              g.classList.remove('has-value')
              const input = g.querySelector('input, textarea, select')
              if (input) input.value = ''
            } catch (ign) {}
          })
        }
      } catch (e) { console.warn('clear filter-card values failed', e) }
      await fetchData()
    } catch (e) {
      console.error('onReset error', e)
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
          const dstr = filters.duration
          if (inst3 && typeof inst3.setDate === 'function') {
            if (dstr && dstr.indexOf(':') !== -1) {
              const parts = String(dstr).split(':').map(x => parseInt(x, 10) || 0)
              const now = new Date()
              now.setHours(parts[0] || 0, parts[1] || 0, parts[2] || 0, 0)
              inst3.setDate(now, true)
            } else if (!dstr) {
              inst3.clear()
            } else {
              durationInput.value.value = dstr || ''
            }
          } else {
            durationInput.value.value = filters.duration || ''
          }
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

  const onExportFormat = (format) => {
    if (!canExport.value) return
    exportTableToFormat(format, 'audio', {
      rows: paginatedRecords.value || [],
      columns: columns.value || [],
      startIndex: startIndex.value || 0,
      fileNamePrefix: 'audio-records'
    })
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
    if (!authStore.hasPermission('Playback Audio')) {
      showToast('Access Denied', 'error')
      return
    }
    if (!row) return
    const fileName = row.file_name || row.fileName || ''
    if (!fileName) return

    const ext = (fileName.split('.').pop() || '').toLowerCase()
    if (['wav','mp3','ogg','flac'].includes(ext)) {
      try {
        const base = getApiBase().replace(/\/$/, '')
        audioSrc.value = `${base}/media/audio/${encodeURIComponent(fileName)}`
        audioMetadata.fileName = fileName
        audioMetadata.duration = row.duration || ''
        audioMetadata.customerNumber = row.customer_number || row.customerNumber || ''
        audioMetadata.extension = row.extension || ''
        audioMetadata.agent = row.agent || ''
        audioMetadata.callDirection = row.call_direction || ''
        audioMetadata.from = row.from || row.start_datetime || ''
        audioMetadata.to = row.to || row.end_datetime || ''
        showAudioModal.value = true
        const csrfToken = getCsrfToken()
        fetch(API_LOG_PLAY_AUDIO(), {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
          body: JSON.stringify({ status: 'initiated_browser', detail: `Play in-browser file: ${audioSrc.value}` })
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
              if (data.running) sendLog('success', `Playback file: ${uncPath}`)
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
      sendLog('error', `FAIL_NT_Player_Connect_RUNNING | Could not connect to local NT Player Connect or another error occurred: ${error.message}. File: ${uncPath}`)
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
      saveLogsInterval = setInterval(pollSaveLogs, 3000)
    } catch (e) { console.warn('start pollSaveLogs failed', e) }
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', onDocClick)
    try { if (saveLogsInterval) clearInterval(saveLogsInterval) } catch (e) {}
  })

  const showShareModal = ref(false)

  const openShare = () => { showShareModal.value = true }

  const onCreate = (payload) => { 
    console.log('Share requested', payload) 
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
