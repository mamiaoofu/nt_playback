<template>
    <!-- Base Role Modal -->
    <div v-if="modelValue && mode === 'base'" class="modal-backdrop" @click.self="close" id="baseRolesModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div :class="'base-role-modal-icon ' + titleIcon" id="baseRoleModalIcon">
                        <i :class="iconClass"></i>
                    </div>
                    <h3 class="modal-title ad" id="baseRoleModalTitle">{{ title }}</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <div class="permissions-section-title">Permissions</div>
                    <div class="permissions-grid-3" id="baseRolePermissionsGrid">
                        <template v-if="loading">
                            <div class="container-overlay" style="height: 487px;">
                                <div class="overlay-box">Loading...</div>
                            </div>
                        </template>
                        <template v-else>
                            <div v-for="(perms, type) in groupedPermissions" :key="type" class="permission-group">
                                <div class="permission-group-header">{{ type }}</div>
                                <div class="permission-list">
                                    <label v-for="perm in perms" :key="perm.action" class="permission-item">
                                        <input type="checkbox" :value="perm.action" v-model="rolePermissions"
                                            :disabled="checkDisabled" />
                                        <span class="perm-checkbox" aria-hidden></span>
                                        <span class="perm-label">{{ perm.name }}</span>
                                    </label>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-role btn-secondary" @click="onReset" style="margin-right: auto">
                    <i class="fas fa-undo"></i>
                    Reset to Default
                </button>
                <button class="btn-role btn-secondary" @click="close">
                    <i class="fas fa-times"></i>
                    Cancel
                </button>
                <button class="btn-role btn-primary" @click="onSave">
                    <i class="fas fa-save"></i>
                    Save Changes
                </button>
            </div>
        </div>
    </div>

    <!-- Create Role Modal -->
    <div v-if="modelValue && mode === 'create'" class="modal-backdrop" @click.self="close" id="createRolesModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="base-role-modal-icon operator" id="createRoleModalIcon">
                        <i class="fas fa-users-cog"></i>
                    </div>
                    <h3 class="modal-title ad" id="createRoleModalTitle">Create New Role</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <label class="form-label-modal">Role Name</label>
                    <div class="input-group" v-has-value>
                        <input v-model="roleNameInput" required type="text" name="roleNameModal" autocomplete="off" class="input" maxlength="30" :class="{ 'form-input-modal': roleNameError || roleNameCheck }">
                        <label class="title-label">Role Name</label>
                        <div v-show="roleNameCheck || roleNameError" class="validate"><i class="fa-solid fa-circle-exclamation"></i>
                            <span v-if="roleNameCheck">This role name is already in the system.</span>
                            <span v-else>{{ typeof roleNameError === 'string' ? roleNameError : 'This field is required.' }}</span>
                        </div>
                    </div>
                </div>
                <div class="form-group-modal">
                    <div class="permissions-grid-3" id="createRolePermissionsGrid">
                        <template v-if="loading">
                            <div class="container-overlay" style="height: 487px;">
                                <div class="overlay-box">Loading...</div>
                            </div>
                        </template>
                        <template v-else>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <div class="permissions-section-title" style="margin-bottom: 0;">Select Permissions
                                </div>
                                <div style="width: 250px;">
                                    <div class="input-group">
                                        <CustomSelect class="select-search" v-model="filters.roleAll" :options="roleAllOptions" placeholder="Copy from Role..." name="copyRoleModal" />
                                    </div>
                                </div>
                            </div>
                            <div v-for="(perms, type) in groupedPermissions" :key="type" class="permission-group">
                                <div class="permission-group-header">{{ type }}</div>
                                <div class="permission-list">
                                    <label v-for="perm in perms" :key="perm.action" class="permission-item">
                                        <input type="checkbox" :value="perm.action" v-model="rolePermissions" :disabled="checkDisabled" />
                                        <span class="perm-checkbox" aria-hidden></span>
                                        <span class="perm-label">{{ perm.name }}</span>
                                    </label>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-role btn-secondary" @click="onReset" style="margin-right: auto">
                    <i class="fas fa-undo"></i>
                    Reset
                </button>
                <button class="btn-role btn-secondary" @click="close">
                    <i class="fas fa-times"></i>
                    Cancel
                </button>
                <button class="btn-role btn-primary" @click="onSave">
                    <i class="fas fa-save"></i>
                    Save Changes
                </button>
            </div>
        </div>
    </div>

    <!-- Edit Role Modal -->
    <div v-if="modelValue && mode === 'edit'" class="modal-backdrop" @click.self="close" id="editRolesModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="base-role-modal-icon operator" id="editRoleModalIcon">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </div>
                    <h3 class="modal-title ad" id="editRoleModalTitle">Edit Role</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <label class="form-label-modal">Role Name</label>
                    <div class="input-group" v-has-value>
                        <input v-model="roleNameInput" required type="text" name="roleNameModal" id="editRoleName" autocomplete="off" class="input" maxlength="30" :class="{ 'form-input-modal': roleNameError || roleNameCheck }">
                        <label class="title-label">Role Name</label>
                        <div v-show="roleNameCheck || roleNameError" class="validate"><i class="fa-solid fa-circle-exclamation"></i>
                            <span v-if="roleNameCheck">This role name is already in the system.</span>
                            <span v-else>{{ typeof roleNameError === 'string' ? roleNameError : 'This field is required.' }}</span>
                        </div>
                    </div>
                </div>
                <div class="form-group-modal">
                    <div class="permissions-section-title">Select Permissions</div>
                    <div class="permissions-grid-3" id="editRolePermissionsGrid">
                        <template v-if="loading">
                            <div class="container-overlay" style="height: 487px;">
                                <div class="overlay-box">Loading...</div>
                            </div>
                        </template>
                        <template v-else>
                            <div v-for="(perms, type) in groupedPermissions" :key="type" class="permission-group">
                                <div class="permission-group-header">{{ type }}</div>
                                <div class="permission-list">
                                    <label v-for="perm in perms" :key="perm.action" class="permission-item">
                                        <input type="checkbox" :value="perm.action" v-model="rolePermissions"
                                            :disabled="checkDisabled" />
                                        <span class="perm-checkbox" aria-hidden></span>
                                        <span class="perm-label">{{ perm.name }}</span>
                                    </label>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-role btn-secondary" @click="onReset" style="margin-right: auto">
                    <i class="fas fa-undo"></i>
                    Reset to Default
                </button>
                <button class="btn-role btn-secondary" @click="close">
                    <i class="fas fa-times"></i>
                    Cancel
                </button>
                <button class="btn-role btn-primary" @click="onSave">
                    <i class="fas fa-save"></i>
                    Save Changes
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { watch, computed, ref } from 'vue'
import CustomSelect from './CustomSelect.vue'
import '../assets/css/components.css'
import { API_GET_DETAILS_ROLE, API_INDEX_ROLE, API_CHECK_ROLE_NAME, API_CREATE_ROLE, API_UPDATE_ROLE } from '../api/paths'
import { getCookie, showToast } from '../assets/js/function-all'
import { ensureCsrf, getCsrfToken } from '../api/csrf'

