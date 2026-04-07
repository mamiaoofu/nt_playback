<template>
    <!-- Create group  -->
    <div v-if="modelValue && mode === 'createGroup'" class="modal-backdrop" @click.self="close" id="createGroupModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="blue-icon" id="createGroupModalIcon">
                        <i class="fa-solid fa-user-group"></i>
                    </div>
                    <h3 class="modal-title ad" id="createGroupModalTitle">Create Group</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <div class="permissions-grid-2" id="groupGrid">
                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                    <div class="input-group" v-has-value>
                                    <input required v-model="name" type="text" name="groupNameModal" autocomplete="off" class="input" :class="{ 'form-input-modal': nameError || nameCheck }" maxlength="30">
                                    <label class="title-label">Group name</label>
                                    <div v-show="nameCheck || nameError" class="validate"><i class="fa-solid fa-circle-exclamation"></i>
                                        <span v-if="nameCheck">This {{ nameType }} name is already in the system.</span>
                                        <span v-else>{{ typeof nameError === 'string' ? nameError : 'This field is required.' }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="form-group-modal">
                                    <div class="input-group" v-has-value>
                                        <input required v-model="description" type="text" name="descriptionModal" autocomplete="off" class="input" maxlength="50">
                                        <label class="title-label">Description</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
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

    <!-- Edit group  -->
    <div v-if="modelValue && mode === 'editGroup'" class="modal-backdrop" @click.self="close" id="editGroupModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="blue-icon" id="editGroupModalIcon">
                        <i class="fa-solid fa-user-group"></i>
                    </div>
                    <h3 class="modal-title ad" id="editGroupModalTitle">Edit Group</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <div class="permissions-grid-2" id="groupGrid">
                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="input-group" v-has-value>
                                    <input required v-model="name" type="text" name="groupNameModal"
                                        autocomplete="off" class="input" :class="{ 'form-input-modal': nameError || nameCheck }" maxlength="30">
                                    <label class="title-label">Group name</label>
                                    <div v-show="nameCheck || nameError" class="validate"><i class="fa-solid fa-circle-exclamation"></i>
                                        <span v-if="nameCheck">This {{ nameType }} name is already in the system.</span>
                                        <span v-else>{{ typeof nameError === 'string' ? nameError : 'This field is required.' }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="form-group-modal">
                                    <div class="input-group" v-has-value>
                                        <input required v-model="description" type="text" name="descriptionModal"
                                            autocomplete="off" class="input" maxlength="50">
                                        <label class="title-label">Description</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
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

    <!-- Create Team  -->
    <div v-if="modelValue && mode === 'createTeam'" class="modal-backdrop" @click.self="close" id="createTeamModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="blue-icon" id="createTeamModalIcon">
                        <i class="fa-solid fa-people-group"></i>
                    </div>
                    <h3 class="modal-title ad" id="createTeamModalTitle">Create Team</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <div class="permissions-grid-2" id="groupGrid">
                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="input-group">
                                    <CustomSelect :class="['select-search', { 'select-toggle-error': selectedGroupError }]" v-model="selectedGroupId" :options="groupOptions" placeholder="Select Group" name="groupModal" />
                                    <div v-show="selectedGroupError" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof selectedGroupError === 'string' ? selectedGroupError : 'This field is required.' }}</div>
                                </div>
                            </div>
                        </div>

                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="form-group-modal">
                                    <div class="input-group" v-has-value>
                                        <input required v-model="name" type="text" name="teamNameModal" autocomplete="off" class="input" :class="{ 'form-input-modal': nameError || nameCheck }" maxlength="30">
                                        <label class="title-label">Team Name</label>
                                        <div v-show="nameCheck || nameError" class="validate"><i class="fa-solid fa-circle-exclamation"></i>
                                            <span v-if="nameCheck">This {{ nameType }} name is already in the system.</span>
                                            <span v-else>{{ typeof nameError === 'string' ? nameError : 'This field is required.' }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-12">
                        <div class="form-group-modal">
                            <div class="permissions-section-title"
                                style="display: flex; align-items: center; gap: 15px;margin-bottom: 5px;">
                                Database Server
                                <span class="d-none" style="color: red; font-size: 14px; font-weight: normal;"
                                    id="validateCreateDatabase"><i class="fa-solid fa-circle-exclamation"></i> This
                                    select is required</span>
                            </div>
                            <div class="permissions-grid-2" id="DatabseSeverGrid">
                                <div v-if="loadingDatabases" style="padding:8px;color:#64748b">Loading databases...</div>
                                <template v-else>
                                    <div style="margin-bottom:8px;">
                                        <label class="permission-item">
                                            <input type="checkbox" v-model="selectAll" />
                                            <span class="perm-checkbox" aria-hidden></span>
                                            <span style="font-weight:600">All databases</span>
                                        </label>
                                    </div>
                                    <div v-for="db in databases" :key="db.id" style="margin-bottom:8px;">
                                        <label class="permission-item">
                                            <input type="checkbox" :value="db.id" v-model="selectedDatabaseIds" />
                                            <span class="perm-checkbox" aria-hidden></span>
                                            <span>{{ db.database_name || db.name || db.display_name }}</span>
                                        </label>
                                    </div>
                                    <div v-if="databases.length === 0" class="empty-state" style="padding:8px;color:#64748b">No databases found.</div>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
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

    <!-- Edit team  -->
    <div v-if="modelValue && mode === 'editTeam'" class="modal-backdrop" @click.self="close" id="editTeamModal">
        <div class="modal-box">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="blue-icon" id="editTeamModalIcon">
                        <i class="fa-solid fa-people-group"></i>
                    </div>
                    <h3 class="modal-title ad" id="editTeamModalTitle">Edit Team</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div class="form-group-modal">
                    <div class="permissions-grid-2" id="groupGrid">
                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="input-group">
                                    <CustomSelect :class="['select-search','select-checkbox', { 'select-toggle-error': selectedGroupError }]" v-model="selectedGroupId"
                                        :options="groupOptions" placeholder="Select Group" name="groupModal" />
                                    <div v-show="selectedGroupError" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof selectedGroupError === 'string' ? selectedGroupError : 'This field is required.' }}</div>
                                </div>
                            </div>
                        </div>

                        <div class="col-lg-12">
                            <div class="form-group-modal">
                                <div class="form-group-modal">
                                    <div class="input-group" v-has-value>
                                        <input required v-model="name" type="text" name="teamNameModal"
                                            autocomplete="off" class="input" :class="{ 'form-input-modal': nameError || nameCheck }" maxlength="30">
                                        <label class="title-label">Team Name</label>
                                         <div v-show="nameCheck || nameError" class="validate"><i class="fa-solid fa-circle-exclamation"></i>
                                            <span v-if="nameCheck">This {{ nameType }} name is already in the system.</span>
                                            <span v-else>{{ typeof nameError === 'string' ? nameError : 'This field is required.' }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-12">
                        <div class="form-group-modal">
                            <div class="permissions-section-title"
                                style="display: flex; align-items: center; gap: 15px;margin-bottom: 5px;">
                                Database Server
                                <span class="d-none" style="color: red; font-size: 14px; font-weight: normal;"
                                    id="validateCreateDatabase"><i class="fa-solid fa-circle-exclamation"></i> This
                                    select is required</span>
                            </div>
                            <div class="permissions-grid-2" id="DatabseSeverGrid">
                                <div v-if="loadingDatabases" style="padding:8px;color:#64748b">Loading databases...</div>
                                <template v-else>
                                    <div style="margin-bottom:8px;">
                                        <label class="permission-item">
                                            <input type="checkbox" v-model="selectAll" />
                                            <span class="perm-checkbox" aria-hidden></span>
                                            <span style="font-weight:600">All databases</span>
                                        </label>
                                    </div>
                                    <div v-for="db in databases" :key="db.id" style="margin-bottom:8px;">
                                        <label class="permission-item">
                                            <input type="checkbox" :value="db.id" v-model="selectedDatabaseIds" />
                                            <span class="perm-checkbox" aria-hidden></span>
                                            <span>{{ db.database_name || db.name || db.display_name }}</span>
                                        </label>
                                    </div>
                                    <div v-if="databases.length === 0" class="empty-state" style="padding:8px;color:#64748b">No databases found.</div>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
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
import { API_GET_DATABASE, API_CHECK_GROUP_NAME, API_CHECK_TEAM_NAME, API_SAVE_GROUP, API_SAVE_TEAM } from '../api/paths'
import { getCookie, showToast } from '../assets/js/function-all'
import { ensureCsrf, getCsrfToken } from '../api/csrf'


import '../assets/css/components.css'

const props = defineProps({
    modelValue: { type: Boolean, default: false },
    mode: { type: String, default: '' },
    group: { type: Object, default: null },
    groups: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue', 'saved'])

const name = ref('')
const nameCheck = ref(false)
const nameError = ref(false)
let _nameTimer = null
const description = ref('')
const selectedGroupId = ref(null)
const selectedGroupError = ref(false)

const databases = ref([])
const selectedDatabaseIds = ref([])
const selectAll = ref(false)
const loadingDatabases = ref(false)

const fetchDatabases = async () => {
    loadingDatabases.value = true
    try {
        const res = await fetch(API_GET_DATABASE(), { credentials: 'include' })
        if (!res.ok) {
            console.error('Failed to fetch databases', res.status)
            databases.value = []
            return
        }
        const json = await res.json()
        // API may return a paginated object { results: [...] } or an array or { database: [...] }
        if (Array.isArray(json)) databases.value = json
        else if (Array.isArray(json.results)) databases.value = json.results
        else if (Array.isArray(json.database)) databases.value = json.database
        else databases.value = []
        // if editing a team, preload selectedDatabaseIds from props.group.maindatabase (if present)
        if (props.mode === 'editTeam' && props.group && Array.isArray(databases.value)) {
            try {
                const parsed = typeof props.group.maindatabase === 'string' ? JSON.parse(props.group.maindatabase) : props.group.maindatabase
                if (Array.isArray(parsed)) {
                    const nums = parsed.map(x => Number(x))
                    selectedDatabaseIds.value = databases.value.filter(d => nums.includes(Number(d.id))).map(d => d.id)
                    selectAll.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
                }
            } catch (e) {
                // ignore parse errors
            }
        }
    } catch (err) {
        console.error('Error fetching databases', err)
        databases.value = []
    } finally {
        loadingDatabases.value = false
    }
}

// toggle selectAll
watch(selectAll, (val) => {
    if (val) selectedDatabaseIds.value = databases.value.map(d => d.id)
    else selectedDatabaseIds.value = []
})

// when modal opens for team create/edit, fetch databases
watch(() => props.modelValue, (val) => {
    if (val && (props.mode === 'createTeam' || props.mode === 'editTeam')) {
        fetchDatabases()
    }
})

// watch name and debounce-check against backend for duplicate group/team name
watch(() => name.value, (val) => {
    nameCheck.value = false
    nameError.value = false
    if (_nameTimer) clearTimeout(_nameTimer)
            _nameTimer = setTimeout(async () => {
        try {
            if (!val || String(val).trim() === '') { nameCheck.value = false; return }
            const trimmed = String(val).trim()
            let url = ''
            if (props.mode === 'createGroup' || props.mode === 'editGroup') {
                url = API_CHECK_GROUP_NAME() + `?group_name=${encodeURIComponent(trimmed)}` + (props.mode === 'editGroup' && props.group && props.group.id ? `&group_id=${encodeURIComponent(String(props.group.id))}` : '')
            } else if (props.mode === 'createTeam' || props.mode === 'editTeam') {
                // for team check, include group_id (selected) and team_id when editing
                url = API_CHECK_TEAM_NAME() + `?team_name=${encodeURIComponent(trimmed)}`
                if (selectedGroupId.value) url += `&group_id=${encodeURIComponent(String(selectedGroupId.value))}`
                if (props.mode === 'editTeam' && props.group && props.group.id) url += `&team_id=${encodeURIComponent(String(props.group.id))}`
            } else {
                return
            }
            const res = await fetch(url, { method: 'GET', credentials: 'include' })
            if (!res.ok) { nameCheck.value = false; return }
            const j = await res.json()
            nameCheck.value = !!(j && (j.is_taken === true || j.exists === true || j.is_taken))
        } catch (e) {
            console.error('name check error', e)
            nameCheck.value = false
        }
    }, 400)
})

watch(() => props.modelValue, (val) => {
    if (val) {
        // clear previous validation when modal opens
        nameError.value = false
        nameCheck.value = false
        selectedGroupError.value = false
    }
    if (val && props.mode === 'editGroup' && props.group) {
        name.value = props.group.group_name || ''
        description.value = props.group.description || ''
    }
    if (val && props.mode === 'createGroup') {
        name.value = ''
        description.value = ''
    }
    if (val && props.mode === 'createTeam') {
        // reset team form, but if a group prop is provided, preselect it
        name.value = ''
        description.value = ''
        if (props.group && (props.group.id || props.group.user_group_id || props.group.user_group)) {
            selectedGroupId.value = props.group.id || props.group.user_group_id || props.group.user_group
        } else {
            selectedGroupId.value = null
        }
        selectedDatabaseIds.value = []
        selectAll.value = false
    }
})

// clear selectedGroupError when user picks a group
watch(() => selectedGroupId.value, (val) => {
    if (val) selectedGroupError.value = false
})

watch(() => props.group, (g) => {
    if (props.modelValue && props.mode === 'editGroup' && g) {
        name.value = g.group_name || ''
        description.value = g.description || ''
    }
    if (props.modelValue && (props.mode === 'editTeam') && g) {
        name.value = g.name || ''
        description.value = g.maindatabase || ''
        selectedGroupId.value = g.user_group_id || g.user_group || null
        // preload selectedDatabaseIds if databases already loaded
        try {
            const parsed = typeof g.maindatabase === 'string' ? JSON.parse(g.maindatabase) : g.maindatabase
            if (Array.isArray(parsed) && databases.value.length) {
                const nums = parsed.map(x => Number(x))
                selectedDatabaseIds.value = databases.value.filter(d => nums.includes(Number(d.id))).map(d => d.id)
                selectAll.value = databases.value.length > 0 && selectedDatabaseIds.value.length === databases.value.length
            }
        } catch (e) {
            // ignore parse errors
        }
    }
    // if modal is open for createTeam and group prop changes, preselect it
    if (props.modelValue && props.mode === 'createTeam' && g) {
        selectedGroupId.value = g.id || g.user_group_id || g.user_group || null
    }
})

const groupOptions = computed(() => {
    return Array.isArray(props.groups) ? props.groups.map(g => ({ label: g.group_name, value: g.id })) : []
})

const nameType = computed(() => {
    if (String(props.mode || '').toLowerCase().includes('group')) return 'group'
    if (String(props.mode || '').toLowerCase().includes('team')) return 'team'
    return 'item'
})

function close() {
    emit('update:modelValue', false)
}

async function onSave() {
    // ฟังก์ชันหลักสำหรับบันทึกข้อมูล (Create หรือ Update)
    // ทำหน้าที่ตรวจสอบความถูกต้องของข้อมูล (Validation) และส่ง Request ไปยัง API

    // ล้างข้อความ error ก่อนหน้า
    nameError.value = false

    // ตรวจสอบฟิลด์ที่จำเป็นทันที (ทำก่อนเพื่อให้แสดง error ทันทีเมื่อกด Save)
    const trimmed = String(name.value || '').trim()
    let hasError = false

    // ตรวจสอบการเลือก Group สำหรับการจัดการ Team
    if ((props.mode === 'createTeam' || props.mode === 'editTeam') && !selectedGroupId.value) {
        selectedGroupError.value = 'This field is required.'
        hasError = true
    }

    // ตรวจสอบว่ากรอกชื่อหรือไม่
    if (!trimmed) {
        nameError.value = 'This field is required.'
        hasError = true
    }

    if (hasError) {
        // โฟกัสไปที่ฟิลด์ที่ไม่ถูกต้องฟิลด์แรก: เริ่มจาก group select แล้วค่อยไปที่ name
        try {
            if ((props.mode === 'createTeam' || props.mode === 'editTeam') && !selectedGroupId.value) {
                const el = document.querySelector('[name="groupModal"]')
                if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ behavior: 'smooth', block: 'center' })
                if (el && typeof el.focus === 'function') el.focus()
            } else {
                const selName = props.mode && props.mode.toLowerCase().includes('team') ? 'teamNameModal' : 'groupNameModal'
                const el = document.querySelector(`[name="${selName}"]`)
                if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ behavior: 'smooth', block: 'center' })
                if (el && typeof el.focus === 'function') el.focus()
            }
        } catch (e) { console.warn('focus failed', e) }
        return
    }

    // หลังจากตรวจสอบฟิลด์จำเป็นแล้ว ถ้ามี flag ชื่อซ้ำให้บล็อกการ submit
    if (nameCheck.value) {
        nameError.value = 'This name is already in the system.'
        return
    }

    try {
        // CSRF token is fetched at login/startup and cached; use cached token
        const csrfToken = getCsrfToken()
        let url = ''
        let body = {}
        if (props.mode === 'createGroup' || props.mode === 'editGroup') {
            url = API_SAVE_GROUP()
            body = { action: props.mode === 'createGroup' ? 'create' : 'update', group_name: name.value, description: description.value }
            if (props.mode === 'editGroup' && props.group && props.group.id) body.group_id = props.group.id
        } else if (props.mode === 'createTeam' || props.mode === 'editTeam') {
            url = API_SAVE_TEAM()
            const maindb = Array.isArray(selectedDatabaseIds.value) ? selectedDatabaseIds.value.map(String) : []
            body = { action: props.mode === 'createTeam' ? 'create' : 'update', name: name.value, maindatabase: JSON.stringify(maindb), user_group_id: selectedGroupId.value }
            if (props.mode === 'editTeam' && props.group && props.group.id) body.team_id = props.group.id
        } else {
            // กรณีไม่รู้จัก mode ให้ emit กลับไปเลย
            emit('saved', { mode: props.mode, data: {}})
            emit('update:modelValue', false)
            return
        }

        const res = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            body: JSON.stringify(body)
        })

        const j = res.ok ? await res.json() : null
        if (res.ok && j && (j.status === 'success' || j.status === 'ok')) {
            // หาชื่อ item จาก response หรือ payload เพื่อนำมาแสดงใน Toast
            let returned = j.data || j.group || j.team || j.result || body
            
            // ตรวจสอบให้แน่ใจว่ามี user_group_id สำหรับอัปเดตหน้าจอ (รวมจาก body ถ้าไม่มีใน response)
            if ((props.mode === 'createTeam' || props.mode === 'editTeam') && body.user_group_id) {
                returned = { ...returned, user_group_id: body.user_group_id, maindatabase: body.maindatabase }
            }

            const itemName = (returned && (returned.group_name || returned.name || returned.team_name || returned.group_name || returned.label)) || name.value || ''
            if (props.mode === 'createGroup' || props.mode === 'createTeam') {
                showToast(`Create ${itemName} successfully`, 'success')
            } else if (props.mode === 'editGroup' || props.mode === 'editTeam') {
                showToast(`Edit ${itemName} successfully`, 'success')
            } else {
                showToast(j.message || 'Saved successfully', 'success')
            }
            emit('saved', { mode: props.mode, data: returned })
            emit('update:modelValue', false)
            return
        } else {
            const msg = (j && (j.message || j.error)) || 'Save failed'
            showToast(msg, 'error')
            // ตั้งค่า error ที่ฟิลด์ (ถ้ามี)
            nameError.value = msg
            return
        }
    } catch (e) {
        console.error('onSave error', e)
        showToast('An error occurred while saving', 'error')
        nameError.value = 'An error occurred'
    }
}
</script>

<style scoped>
.modal-body {
    min-height: 350px;
    overflow: auto
}
.form-input-modal {
    border-radius: 25px;
    border: 1px solid rgb(245, 163, 163) !important;
    box-shadow: rgba(220, 53, 69, 0.25) 0px 0px 0px 0.2rem !important;
}
</style>