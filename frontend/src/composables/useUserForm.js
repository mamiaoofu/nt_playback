import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { registerRequest } from '../utils/pageLoad'
import { showToast } from '../assets/js/function-all'
import { API_GROUP_INDEX, API_GET_DATABASE, API_GET_ALL_ROLES_PERMISSIONS, API_CHECK_USERNAME, API_CREATE_USER, API_UPDATE_USER } from '../api/paths'
import { getCsrfToken } from '../api/csrf'

export function useUserForm(props) {
    const loading = ref(false)
    const selectedGroupId = ref(null)
    const usernameCheck = ref(false)

    const route = useRoute()
    const router = useRouter()

    const mode = computed(() => {
        if (props.mode) return props.mode
        try {
            if (!route) return 'add'
            const q = route.query && route.query.mode
            if (q === 'edit') return 'edit'
            const p = (route.path || route.fullPath || '').toString().toLowerCase()
            if (p.includes('/edit')) return 'edit'
            const paramMode = route.params && route.params.mode
            if (paramMode === 'edit') return 'edit'
            return 'add'
        } catch (e) {
            return 'add'
        }
    })

    const form = ref({
        username: '',
        password: '',
        confirmPassword: '',
        firstName: '',
        lastName: '',
        email: '',
        phone: ''
    })

    let _usernameTimer = null

    const getInitialUserId = () => {
        try {
            const d = props.initialData || null
            if (!d) return null
            const up = d.user_profile || d.userProfile || null
            const u = (up && (up.user || up.user_to_edit || up.user)) || (d.user_to_edit && d.user_to_edit) || d.user || null
            if (u && (u.id || u.user_id)) return u.id || u.user_id
            if (d.id) return d.id
            return null
        } catch (e) {
            return null
        }
    }

    const errors = reactive({
        username: false,
        password: false,
        confirmPassword: false,
        firstName: false,
        lastName: false,
        email: false,
        group: false,
        team: false,
        role: false
    })

    watch(() => form.value.username, (val) => {
        usernameCheck.value = false
        errors.username = false
        if (_usernameTimer) clearTimeout(_usernameTimer)
        _usernameTimer = setTimeout(async () => {
            try {
                if (!val || String(val).trim() === '') { usernameCheck.value = false; return }
                const uname = String(val).trim()
                const unameOk = /^[A-Za-z0-9]+$/.test(uname)
                if (!unameOk) {
                    errors.username = 'Username must contain only English letters and numbers'
                    usernameCheck.value = false
                    return
                }
                const userId = getInitialUserId()
                const url = API_CHECK_USERNAME() + `?username=${encodeURIComponent(uname)}` + (userId ? `&user_id=${encodeURIComponent(String(userId))}` : '')
                const res = await fetch(url, { method: 'GET', credentials: 'include' })
                if (!res.ok) { usernameCheck.value = false; return }
                const j = await res.json()
                usernameCheck.value = !!(j && j.is_taken === true)
            } catch (e) {
                console.error('username check error', e)
                usernameCheck.value = false
            }
        }, 400)
    })

    const groups = ref([])
    const teams = ref([])
    const groupTeamsMap = ref({})
    const databases = ref([])

    const passwordVisible = ref(false)
    const confirmPasswordVisible = ref(false)

    const allPermissions = ref([])
    const groupedPermissions = ref({})
    const orderedTypes = [
        'access',
        'audio recording',
        'user management',
        'logs'
    ]
    const typeLabels = {
        'access': 'ACCESS',
        'audio recording': 'AUDIO RECORDING',
        'user management': 'USER MANAGEMENT',
        'logs': 'LOGS'
    }

    for (const t of orderedTypes) groupedPermissions.value[t] = []

    const customRoles = ref([])
    const selectedCustomRoleId = ref(null)
    const otherRoleOpen = ref(false)
    const selectedCustomRoleName = computed(() => {
        const r = customRoles.value.find(x => String(x.id) === String(selectedCustomRoleId.value))
        return r ? r.name : null
    })

    function toggleOtherRoleDropdown() {
        otherRoleOpen.value = !otherRoleOpen.value
    }

    function selectCustomRole(role) {
        if (!role) return
        selectedCustomRoleId.value = role.id
        otherRoleOpen.value = false
        selectedBaseRoleKey.value = null
        errors.role = false
        setSelectedPermissionsFromCustomRole(role.id)
    }

    function clearCustomRole() {
        selectedCustomRoleId.value = null
        otherRoleOpen.value = false
        clearSelectedPermissions()
    }

    function populateFromInitial(data) {
        if (!data) return
        const up = data.user_profile || data.userProfile || null
        const u = up && (up.user || up.user_to_edit || up.user) || (data.user_to_edit && data.user_to_edit) || null
        if (u) {
            if (form && form.value) {
                form.value.username = u.username || u.user_name || ''
                form.value.firstName = u.first_name || u.firstName || ''
                form.value.lastName = u.last_name || u.lastName || ''
                form.value.email = u.email || ''
            }
        }

        if (up && up.phone) {
            if (form && form.value) form.value.phone = up.phone
        } else if (data.phone) {
            if (form && form.value) form.value.phone = data.phone
        }

        const team = up && up.team ? up.team : (data.team || null)
        if (team) {
            const gid = (team.user_group && team.user_group.id) || team.user_group_id || (team.user_group && team.user_group.user_group_id) || null
            if (gid) selectedGroupId.value = String(gid)
            if (team.id) selectedTeamId.value = String(team.id)
        }

        let selD = data.selected_db_id || data.selected_db_ids || data.selected_db_ids_json || data.selected_db_ids_json || data.selected_db_ids || data.selected_db_id
        if (!selD && data.selected_db_id === undefined && data.selected_db_ids === undefined) {
            selD = data.selectedDatabaseIds || data.selected_database_ids
        }
        if (typeof selD === 'string') {
            try { selD = JSON.parse(selD) } catch (e) { selD = selD.replace(/[[\]"]+/g, '').split(',').map(s => s.trim()).filter(Boolean) }
        }
        if (Array.isArray(selD)) {
            selectedDatabaseIds.value = selD.map(x => String(x))
            defaultDatabaseIds.value = [...selectedDatabaseIds.value]
            selectedAllDatabases.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
        }

        const allSelectedFlag = data.all_db_selected || data.all_db_selected === true || data.all_db_selected === 'true'
        if (allSelectedFlag) {
            selectedAllDatabases.value = true
            if (databases.value && databases.value.length > 0) {
                selectedDatabaseIds.value = databases.value.map(d => String(d.id))
                defaultDatabaseIds.value = [...selectedDatabaseIds.value]
                selectedAllDatabases.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
            }
        }

        const selRoleType = data.selected_role_type || data.selected_role_type_json || data.selectedRoleType || null
        const selRoleId = data.selected_role_id || data.selected_role_id_json || data.selectedRoleId || null
        if (selRoleType && ['administrator', 'auditor', 'operator'].includes(selRoleType)) {
            selectedBaseRoleKey.value = selRoleType
            selectedCustomRoleId.value = null
        } else if (selRoleId) {
            selectedCustomRoleId.value = String(selRoleId)
            selectedBaseRoleKey.value = null
        }
    }

    function clearUserInfo() {
        clearSelectedPermissions()
        selectedBaseRoleKey.value = null
        selectedCustomRoleId.value = null
        otherRoleOpen.value = false

        passwordVisible.value = false
        confirmPasswordVisible.value = false

        try {
            const userCard = document.querySelector('.card-left')
            if (userCard) {
                userCard.querySelectorAll('input').forEach(inp => {
                    if (inp.type === 'checkbox' || inp.type === 'radio') inp.checked = false
                    else inp.value = ''
                })
                userCard.querySelectorAll('.input-group.has-value').forEach(el => el.classList.remove('has-value'))
            }
        } catch (e) {
            console.warn('clearUserInfo: failed to clear inputs', e)
        }

        if (form && form.value) {
            form.value.username = ''
            form.value.password = ''
            form.value.confirmPassword = ''
            form.value.firstName = ''
            form.value.lastName = ''
            form.value.email = ''
            form.value.phone = ''
        }

        selectedGroupId.value = null
        selectedTeamId.value = null
    }

    function clearDatabaseScope() {
        selectedDatabaseIds.value = []
        selectedAllDatabases.value = false
    }

    async function submit() {
        errors.username = false
        errors.password = false
        errors.confirmPassword = false
        errors.firstName = false
        errors.lastName = false
        errors.email = false
        errors.phone = false
        errors.group = false
        errors.team = false

        let hasError = false
        if (!form.value.username || String(form.value.username).trim() === '') { errors.username = 'This field is required.'; hasError = true }
        else {
            const uname = String(form.value.username).trim()
            if (!/^[A-Za-z0-9]+$/.test(uname)) { errors.username = 'Username must contain only English letters and numbers'; hasError = true }
        }
        if (mode && mode.value !== 'edit') {
            if (!form.value.password || String(form.value.password).trim() === '') { errors.password = 'This field is required.'; hasError = true }
            else if (String(form.value.password).length < 8) { errors.password = 'Password must be at least 8 characters long'; hasError = true }
            if (!form.value.confirmPassword || String(form.value.confirmPassword).trim() === '') { errors.confirmPassword = 'This field is required.'; hasError = true }
            if (form.value.password && form.value.confirmPassword && form.value.password !== form.value.confirmPassword) { errors.confirmPassword = 'Passwords do not match'; hasError = true }
        }
        if (!form.value.firstName || String(form.value.firstName).trim() === '') { errors.firstName = 'This field is required.'; hasError = true }
        else if (!/^[\p{L}\s]+$/u.test(String(form.value.firstName).trim())) { errors.firstName = 'Special characters are not allowed in first name'; hasError = true }
        if (!form.value.lastName || String(form.value.lastName).trim() === '') { errors.lastName = 'This field is required.'; hasError = true }
        else if (!/^[\p{L}\s]+$/u.test(String(form.value.lastName).trim())) { errors.lastName = 'Special characters are not allowed in last name'; hasError = true }
        if (!selectedGroupId.value) { errors.group = true; hasError = true }
        if (!selectedTeamId.value) { errors.team = true; hasError = true }
        if (form.value.email && String(form.value.email).trim() !== '') {
            const e = String(form.value.email).trim()
            const eok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)
            if (!eok) { errors.email = 'Please enter a valid email address'; hasError = true }
        }
        if (form.value.phone && String(form.value.phone).trim() !== '') {
            const p = String(form.value.phone).trim()
            if (!/^[0-9]+$/.test(p)) { errors.phone = 'Phone must contain only numbers'; hasError = true }
        }
        if (!selectedBaseRoleKey.value && !selectedCustomRoleId.value) { errors.role = true; hasError = true }

        if (hasError) {
            try {
                await nextTick()
                const validates = Array.from(document.querySelectorAll('.validate'))
                    .filter(el => el.offsetParent !== null)
                if (validates.length) {
                    const first = validates[0]
                    const group = first.closest('.input-group') || first
                    try { group.scrollIntoView({ behavior: 'smooth', block: 'center' }) } catch (e) { first.scrollIntoView() }
                }
            } catch (e) {
                console.error('scroll to validation error failed', e)
            }
            return
        }

        const fd = new FormData()
        fd.append('username', form.value.username || '')
        if (form.value.password) fd.append('password', form.value.password)
        fd.append('first_name', form.value.firstName || '')
        fd.append('last_name', form.value.lastName || '')
        if (form.value.email) fd.append('email', form.value.email)
        if (form.value.phone) fd.append('phone', form.value.phone)

        if (selectedCustomRoleId.value) fd.append('role', selectedCustomRoleId.value)
        else if (selectedBaseRoleKey.value) fd.append('role', selectedBaseRoleKey.value)

        if (selectedTeamId.value) fd.append('team', selectedTeamId.value)
        if (selectedGroupId.value) fd.append('group', selectedGroupId.value)

        if (selectedAllDatabases.value) {
            fd.append('db_id-all', 'all')
        } else {
            for (const db of databases.value || []) {
                const key = `db_id-${db.id}`
                if (selectedDatabaseIds.value.includes(String(db.id))) fd.append(key, 'on')
            }
        }

        try {
            const perms = Object.keys(selectedPermissions.value).filter(k => selectedPermissions.value[k])
            fd.append('permissions', JSON.stringify(perms))
        } catch (e) { }

        let url = API_CREATE_USER()
        let method = 'POST'
        const initialUserId = getInitialUserId()
        if (mode && mode.value === 'edit') {
            const id = initialUserId || route.params.id || route.query.user_id
            if (id) {
                url = API_UPDATE_USER(id)
            } else {
                fd.append('user_id', initialUserId || '')
                url = API_CREATE_USER()
            }
        }

        try {
            loading.value = true
            const csrfToken = getCsrfToken()
            const res = await fetch(url, { method, credentials: 'include', body: fd, headers: { 'X-CSRFToken': csrfToken || '' } })
            const j = res.ok ? await res.json() : null
            if (!res.ok) {
                showToast(`Error: Request failed`, 'error')
                return
            }
            if (j && j.status === 'success') {
                try {
                    const name = form.value.firstName || form.value.username || ''
                    if (mode && mode.value === 'edit') {
                        try {
                            const pendingUser = {
                                username: form.value.username || '',
                                first_name: form.value.firstName || '',
                                last_name: form.value.lastName || '',
                                email: form.value.email || '',
                                id: initialUserId || null,
                                mode: 'edit'
                            }
                            localStorage.setItem('pending_user', JSON.stringify(pendingUser))
                        } catch (e) { }
                        try {
                            showToast(`Edit ${name} successfully`, 'success')
                        } catch (e) { console.error('showToast error', e) }
                        try { router.push('/user-management') } catch (e) { try { router.back() } catch (er) { /* ignore */ } }
                    } else {
                        try {
                            const toast = { message: `Create ${name} successfully`, type: 'success' }
                            localStorage.setItem('pending_toast', JSON.stringify(toast))
                        } catch (e) { }
                        try {
                            const pendingUser = {
                                username: form.value.username || '',
                                first_name: form.value.firstName || '',
                                last_name: form.value.lastName || '',
                                email: form.value.email || '',
                                id: initialUserId || null,
                                mode: mode && mode.value ? mode.value : 'add'
                            }
                            localStorage.setItem('pending_user', JSON.stringify(pendingUser))
                        } catch (e) { }
                        try { router.push('/user-management') } catch (e) { router.back() }
                    }
                } catch (e) { console.error('redirect error', e) }
                return
            } else {
                const msg = (j && (j.message || j.error)) || 'Unknown error'
                showToast(`Error: ${msg}`, 'error')
                return
            }
        } catch (e) {
            console.error('submit error', e)
            showToast(`submit error ${e.message || e}`, 'error')
        } finally {
            loading.value = false
        }
    }

    function cancel() {
        try { router.back() } catch (e) { router.push('/user-management') }
    }

    function setSelectedPermissionsFromCustomRole(roleId) {
        const role = customRoles.value.find(r => String(r.id) === String(roleId))
        clearSelectedPermissions()
        if (!role) return
        let permNames = []
        if (Array.isArray(role.permissions)) {
            permNames = role.permissions.flat(Infinity).map(x => String(x || '').trim().toLowerCase()).filter(Boolean)
        }

        for (const p of allPermissions.value) {
            const pname = String(p.name || p.action || '').trim().toLowerCase()
            const matched = permNames.some(rn => rn === pname || rn.includes(pname) || pname.includes(rn))
            if (matched) selectedPermissions.value[p.action] = true
        }
    }

    const buildGroupTeamsMap = (groupList, teamList) => {
        const map = {}
        for (const g of groupList) map[g.id] = []
        for (const t of teamList) {
            const gid = t.user_group_id || t.user_group || t.user_group_id_id || t.user_group_id
            if (gid != null && map[gid]) map[gid].push(t)
        }
        return map
    }

    const groupOptions = computed(() => {
        return groups.value.map(g => ({
            value: String(g.id || g.user_group_id || g.user_group || ''),
            label: g.group_name || g.group || g.name || (g.user_group && g.user_group.group_name) || g.user_group || ''
        }))
    })

    const selectedTeamId = ref(null)
    const selectedDatabaseIds = ref([])
    const selectedAllDatabases = ref(false)
    const defaultDatabaseIds = ref([])

    function toggleDatabase(db) {
        const idStr = String(db.id)
        const idx = selectedDatabaseIds.value.indexOf(idStr)
        if (idx === -1) selectedDatabaseIds.value.push(idStr)
        else selectedDatabaseIds.value.splice(idx, 1)
        selectedAllDatabases.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
    }

    watch(selectedTeamId, (teamId) => {
        if (selectedDatabaseIds.value && selectedDatabaseIds.value.length > 0) {
            if (!teamId) selectedDatabaseIds.value = []
            return
        }

        if (!teamId) {
            selectedDatabaseIds.value = []
            return
        }
        const team = teams.value.find(t => String(t.id) === String(teamId))
        if (!team) return
        let mains = []
        try {
            if (typeof team.maindatabase === 'string') mains = JSON.parse(team.maindatabase)
            else if (Array.isArray(team.maindatabase)) mains = team.maindatabase
        } catch (e) {
            if (typeof team.maindatabase === 'string') {
                mains = team.maindatabase.replace(/[[\]\"]+/g, '').split(',').map(s => s.trim()).filter(Boolean)
            }
        }
        selectedDatabaseIds.value = mains.map(x => String(x))
        defaultDatabaseIds.value = [...selectedDatabaseIds.value]
        selectedAllDatabases.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
    })

    function resetDatabase() {
        selectedDatabaseIds.value = [...defaultDatabaseIds.value]
        selectedAllDatabases.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
    }

    function toggleAllDatabases() {
        selectedAllDatabases.value = !selectedAllDatabases.value
        if (selectedAllDatabases.value) {
            selectedDatabaseIds.value = databases.value.map(d => String(d.id))
        } else {
            selectedDatabaseIds.value = []
        }
    }

    const baseRoles = ref({})
    const selectedBaseRoleKey = ref(null)
    const selectedPermissions = ref({})

    const permissionInputsEnabled = computed(() => {
        if (mode && mode.value === 'edit') return true
        return !!selectedBaseRoleKey.value || !!selectedCustomRoleId.value
    })

    const roleCardsDisabled = computed(() => false)

    function clearSelectedPermissions() {
        selectedPermissions.value = {}
    }

    function selectBaseRole(roleKey) {
        if (!roleKey) return
        if (selectedBaseRoleKey.value === roleKey) {
            selectedBaseRoleKey.value = null
            clearSelectedPermissions()
            return
        }

        selectedBaseRoleKey.value = roleKey
        selectedCustomRoleId.value = null
        errors.role = false

        clearSelectedPermissions()
        const br = baseRoles.value && baseRoles.value[roleKey]
        if (br && Array.isArray(br.permissions)) {
            const perms = br.permissions.flat().map(p => p.toString().trim())
            for (const p of perms) selectedPermissions.value[p] = true
        }
    }

    function applyBaseRolePermissions(roleKey) {
        if (!roleKey) return
        selectedBaseRoleKey.value = roleKey
        selectedCustomRoleId.value = null
        clearSelectedPermissions()
        const br = baseRoles.value && baseRoles.value[roleKey]
        if (br && Array.isArray(br.permissions)) {
            const perms = br.permissions.flat().map(p => p.toString().trim())
            for (const p of perms) selectedPermissions.value[p] = true
        }
    }

    function togglePermission(perm) {
        if (!permissionInputsEnabled.value) return
        const k = perm.action
        selectedPermissions.value[k] = !selectedPermissions.value[k]
    }

    const teamOptions = computed(() => {
        const gid = selectedGroupId.value
        if (!gid) return []
        return teams.value
            .filter(t => {
                const tgid = (t.user_group && (t.user_group.id || t.user_group.user_group_id)) || t.user_group_id || t.user_group_id_id || t.user_group
                return String(tgid) === String(gid)
            })
            .map(t => ({ value: String(t.id || t.user_team_id || t.id || ''), label: t.name || t.team_name || t.name }))
    })

    watch(selectedGroupId, (val, old) => {
        if (old !== null && old !== undefined && String(old) !== String(val)) {
            selectedTeamId.value = null
        }
    })

    const fetchData = async () => {
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
                try {
                    const dbRes = await fetch(API_GET_DATABASE(), { credentials: 'include' })
                    if (dbRes.ok) {
                        const dbJson = await dbRes.json()
                        if (Array.isArray(dbJson.results)) {
                            databases.value = dbJson.results
                        } else if (Array.isArray(dbJson)) {
                            databases.value = dbJson
                        } else if (Array.isArray(dbJson.main_db)) {
                            databases.value = dbJson.main_db
                        } else if (Array.isArray(dbJson.databases)) {
                            databases.value = dbJson.databases
                        } else {
                            databases.value = []
                        }
                        if (selectedAllDatabases.value) {
                            selectedDatabaseIds.value = databases.value.map(d => String(d.id))
                            defaultDatabaseIds.value = [...selectedDatabaseIds.value]
                            selectedAllDatabases.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
                        }
                    } else {
                        console.error('Failed to fetch databases', dbRes.status)
                    }
                } catch (dbError) {
                    console.error('Error fetching databases:', dbError)
                }
            } catch (error) {
                console.error('Error fetching groups:', error)
            } finally {
                loading.value = false
            }
        })()
        registerRequest(task)
        await task
    }

    const fetchGetAllRolesPermissions = async () => {
        const task = (async () => {
            loading.value = true
            try {
                const res = await fetch(API_GET_ALL_ROLES_PERMISSIONS(), { credentials: 'include' })
                if (!res.ok) {
                    console.error('Failed to fetch get all roles permissions', res.status)
                    return
                }
                const json = await res.json()
                const perms = Array.isArray(json.all_permissions) ? json.all_permissions : []
                allPermissions.value = perms
                customRoles.value = Array.isArray(json.custom_roles) ? json.custom_roles : []
                baseRoles.value = json.base_roles || {}

                const map = {}
                for (const t of orderedTypes) map[t] = []
                for (const p of perms) {
                    const t = (p.type || '').toString().trim().toLowerCase()
                    if (!map[t]) map[t] = []
                    map[t].push(p)
                }
                for (const t of orderedTypes) {
                    groupedPermissions.value[t] = map[t] || []
                }

                if (selectedBaseRoleKey.value) {
                    applyBaseRolePermissions(selectedBaseRoleKey.value)
                } else if (selectedCustomRoleId.value) {
                    setSelectedPermissionsFromCustomRole(selectedCustomRoleId.value)
                }

            } catch (error) {
                console.error('Error fetching permissions:', error)
            } finally {
                loading.value = false
            }
        })()
        registerRequest(task)
        await task
    }
    onMounted(() => {
        fetchData()
        fetchGetAllRolesPermissions()
    })

    onMounted(() => {
        if (props.initialData) populateFromInitial(props.initialData)
    })

    watch(() => props.initialData, (val) => {
        if (val) populateFromInitial(val)
    })

    watch(() => form.value.firstName, (val) => {
        if (!val || String(val).trim() === '') {
            errors.firstName = false
            return
        }
        const v = String(val).trim()
        if (!/^[\p{L}\s]+$/u.test(v)) errors.firstName = 'Special characters are not allowed in first name'
        else errors.firstName = false
    })

    watch(() => form.value.lastName, (val) => {
        if (!val || String(val).trim() === '') {
            errors.lastName = false
            return
        }
        const v = String(val).trim()
        if (!/^[\p{L}\s]+$/u.test(v)) errors.lastName = 'Special characters are not allowed in last name'
        else errors.lastName = false
    })

    watch(() => form.value.password, (val) => {
        if (!val || String(val).trim() === '') {
            errors.password = false
        } else if (String(val).length < 8) {
            errors.password = 'Password must be at least 8 characters long'
        } else {
            errors.password = false
        }
        if (form.value.confirmPassword && String(form.value.confirmPassword).trim() !== '') {
            if (val !== form.value.confirmPassword) errors.confirmPassword = 'Passwords do not match'
            else errors.confirmPassword = false
        }
    })

    watch(() => form.value.confirmPassword, (val) => {
        if (!val || String(val).trim() === '') { errors.confirmPassword = false; return }
        if (form.value.password !== val) errors.confirmPassword = 'Passwords do not match'
        else errors.confirmPassword = false
    })

    watch(() => selectedGroupId.value, (v) => { if (v) errors.group = false })
    watch(() => selectedTeamId.value, (v) => { if (v) errors.team = false })

    watch(() => form.value.email, (val) => {
        if (!val || String(val).trim() === '') { errors.email = false; return }
        const e = String(val).trim()
        const eok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)
        errors.email = eok ? false : 'Please enter a valid email address'
    })

    watch(() => form.value.phone, (val) => {
        if (!val || String(val).trim() === '') { errors.phone = false; return }
        const v = String(val)
        const digits = v.replace(/\D+/g, '')
        if (digits !== v) {
            try { if (form && form.value) form.value.phone = digits } catch (e) { }
        }
        errors.phone = digits.length > 0 ? false : 'Phone must contain only numbers'
    })

    const state = {
        loading,
        selectedGroupId,
        usernameCheck,
        mode,
        form,
        errors,
        groups,
        teams,
        groupTeamsMap,
        databases,
        passwordVisible,
        confirmPasswordVisible,
        allPermissions,
        groupedPermissions,
        orderedTypes,
        typeLabels,
        customRoles,
        selectedCustomRoleId,
        otherRoleOpen,
        selectedCustomRoleName,
        groupOptions,
        selectedTeamId,
        selectedDatabaseIds,
        selectedAllDatabases,
        defaultDatabaseIds,
        baseRoles,
        selectedBaseRoleKey,
        selectedPermissions,
        permissionInputsEnabled,
        roleCardsDisabled,
        teamOptions
    }

    const actions = {
        toggleOtherRoleDropdown,
        selectCustomRole,
        clearCustomRole,
        populateFromInitial,
        clearUserInfo,
        clearDatabaseScope,
        submit,
        cancel,
        setSelectedPermissionsFromCustomRole,
        toggleDatabase,
        resetDatabase,
        toggleAllDatabases,
        clearSelectedPermissions,
        selectBaseRole,
        applyBaseRolePermissions,
        togglePermission,
        fetchData,
        fetchGetAllRolesPermissions
    }

    return {
        ...state,
        ...actions
    }
}