const props = defineProps({
    modelValue: { type: Boolean, default: false },
    roleId: { type: [String, Number], default: null },
    roleName: { type: String, default: '' },
    mode: { type: String, default: 'base' }
})
const emit = defineEmits(['update:modelValue'])

const close = () => emit('update:modelValue', false)

// Expand a list of action values to include required access actions
function expandWithDependencies(actionsList) {
    const set = new Set(Array.isArray(actionsList) ? actionsList.slice() : [])
    if (!Array.isArray(allPermissions.value)) return Array.from(set)
    const nameToAct = nameToAction.value || {}

    Array.from(set).forEach(actionValue => {
        const perm = (allPermissions.value || []).find(p => p && p.action === actionValue)
        if (!perm || !perm.name) return
        const deps = dependencyMap[String(perm.name).trim()] || []
        deps.forEach(accessName => {
            const accessAction = nameToAct[String(accessName).trim()]
            if (accessAction) set.add(accessAction)
        })
    })

    return Array.from(set)
}

const onReset = () => {
    if (props.mode === 'create') {
        // In create mode Reset should clear the form
        roleNameInput.value = ''
        rolePermissions.value = []
        defaultPermissions.value = []
        roleNameError.value = false
        roleNameCheck.value = false
        filters.value.roleAll = ''
        return
    }

    const expanded = expandWithDependencies(defaultPermissions.value)
    rolePermissions.value = expanded.slice()
    // keep defaultPermissions stable so repeated resets are idempotent
    defaultPermissions.value = expanded.slice()
}

