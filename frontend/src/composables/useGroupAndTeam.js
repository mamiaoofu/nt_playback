import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { registerRequest } from '../utils/pageLoad'
import { API_GROUP_INDEX, API_TEAM_INDEX, API_GET_TEAM_BY_GROUP, API_SAVE_GROUP, API_SAVE_TEAM } from '../api/paths'
import { ensureCsrf, getCsrfToken } from '../api/csrf'
import { showToast, confirmDelete } from '../assets/js/function-all'

export function useGroupAndTeam() {
    const authStore = useAuthStore()
    const searchQuery = ref('')
    const teamSearchQuery = ref('')
    const selectedGroupId = ref(null)

    const groups = ref([])
    const teams = ref([])
    const groupTeamsMap = ref({})
    const loading = ref(false)

    const showGroupModal = ref(false)
    const selectedModalMode = ref('create')
    const editGroup = ref(null)
    const loadingTeamsByGroup = ref(false)

    const filteredGroups = computed(() => {
        const q = (searchQuery.value || '').toLowerCase().trim()
        if (!q) return groups.value
        return groups.value.filter(g => (g.group_name || '').toLowerCase().includes(q))
    })

    const buildGroupTeamsMap = (groupList, teamList) => {
        const map = {}
        for (const g of groupList) map[g.id] = []
        for (const t of teamList) {
            const gid = t.user_group_id || t.user_group || t.user_group_id_id || t.user_group_id
            if (gid != null && map[gid]) map[gid].push(t)
        }
        return map
    }

    const fetchIndexGroup = async () => {
        const task = (async () => {
            loading.value = true
            try {
                const res = await fetch(API_GROUP_INDEX(), { credentials: 'include' })
                if (!res.ok) {
                    console.error('Failed to fetch groups', res.status)
                    return
                }
                const json = await res.json()
                groups.value = Array.isArray(json.user_group) ? json.user_group : []
                teams.value = Array.isArray(json.user_team) ? json.user_team : []
                groupTeamsMap.value = buildGroupTeamsMap(groups.value, teams.value)
            } catch (error) {
                console.error('Error fetching groups:', error)
            } finally {
                loading.value = false
            }
        })()
        registerRequest(task)
        await task
    }

    const filteredTeams = computed(() => {
        const gid = selectedGroupId.value
        if (!gid) return []
        const list = Array.isArray(groupTeamsMap.value[gid]) ? groupTeamsMap.value[gid] : []
        const q = (teamSearchQuery.value || '').toLowerCase().trim()
        if (!q) return list
        return list.filter(t => (t.name || '').toLowerCase().includes(q))
    })

    const selectedGroupName = computed(() => {
        const gid = selectedGroupId.value
        if (!gid) return ''
        const g = groups.value.find(x => (x.id == gid))
        return g ? g.group_name : ''
    })

    function onTyping() {}

    function onSearch() {}

    function selectGroup(group) {
        if (selectedGroupId.value === group.id) {
            selectedGroupId.value = null
            teamSearchQuery.value = ''
            return
        }
        selectedGroupId.value = group.id
        teamSearchQuery.value = ''
    }

    function openCreateGroup() {
        selectedModalMode.value = 'createGroup'
        showGroupModal.value = true
    }

    function openEditGroup(id) {
        const g = groups.value.find(x => x.id == id)
        editGroup.value = g ? { id: g.id, group_name: g.group_name, description: g.description } : { id }
        selectedModalMode.value = 'editGroup'
        showGroupModal.value = true
    }

    async function deleteGroup(id) {
        const confirmed = await confirmDelete()
        if (!confirmed) return
        try {
            const res = await fetch(API_SAVE_GROUP(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ action: 'delete', group_id: id })
            })
            const json = await res.json()
            if (json.status === 'success') {
                showToast('Group deleted successfully', 'success')
                groups.value = groups.value.filter(g => g.id !== id)
                delete groupTeamsMap.value[id]
                if (selectedGroupId.value === id) selectedGroupId.value = null
            } else {
                showToast(json.message || 'Failed to delete group', 'error')
            }
        } catch (e) {
            console.error(e)
            showToast('An error occurred', 'error')
        }
    }

    function onTypingTeam() {}

    function onSearchTeam() {}

    function openCreateTeam() {
        selectedModalMode.value = 'createTeam'
        // pass currently selected group (if any) into the modal so it can preselect
        if (selectedGroupId.value) {
            const g = groups.value.find(x => x.id == selectedGroupId.value)
            editGroup.value = g ? { ...g } : { id: selectedGroupId.value }
        } else {
            editGroup.value = null
        }
        showGroupModal.value = true
    }

    function openEditTeam(id) {
        const t = teams.value.find(x => x.id == id)
        if (t) {
            editGroup.value = {
                id: t.id,
                name: t.name,
                maindatabase: t.maindatabase,
                user_group_id: t.user_group_id || t.user_group || null,
                group_name: groups.value.find(g => g.id == (t.user_group_id || t.user_group))?.group_name || ''
            }
        } else {
            editGroup.value = { id }
        }
        selectedModalMode.value = 'editTeam'
        showGroupModal.value = true
    }

    async function deleteTeam(id) {
        const confirmed = await confirmDelete()
        if (!confirmed) return

        try {
            const res = await fetch(API_SAVE_TEAM(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ action: 'delete', team_id: id })
            })
            const json = await res.json()
            if (json.status === 'success') {
                showToast('Team deleted successfully', 'success')
                teams.value = teams.value.filter(t => t.id !== id)
                for (const gid in groupTeamsMap.value) {
                    groupTeamsMap.value[gid] = groupTeamsMap.value[gid].filter(t => t.id !== id)
                }
            } else {
                showToast(json.message || 'Failed to delete team', 'error')
            }
        } catch (e) {
            console.error(e)
            showToast('An error occurred', 'error')
        }
    }

    function onGroupSaved(payload) {
        if (!payload || !payload.data) return
        const { mode, data } = payload
        if (mode === 'editGroup') {
            const idx = groups.value.findIndex(g => g.id == data.id)
            if (idx !== -1) {
                const updatedGroup = { ...groups.value[idx], group_name: data.group_name, description: data.description }
                groups.value.splice(idx, 1)
                groups.value.unshift(updatedGroup)
            }
        } else if (mode === 'createGroup') {
            const newId = data.id || Date.now()
            groups.value.unshift({ id: newId, group_name: data.group_name, description: data.description, status: 1 })
            groupTeamsMap.value = { ...groupTeamsMap.value, [newId]: [] }
        } else if (mode === 'createTeam') {
            const newTeam = { ...data, status: 1 }
            teams.value.push(newTeam)
            const gid = newTeam.user_group_id || newTeam.user_group
            if (gid) {
                if (!groupTeamsMap.value[gid]) groupTeamsMap.value[gid] = []
                groupTeamsMap.value[gid].push(newTeam)
            }
        } else if (mode === 'editTeam') {
            const idx = teams.value.findIndex(t => t.id == data.id)
            if (idx !== -1) {
                const oldTeam = teams.value[idx]
                const oldGid = oldTeam.user_group_id || oldTeam.user_group
                const newGid = data.user_group_id || data.user_group
                const updatedTeam = { ...oldTeam, ...data }
                teams.value.splice(idx, 1)
                teams.value.unshift(updatedTeam)
                if (oldGid != newGid) {
                    if (groupTeamsMap.value[oldGid]) {
                        groupTeamsMap.value[oldGid] = groupTeamsMap.value[oldGid].filter(t => t.id != data.id)
                    }
                    if (!groupTeamsMap.value[newGid]) groupTeamsMap.value[newGid] = []
                    groupTeamsMap.value[newGid].push(teams.value[idx])
                } else {
                    if (groupTeamsMap.value[oldGid]) {
                        const tIdx = groupTeamsMap.value[oldGid].findIndex(t => t.id == data.id)
                        if (tIdx !== -1) {
                            groupTeamsMap.value[oldGid].splice(tIdx, 1)
                            groupTeamsMap.value[oldGid].unshift(updatedTeam)
                        }
                    }
                }
            }
        }
    }

    onMounted(() => {
        fetchIndexGroup()
    })

    const state = {
        authStore,
        searchQuery,
        teamSearchQuery,
        selectedGroupId,
        groups,
        teams,
        groupTeamsMap,
        loading,
        showGroupModal,
        selectedModalMode,
        editGroup,
        loadingTeamsByGroup,
        filteredGroups,
        filteredTeams,
        selectedGroupName
    }

    const actions = {
        onTyping,
        onSearch,
        selectGroup,
        openCreateGroup,
        openEditGroup,
        deleteGroup,
        onTypingTeam,
        onSearchTeam,
        openCreateTeam,
        openEditTeam,
        deleteTeam,
        onGroupSaved
    }

    return {
        ...state,
        ...actions
    }
}