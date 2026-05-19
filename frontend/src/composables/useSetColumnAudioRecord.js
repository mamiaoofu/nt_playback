import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { API_GET_COLUMN_AUDIO_RECORD, API_SAVE_COLUMN_AUDIO_RECORD } from '../api/paths'
import { registerRequest } from '../utils/pageLoad'
import { showToast, confirmDelete } from '../assets/js/function-all'
import { getCsrfToken } from '../api/csrf'

export function useSetColumnAudioRecord() {
    const searchQuery = ref('')
    const authStore = useAuthStore()
    const columns = ref([])
    const selectedColumnId = ref(null)
    const loading = ref(false)

    const showModal = ref(false)
    const modalMode = ref('createColumn')
    const editColumnData = ref(null)

    const filteredColumns = computed(() => {
        const q = (searchQuery.value || '').toLowerCase().trim()
        if (!q) return columns.value
        return columns.value.filter(c => (c.name || '').toLowerCase().includes(q))
    })

    const fetchGetColumnAudioRecord = async (showLoading = true) => {
        const task = (async () => {
            if (showLoading) loading.value = true
            try {
                const res = await fetch(API_GET_COLUMN_AUDIO_RECORD(), { credentials: 'include' })
                if (!res.ok) return
                const json = await res.json()
                columns.value = json.data || []
            } catch (err) {
                console.error('fetchGetColumnAudioRecord error', err)
            } finally {
                if (showLoading) loading.value = false
            }
        })()
        registerRequest(task)
        await task
    }

    function onTyping() {
        // Client-side filtering handled by computed
    }

    function onSearch() {
        // Client-side filtering handled by computed
    }

    function selectColumn(column) {
        selectedColumnId.value = column.id
    }

    function openCreateGroup() {
        modalMode.value = 'createColumn'
        editColumnData.value = null
        showModal.value = true
    }

    function openEditColumn(id) {
        const col = columns.value.find(c => c.id === id)
        if (col) {
            editColumnData.value = col
            modalMode.value = 'editColumn'
            showModal.value = true
        }
    }

    async function onModalSaved(data) {
        try {
            const csrfToken = getCsrfToken()
            
            const payload = { ...data }
            if (!payload.action) {
                payload.action = (modalMode.value === 'createColumn') ? 'create' : 'update'
            }

            const res = await fetch(API_SAVE_COLUMN_AUDIO_RECORD(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
                body: JSON.stringify(payload)
            })
            
            const json = await res.json()
            if (json.status === 'success') {
                showToast(json.message || 'Saved successfully', 'success')
                showModal.value = false
                fetchGetColumnAudioRecord(false)
            } else {
                showToast(json.message || 'Failed to save', 'error')
            }
        } catch (e) {
            console.error('Error saving column', e)
            showToast('An error occurred', 'error')
        }
    }

    async function deleteColumn(id) {
        const confirmed = await confirmDelete()
        if (!confirmed) return
        
        await onModalSaved({ id, action: 'delete' })
    }

    async function toggleSetColumnUse(userId, column) {
        const newUse = !column.use
        
        const previousColumns = JSON.stringify(columns.value)
        
        if (newUse) {
            columns.value.forEach(c => {
                c.use = (c.id === column.id)
            })
        } else {
            column.use = false
        }

        try {
            const csrfToken = getCsrfToken()
            
            const payload = {
                action: 'toggle',
                id: column.id,
                use: newUse,
                name: column.name,
                description: column.description,
                raw_data: column.raw_data
            }

            const res = await fetch(API_SAVE_COLUMN_AUDIO_RECORD(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
                body: JSON.stringify(payload)
            })
            
            const json = await res.json()
            if (json.status === 'success') {
                showToast(json.message, 'success')
            } else {
                showToast(json.message || 'Failed to update status', 'error')
                columns.value = JSON.parse(previousColumns)
            }
        } catch (e) {
            console.error('Error toggling column', e)
            showToast('An error occurred', 'error')
            columns.value = JSON.parse(previousColumns)
        }
    }

    onMounted(() => {
        fetchGetColumnAudioRecord()
    })

    function clearSearch() {
        searchQuery.value = ''
        nextTick(() => {
        if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') searchInputRef.value.focus()
        })
    }


    const state = {
        searchQuery,
        authStore,
        columns,
        selectedColumnId,
        loading,
        showModal,
        modalMode,
        editColumnData,
        filteredColumns
    }

    const actions = {
        fetchGetColumnAudioRecord,
        onTyping,
        onSearch,
        selectColumn,
        openCreateGroup,
        openEditColumn,
        deleteColumn,
        toggleSetColumnUse,
        onModalSaved,
        clearSearch
    }

    return {
        ...state,
        ...actions
    }
}