// CSRF handled centrally

const onSave = async () => {
    // clear previous errors
    roleNameError.value = false

    const isBase = props.mode === 'base'
    const name = String(roleNameInput.value || '').trim()

    // For base-role modal, we only send permissions (no name required)
    if (!isBase) {
        if (!name) {
            roleNameError.value = 'This field is required.'
            return
        }
        // if duplicate flag set from watcher, block submit
        if (roleNameCheck.value) {
            roleNameError.value = 'This role name is already in the system.'
            return
        }
    }

    const payload = {
        permissions: Array.isArray(rolePermissions.value) ? rolePermissions.value.slice() : []
    }
    if (!isBase) payload.role_name = name

    let url = API_CREATE_ROLE()
    // treat base modal as an update (edit) for the given roleId
    if ((props.mode === 'edit' || isBase) && props.roleId) {
        url = API_UPDATE_ROLE(props.roleId)
        payload.role_id = props.roleId
    }

    try {
    loading.value = true
    // CSRF token cached at login/startup; use cached token
    const csrfToken = getCsrfToken()
        const res = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            body: JSON.stringify(payload)
        })
        const j = res.ok ? await res.json() : null
        if (!res.ok) {
            console.error('Role save failed', res.status)
            roleNameError.value = 'Request failed'
            return
        }
        if (j && j.status === 'success') {
            const roleObj = (j.role && typeof j.role === 'object') ? j.role : (j.role || { id: j.id || payload.role_id || null, name: payload.role_name || props.roleName })

            if (props.mode === 'create') {
                try { emit('role-created', roleObj) } catch (e) {}
                try { showToast(`Create ${roleObj.name} successfully`, 'success') } catch (e) {}
                try {
                    if (Array.isArray(roleAllOptions.value) && roleAllOptions.value.length > 1 && Array.isArray(roleAllOptions.value[1].options)) {
                        roleAllOptions.value[1].options.unshift({ label: roleObj.name, value: `custom:${roleObj.id}` })
                    }
                } catch (e) {}
                try { roleNameInput.value = ''; rolePermissions.value = []; roleNameCheck.value = false; roleNameError.value = false; filters.value.roleAll = '' } catch (e) {}
            } else if (isBase) {
                // base role updated
                const displayName = props.roleName || (props.roleId === 1 ? 'Administrator' : props.roleId === 2 ? 'Auditor' : props.roleId === 3 ? 'Operator/Agent' : (roleObj.name || 'Role'))
                try { emit('role-updated', roleObj) } catch (e) {}
                try { showToast(`${displayName} successfully`, 'success') } catch (e) {}
                // keep inputs as-is; just clear transient errors
                try { roleNameCheck.value = false; roleNameError.value = false } catch (e) {}
            } else {
                try { emit('role-updated', roleObj) } catch (e) {}
                try { showToast(`Edit ${roleObj.name} successfully`, 'success') } catch (e) {}
                try {
                    if (Array.isArray(roleAllOptions.value) && roleAllOptions.value.length > 1 && Array.isArray(roleAllOptions.value[1].options)) {
                        const opts = roleAllOptions.value[1].options
                        const idx = opts.findIndex(o => String(o.value).endsWith(`:${roleObj.id}`) || o.value === `custom:${roleObj.id}`)
                        if (idx !== -1) opts[idx].label = roleObj.name
                    }
                } catch (e) {}
                try { roleNameInput.value = ''; rolePermissions.value = []; roleNameCheck.value = false; roleNameError.value = false; filters.value.roleAll = '' } catch (e) {}
            }

            close()
            return
        } else {
            const msg = (j && (j.message || j.error)) || 'Unknown error'
            roleNameError.value = msg
            return
        }
    } catch (e) {
        console.error('onSave error', e)
        roleNameError.value = 'An error occurred'
    } finally {
        loading.value = false
    }
}

// using centralized endpoint functions from src/api/paths.js

const loading = ref(false)
const roleNameInput = ref('')
const roleNameCheck = ref(false)
const roleNameError = ref(false)
const allPermissions = ref([])
const rolePermissions = ref([])
const defaultPermissions = ref([])
const adminOrder = ref([])
const isAdministrator = ref(false)
const checkDisabled = computed(() => String(props.roleId) === '1')

// For the "Copy from Role" select
const roleAllOptions = ref([])
const filters = ref({ roleAll: '' })

// debounce timer for role name check
let _roleNameTimer = null

async function fetchIndexRoles() {
    try {
        const res = await fetch(API_INDEX_ROLE(), { credentials: 'include' })
        if (!res.ok) throw new Error('Failed to fetch index roles')
        const json = await res.json()
        const customs = Array.isArray(json.user_permission_other) ? json.user_permission_other : []
        // Build options: base roles first, then custom roles
        const base = [
            { label: 'Administrator', value: 'base:1' },
            { label: 'Auditor', value: 'base:2' },
            { label: 'Operator/Agent', value: 'base:3' }
        ]
        const customOpts = customs.map(r => ({ label: r.name || `Role ${r.id}`, value: `custom:${r.id}` }))
        roleAllOptions.value = [
            { group: 'Base Roles', options: base },
            { group: 'Custom Roles', options: customOpts }
        ]
    } catch (e) {
        console.error('fetchIndexRoles error', e)
        roleAllOptions.value = [
            { group: 'Base Roles', options: base },
            { group: 'Custom Roles', options: [] }
        ]
    }
}

// When user selects an option to copy from, fetch that role's permissions and apply
watch(() => filters.value.roleAll, async (val) => {
    if (!props.modelValue || props.mode !== 'create') return
    if (!val) {
        rolePermissions.value = []
        defaultPermissions.value = []
        return
    }
    const sel = String(val)
    if (sel.startsWith('base:')) {
        const id = sel.split(':')[1]
        try {
            const res = await fetch(API_GET_DETAILS_ROLE() + id, { credentials: 'include' })
            if (!res.ok) throw new Error('Failed to fetch role details')
            const data = await res.json()
            const rp = Array.isArray(data.role_permissions) ? data.role_permissions : []
            rolePermissions.value = rp.slice()
            defaultPermissions.value = Array.isArray(data.default_permissions) ? data.default_permissions : []
        } catch (e) {
            console.error('Error copying base role permissions', e)
        }
    } else if (sel.startsWith('custom:')) {
        const id = sel.split(':')[1]
        try {
            const res = await fetch(API_GET_DETAILS_ROLE() + id, { credentials: 'include' })
            if (!res.ok) throw new Error('Failed to fetch custom role details')
            const data = await res.json()
            const rp = Array.isArray(data.role_permissions) ? data.role_permissions : []
            rolePermissions.value = rp.slice()
            defaultPermissions.value = Array.isArray(data.default_permissions) ? data.default_permissions : []
        } catch (e) {
            console.error('Error copying custom role permissions', e)
        }
    }
})

// watch roleNameInput and debounce-check against backend for duplicate role name
watch(() => roleNameInput.value, (val) => {
    // clear the required-field error when the user starts typing
    if (roleNameError.value === 'This field is required.' && String(val).trim() !== '') {
        roleNameError.value = false
    }
    roleNameCheck.value = false
    if (_roleNameTimer) clearTimeout(_roleNameTimer)
    _roleNameTimer = setTimeout(async () => {
        try {
            if (!val || String(val).trim() === '') { roleNameCheck.value = false; return }
            const name = String(val).trim()
            const url = API_CHECK_ROLE_NAME() + `?role_name=${encodeURIComponent(name)}` + (props.mode === 'edit' && props.roleId ? `&role_id=${encodeURIComponent(String(props.roleId))}` : '')
            const res = await fetch(url, { method: 'GET', credentials: 'include' })
            if (!res.ok) { roleNameCheck.value = false; return }
            const j = await res.json()
            roleNameCheck.value = !!(j && (j.is_taken === true || j.exists === true || j.is_taken))
        } catch (e) {
            console.error('role name check error', e)
            roleNameCheck.value = false
        }
    }, 400)
})

async function fetchRoleDetails(roleId, template = false) {
    if (!roleId) return
    loading.value = true
    const startTime = Date.now()
    try {
        const res = await fetch(API_GET_DETAILS_ROLE() + roleId, { credentials: 'include' })
        if (!res.ok) throw new Error('Failed to fetch role details')
        const data = await res.json()
        if (data && data.status) {
            // always populate the available permissions list
            allPermissions.value = Array.isArray(data.all_permissions) ? data.all_permissions : []

            // if this is the admin role, capture canonical ordering of actions
            if (String(roleId) === '1') {
                adminOrder.value = Array.isArray(data.all_permissions) ? data.all_permissions.map(p => p && p.action).filter(Boolean) : []
            }

            // when not in template mode, populate form inputs (edit flow)
            if (!template) {
                roleNameInput.value = data.role_name || ''
                rolePermissions.value = Array.isArray(data.role_permissions) ? data.role_permissions : []
                defaultPermissions.value = Array.isArray(data.default_permissions) ? data.default_permissions : []
            }

            // fallback for administrator detection
            isAdministrator.value = Boolean(data.is_administrator) || String(roleId) === '1' || (data.role_name && String(data.role_name).toLowerCase() === 'administrator')
        } else {
            allPermissions.value = []
            if (!template) {
                rolePermissions.value = []
                defaultPermissions.value = []
            }
        }
    } catch (e) {
        console.error('Error fetching role details:', e)
        allPermissions.value = []
        if (!template) {
            rolePermissions.value = []
            defaultPermissions.value = []
        }
    } finally {
        // ensure loading indicator is visible at least 1s for UX
        const elapsed = Date.now() - startTime
        const minMs = 500
        if (elapsed < minMs) {
            await new Promise(r => setTimeout(r, minMs - elapsed))
        }
        loading.value = false
    }
}

const title = computed(() => {
    if (props.roleName) return props.roleName
    switch (String(props.roleId)) {
        case '1': return 'Edit Administrator'
        case '2': return 'Edit Auditor'
        case '3': return 'Edit Operator/Agent'
    }
})

const titleIcon = computed(() => {
    switch (String(props.roleId)) {
        case '1': return 'admin'
        case '2': return 'auditor'
        case '3': return 'operator'
    }
})

const iconClass = computed(() => {
    switch (String(props.roleId)) {
        case '1': return 'fas fa-crown'
        case '2': return 'fas fa-clipboard-check'
        case '3': return 'fas fa-headset'
    }
})

watch(() => props.modelValue, async (val) => {
    if (!val) return
    // reset modal state on open so inputs/selects start fresh
    roleNameInput.value = ''
    rolePermissions.value = []
    defaultPermissions.value = []
    roleNameError.value = false
    roleNameCheck.value = false
    filters.value.roleAll = ''
    roleAllOptions.value = []
    allPermissions.value = []
    // prefer legacy initializer only for non-create flows
    if (props.mode !== 'create' && window && typeof window.initBaseRoleModal === 'function') {
        try { window.initBaseRoleModal(props.roleId) } catch (e) { console.error(e) }
    }

    // When opening the modal in `create` mode, use roleId=1 (Administrator) as the
    // source of available permissions but do not pre-fill the create form inputs.
    if (props.mode === 'create') {
        // ensure inputs are empty first (avoid later overwrite/flicker)
        roleNameInput.value = ''
        rolePermissions.value = []
        // Fetch admin permissions as the default available set (template mode: do not populate inputs)
        await fetchRoleDetails(1, true)
        // populate copy-select options
        await fetchIndexRoles()
        // reset copy selection
        filters.value.roleAll = ''
        return
    }

    // ensure we have canonical admin order for consistent sorting
    if (!adminOrder.value || adminOrder.value.length === 0) {
        try { await fetchRoleDetails(1, true) } catch (e) { console.error('failed to fetch admin order', e) }
    }

    // default: fetch details for the provided roleId
    fetchRoleDetails(props.roleId)
})

const groupedPermissions = computed(() => {
    // sort permissions by canonical admin order when available, falling back to numeric `id`
    const ap = (allPermissions.value || []).slice().sort((a, b) => {
        const ia = (adminOrder.value || []).indexOf(a && a.action)
        const ib = (adminOrder.value || []).indexOf(b && b.action)
        if (ia !== -1 || ib !== -1) {
            if (ia === -1) return 1
            if (ib === -1) return -1
            return ia - ib
        }
        return (Number(a.id) || 0) - (Number(b.id) || 0)
    })
    const grouped = ap.reduce((acc, perm) => {
        const type = perm.type || 'Other'
        if (!acc[type]) acc[type] = []
        acc[type].push(perm)
        return acc
    }, {})

    const order = ['access', 'Audio Records', 'Management', 'Role & Permissions', 'Group & Team', 'Logs', 'Settings']
    const keys = Object.keys(grouped).sort((a, b) => {
        const ia = order.indexOf(a.toString().trim())
        const ib = order.indexOf(b.toString().trim())
        if (ia !== -1 && ib !== -1) return ia - ib
        if (ia !== -1) return -1
        if (ib !== -1) return 1
        return a.localeCompare(b)
    })

    const ordered = {}
    keys.forEach(k => ordered[k] = grouped[k])
    return ordered
})

// Map of permission display names -> required access-group permission names
// When a permission (non-access) is selected, ensure these access names are checked.
const dependencyMap = {
    // Access
    // 'Audio Records' : [],
    // 'User Management' : [],
    // 'Delegate Management' : [],
    // 'Ticket Management' : [],
    // 'Role & Permissions' : [],
    // 'Group & Team' : [],
    // 'Audit Log' : [],
    // 'System Log' : [],
    // 'Ticket History' : [],
    // 'Settings' : [],

    // Audio Records
    'Query Audio Records' : ['Audio Records'],
    'Playback Audio Records' : ['Audio Records'],
    'Download Voice File' : ['Audio Records'],
    'Save As Index' : ['Audio Records'],
    'Delegate Files' : ['Audio Records'],

    //Management
    'Add User' : ['User Management'],
    'Edit User' : ['User Management'],
    'Delete User' : ['User Management'],
    'Change User Status' : ['User Management'],
    'Reset User Password' : ['User Management'],
    'Save As User Index' : ['User Management'],
    // 'Create Delegate File' : ['Delegate Management'],
    // 'Download Delegate File' : ['Delegate Management'],
    // 'Change Delegate File Status' : ['Delegate Management'],
    // 'Save As Delegate File Index' : ['Delegate Management'],
    // 'Create Ticket' : ['Ticket Management'],
    // 'Download Ticket File' : ['Ticket Management'],
    // 'Change Ticket Status' : ['Ticket Management'],
    // 'Save As Ticket Index' : ['Ticket Management'],
    'Ticket Resent' : ['Ticket Management'],

    //Role & Permissions
    'Edit Base Roles' : ['Role & Permissions'],
    'Add New Custom Roles' : ['Role & Permissions'],
    'Edit Custom Roles' : ['Role & Permissions'],
    'Delete Custom Roles' : ['Role & Permissions'],

    //Group & Team
    'Add New Group' : ['Group & Team'],
    'Edit Group' : ['Group & Team'],
    'Delete Group' : ['Group & Team'],
    'Add New Team' : ['Group & Team'],
    'Edit Team' : ['Group & Team'],
    'Delete Team' : ['Group & Team'],

    //Logs
    // NOTE: keep 'Save As Audit Log' from automatically removing the 'Audit Log' access
    // when it is unchecked. We'll handle its addition explicitly below so unchecking
    // does not remove the access permission.
    'Save As System Log' : ['System Log'],
    'Save As Ticket History' : ['Ticket History'],
    'Save As Audit Log' : ['Audit Log'],

    //Setting
    'Set Column' : ['Settings'],
    'Download Player' : ['Settings'],

}

// Helper: map permission display name -> action value (from allPermissions)
const nameToAction = computed(() => {
    const m = {}
    ;(allPermissions.value || []).forEach(p => {
        if (p && p.name) m[String(p.name).trim()] = p.action
    })
    return m
})

// Reverse map: access-name -> list of permission names that depend on it
const reverseDependencyMap = computed(() => {
    const rev = {}
    Object.keys(dependencyMap).forEach(name => {
        const deps = dependencyMap[name] || []
        deps.forEach(d => {
            const key = String(d).trim()
            if (!rev[key]) rev[key] = []
            if (rev[key].indexOf(name) === -1) rev[key].push(name)
        })
    })
    return rev
})

const _syncingDeps = ref(false)

// Watch rolePermissions (as a shallow array copy) to add/remove access items
watch(() => rolePermissions.value.slice(), (newArr, oldArr) => {
    if (_syncingDeps.value) return
    _syncingDeps.value = true
    try {
        const added = newArr.filter(v => !oldArr.includes(v))
        const removed = oldArr.filter(v => !newArr.includes(v))

        // Handle additions: ensure access permissions are present
        added.forEach(actionValue => {
            const perm = (allPermissions.value || []).find(p => p && p.action === actionValue)
            if (!perm || !perm.name) return
            const deps = dependencyMap[String(perm.name).trim()] || []
            deps.forEach(accessName => {
                const accessAction = nameToAction.value[String(accessName).trim()]
                if (accessAction && !rolePermissions.value.includes(accessAction)) {
                    rolePermissions.value = rolePermissions.value.concat([accessAction])
                }
            })

            try {
                const specialMap = {
                    'Save As Audit Log': 'Audit Log',
                    'Save As System Log': 'System Log',
                    'Save As Ticket History': 'Ticket History'
                }
                const s = String(perm.name).trim()
                if (specialMap[s]) {
                    const accessAction = nameToAction.value[specialMap[s]]
                    if (accessAction && !rolePermissions.value.includes(accessAction)) {
                        rolePermissions.value = rolePermissions.value.concat([accessAction])
                    }
                }
            } catch (e) { /* silent */ }
        })

        // Handle removals:
        // Only cascade removal downward: if an access-type permission is manually removed,
        // also remove dependent sub-permissions that require it.
        // NOTE: Sub-items being unchecked do NOT automatically uncheck their parent access —
        // the user must uncheck the access (parent) manually.
        removed.forEach(actionValue => {
            const perm = (allPermissions.value || []).find(p => p && p.action === actionValue)
            if (!perm || !perm.name) return

            // If this removed permission is an access-type, remove any dependent permissions that require it
            const revDeps = reverseDependencyMap.value[String(perm.name).trim()] || []
            if (revDeps && revDeps.length) {
                revDeps.forEach(depName => {
                    const depAction = nameToAction.value[String(depName).trim()]
                    if (!depAction) return
                    if ((rolePermissions.value || []).includes(depAction)) {
                        rolePermissions.value = (rolePermissions.value || []).filter(a => a !== depAction)
                    }
                })
            }
        })
    } finally {
        _syncingDeps.value = false
    }
}, { immediate: false })
</script>

<style scoped>
/* Permissions layout */
.permission-group {
    margin-bottom: 22px !important;
}

.permissions-section-title {
    margin-bottom: 8px;
    font-weight: 700
}

.permissions-grid-3 {
    display: block;
    position: relative;
    min-height: 140px
}

.container-overlay {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    background: rgba(255, 255, 255, 0.6);
    border-radius: 8px;
    width: 100%;
    padding-top: 15%;
    box-sizing: border-box
}

.permission-group {
    margin-bottom: 18px
}

.permission-group-header {
    font-weight: 700;
    color: #6c757d;
    margin: 10px 0 8px;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: .02em;
}

.permission-list {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 8px;
}

.permission-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    cursor: pointer;
    transition: all .15s ease;
}

/* responsive: fewer columns on small widths */
@media (max-width: 900px) {
    .permission-list {
        grid-template-columns: repeat(2, 1fr)
    }
}

@media (max-width: 520px) {
    .permission-list {
        grid-template-columns: repeat(1, 1fr)
    }
}

/* make modal body scrollable if content tall */
.modal-body {
    max-height: 454px;
    overflow: auto
}
.form-input-modal {
    border-radius: 25px;
    border: 1px solid rgb(245, 163, 163) !important;
    box-shadow: rgba(220, 53, 69, 0.25) 0px 0px 0px 0.2rem !important;
}
</style>