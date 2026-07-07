<template>
    <MainLayout>
        <div class="main-wrapper container-fluid-home py-3" style="display:flex; flex-direction:column; height:100%;">
            <div class="row row-container">
                <div class="col-lg-12">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
                                <div class="d-flex align-items-center">
                                    <div class="d-flex align-items-center justify-content-center me-1"
                                         style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                                        <i class="fas fa-network-wired" style="color: #2b6cb0; font-size: 18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Network Share</h5>
                                </div>

                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="search-group" style="width:260px; position:relative;">
                                        <li class="option option-search">
                                            <div class="search-input-wrap">
                                                <i class="fa-solid fa-magnifying-glass search-icon"></i>
                                                <input v-model="searchQuery" type="text"
                                                       class="form-control form-control-sm search-input"
                                                       placeholder="Search..." @input="onTyping" @keyup.enter="loadSettings" />
                                                <i v-if="searchQuery" class="fa-solid fa-xmark fa-times clear-icon" aria-hidden="true" @click.stop="clearSearch"></i>
                                            </div>
                                        </li>
                                    </div>
                                    <button class="btn-role btn-primary btn-sm" id="addNetworkShareBtn" @click.stop="openCreateModal">
                                        <i class="fas fa-plus"></i>
                                        Add Network Share
                                    </button>
                                </div>
                            </div>

                            <div class="custom-roles-list" style="margin-top: 15px;">
                                <template v-if="loading">
                                    <div class="table-overlay" style="height: 400px;">
                                        <div class="overlay-box">Loading...</div>
                                    </div>
                                </template>
                                <template v-else>
                                    <div v-if="shares.length">
                                        <div class="group-list">
                                            <div v-for="share in shares" :key="share.id" class="group-card-item">
                                                <div class="group-card-main">
                                                    <div class="group-card-header">
                                                        <span class="group-card-title" style="font-size: 14px; font-weight: 800; color: #1e293b;">
                                                            <i class="fas fa-database" style="margin-right: 6px; color: #416fd6;"></i>
                                                            {{ share.mainDbName }}
                                                        </span>
                                                    </div>
                                                    <div class="group-card-desc" style="margin-top: 6px; display: flex; align-items: center; gap: 15px; font-size: 10px; color: #64748b;">
                                                        <span><i class="fas fa-hashtag" style="margin-right: 4px; font-size: 10px; color: #94a3b8;"></i> Main DB ID: {{ share.mainDbId || '-' }}</span>
                                                        <span><i class="fas fa-user" style="margin-right: 4px; font-size: 10px; color: #94a3b8;"></i> Username: {{ share.username || '-' }}</span>
                                                        <span><i class="fas fa-network-wired" style="margin-right: 4px; font-size: 10px; color: #94a3b8;"></i> Network Path: {{ share.networkPath || '-' }}</span>
                                                    </div>
                                                </div>

                                                <div class="group-card-actions" style="display: flex; align-items: center; gap: 8px;">
                                                    <label class="switch_status" @click.stop>
                                                        <input type="checkbox" :checked="share.isActive"
                                                            @change="() => toggleActive(share.id)" />
                                                        <span class="slider_status round"></span>
                                                    </label>
                                                    <button class="group-edit-btn" @click.stop="openEditModal(share)">
                                                        Click to edit
                                                    </button>
                                                    <button type="button" class="group-delete-btn" @click.stop="deleteShare(share.id)">
                                                        <i class="fas fa-trash" style="font-size: 12px;"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div v-else class="empty-state" style="text-align: center; padding: 40px 0; color: #64748b;">
                                        <i class="fas fa-network-wired" style="font-size: 48px; margin-bottom: 15px; color: #cbd5e1;"></i>
                                        <p>No network shares found. Click "Add Network Share" to create one.</p>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Add/Edit Modal -->
        <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
            <div class="modal-box">
                <div class="modal-header">
                    <div style="display: flex; align-items: center; gap: 4px">
                        <div class="blue-icon">
                            <i class="fas fa-network-wired"></i>
                        </div>
                        <h3 class="modal-title ad">{{ isEdit ? 'Edit Network Share' : 'Add Network Share' }}</h3>
                    </div>
                    <button type="button" class="btn-close" @click="closeModal"></button>
                </div>
                <div class="modal-body">
                    <div class="form-group-modal">
                        <div class="permissions-grid-2">
                            <!-- Database selection -->
                            <div class="col-lg-12 mb-3">
                                <div class="form-group-modal">
                                    <CustomSelect v-model="form.mainDbId" :options="databaseOptions" placeholder="Database Server*" />
                                </div>
                            </div>

                            <!-- Network Path -->
                            <div class="col-lg-12 mb-3">
                                <div class="input-group" v-has-value>
                                    <input required v-model="form.networkPath" type="text" autocomplete="off" class="input" :class="{ 'form-input-modal': errors.networkPath }">
                                    <label class="title-label">Network Path*</label>
                                    <div v-show="errors.networkPath" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ errors.networkPath }}</div>
                                </div>
                            </div>

                            <!-- Username -->
                            <div class="col-lg-12 mb-3">
                                <div class="input-group" v-has-value>
                                    <input required v-model="form.username" type="text" autocomplete="off" class="input" :class="{ 'form-input-modal': errors.username }">
                                    <label class="title-label">Username</label>
                                    <div v-show="errors.username" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ errors.username }}</div>
                                </div>
                            </div>

                            <!-- Password -->
                            <div class="col-lg-12 mb-3">
                                <div class="input-group" v-has-value>
                                    <input required v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="off" class="input" :class="{ 'form-input-modal': errors.password, 'padding-toggle': !isEdit || isChangingPassword, 'padding-change-btn': isEdit && !isChangingPassword, 'padding-cancel-btn': isEdit && isChangingPassword }" :readonly="isEdit && !isChangingPassword">
                                    <label class="title-label">Password</label>
                                    
                                    <!-- Eye toggle: shown in Add mode, or Edit mode when changing password -->
                                    <span v-if="!isEdit || isChangingPassword" class="password-toggle-icon" @click="showPassword = !showPassword" title="Show/Hide Password">
                                        <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                                    </span>
                                    
                                    <!-- "กรอกค่าใหม่" (Change Password) button: shown in Edit mode when NOT changing password -->
                                    <span v-if="isEdit && !isChangingPassword" class="password-change-btn" @click="startChangePassword">
                                        กรอกค่าใหม่
                                    </span>
                                    
                                    <!-- Cancel changing password: shown in Edit mode when changing password -->
                                    <span v-if="isEdit && isChangingPassword" class="password-change-cancel-btn" @click="cancelChangePassword" title="Cancel editing password">
                                        <i class="fas fa-undo" style="margin-right: 4px;"></i>ยกเลิก
                                    </span>

                                    <div v-show="errors.password" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ errors.password }}</div>
                                </div>
                            </div>

                            <!-- Is Active -->
                            <div class="col-lg-12 mb-2" style="text-align: left;">
                                <label class="permission-item d-inline-flex align-items-center" style="cursor: pointer;">
                                    <input type="checkbox" v-model="form.isActive" />
                                    <span class="perm-checkbox" aria-hidden></span>
                                    <span style="font-weight: 600; margin-left: 5px;">Active Status</span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-role btn-secondary" @click="closeModal" :disabled="saving">
                        <i class="fas fa-times"></i>
                        Cancel
                    </button>
                    <button class="btn-role btn-primary" @click="saveChanges" :disabled="saving">
                        <i class="fas fa-save"></i>
                        {{ saving ? 'Saving...' : 'Save Changes' }}
                    </button>
                </div>
            </div>
        </div>
    </MainLayout>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import MainLayout from '../layouts/MainLayout.vue'
import CustomSelect from '../components/CustomSelect.vue'
import { API_NETWORK_SHARE_CONFIG } from '../api/paths'
import { showToast } from '../assets/js/function-all'
import { getCsrfToken } from '../api/csrf'
import '../assets/css/components.css'

const shares = ref([])
const databases = ref([])
const searchQuery = ref('')
const loading = ref(false)
const saving = ref(false)

const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const showPassword = ref(false)
const isChangingPassword = ref(false)

const startChangePassword = () => {
    isChangingPassword.value = true
    form.value.password = ''
}

const cancelChangePassword = () => {
    isChangingPassword.value = false
    form.value.password = '******'
}

const form = ref({
    networkPath: '',
    username: '',
    password: '',
    mainDbId: null,
    isActive: true
})

const errors = ref({
    networkPath: '',
    username: '',
    password: ''
})

let typingTimer = null

const onTyping = () => {
    if (typingTimer) clearTimeout(typingTimer)
    typingTimer = setTimeout(() => {
        loadSettings()
    }, 400)
}

const clearSearch = () => {
    searchQuery.value = ''
    loadSettings()
}

const loadSettings = async () => {
    loading.value = true
    try {
        const url = `${API_NETWORK_SHARE_CONFIG()}?search=${encodeURIComponent(searchQuery.value)}`
        const res = await fetch(url, { credentials: 'include' })
        if (res.ok) {
            const json = await res.json()
            if (json.status === 'success') {
                shares.value = json.data
                databases.value = json.databases
            }
        } else {
            showToast('Failed to load settings', 'error')
        }
    } catch (err) {
        console.error('Error loading Network Share settings:', err)
        showToast('Error loading settings', 'error')
    } finally {
        loading.value = false
    }
}

const databaseOptions = computed(() => {
    if (!Array.isArray(databases.value)) return []
    return databases.value
        .filter(db => {
            if (!isEdit.value) {
                // For creation, exclude already assigned databases
                return !db.is_assigned
            } else {
                // For update, exclude already assigned databases EXCEPT the one currently assigned to this share
                return !db.is_assigned || db.id === form.value.mainDbId
            }
        })
        .map(db => ({ label: db.database_name, value: db.id }))
})

const openCreateModal = () => {
    isEdit.value = false
    editId.value = null
    showPassword.value = false
    isChangingPassword.value = false
    form.value = {
        networkPath: '',
        username: '',
        password: '',
        mainDbId: null,
        isActive: true
    }
    errors.value.networkPath = ''
    errors.value.username = ''
    errors.value.password = ''
    showModal.value = true
}

const openEditModal = (share) => {
    isEdit.value = true
    editId.value = share.id
    showPassword.value = false
    isChangingPassword.value = false
    form.value = {
        networkPath: share.networkPath,
        username: share.username,
        password: share.password,
        mainDbId: share.mainDbId,
        isActive: share.isActive
    }
    errors.value.networkPath = ''
    errors.value.username = ''
    errors.value.password = ''
    showModal.value = true
}

const closeModal = () => {
    showModal.value = false
    showPassword.value = false
    isChangingPassword.value = false
}

const saveChanges = async () => {
    errors.value.networkPath = ''
    errors.value.username = ''
    errors.value.password = ''
    
    if (!form.value.mainDbId) {
        showToast('Database Server is required.', 'error')
        return
    }
    
    if (!form.value.networkPath.trim()) {
        errors.value.networkPath = 'Network Path is required.'
        return
    }
    
    if (!form.value.username.trim()) {
        errors.value.username = 'Username is required.'
        return
    }
    
    if (!form.value.password.trim()) {
        errors.value.password = 'Password is required.'
        return
    }

    saving.value = true
    try {
        const csrfToken = getCsrfToken()
        const payload = {
            action: isEdit.value ? 'update' : 'create',
            id: editId.value,
            networkPath: form.value.networkPath,
            username: form.value.username,
            password: form.value.password,
            mainDbId: form.value.mainDbId,
            isActive: form.value.isActive
        }

        const res = await fetch(API_NETWORK_SHARE_CONFIG(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            body: JSON.stringify(payload),
            credentials: 'include'
        })
        const json = await res.json()
        if (json.status === 'success') {
            showToast(json.message || 'Settings saved successfully', 'success')
            closeModal()
            loadSettings()
        } else {
            showToast(json.message || 'Failed to save settings', 'error')
        }
    } catch (err) {
        console.error('Error saving Network Share settings:', err)
        showToast('Error saving settings', 'error')
    } finally {
        saving.value = false
    }
}

const toggleActive = async (id) => {
    try {
        const csrfToken = getCsrfToken()
        const res = await fetch(API_NETWORK_SHARE_CONFIG(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            body: JSON.stringify({ action: 'toggle_active', id }),
            credentials: 'include'
        })
        const json = await res.json()
        if (json.status === 'success') {
            showToast(json.message || 'Status toggled successfully', 'success')
            loadSettings()
        } else {
            showToast(json.message || 'Failed to toggle status', 'error')
        }
    } catch (err) {
        console.error('Error toggling Network Share status:', err)
        showToast('Error updating status', 'error')
    }
}

const deleteShare = async (id) => {
    if (!confirm('Are you sure you want to delete this network share configuration?')) {
        return
    }
    try {
        const csrfToken = getCsrfToken()
        const res = await fetch(API_NETWORK_SHARE_CONFIG(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            body: JSON.stringify({ action: 'delete', id }),
            credentials: 'include'
        })
        const json = await res.json()
        if (json.status === 'success') {
            showToast(json.message || 'Deleted successfully', 'success')
            loadSettings()
        } else {
            showToast(json.message || 'Failed to delete configuration', 'error')
        }
    } catch (err) {
        console.error('Error deleting Network Share config:', err)
        showToast('Error deleting configuration', 'error')
    }
}

onMounted(() => {
    loadSettings()
})
</script>

<style scoped>
.option.option-search::marker {
    display: none;
}

li.option.option-search {
    list-style: none;
}

.form-input-modal {
    border-radius: 25px;
    border: 1px solid rgb(245, 163, 163) !important;
    box-shadow: rgba(220, 53, 69, 0.25) 0px 0px 0px 0.2rem !important;
}

.modal-body {
    min-height: 280px;
    overflow: visible;
}

/* switch_status CSS */
.switch_status {
    position: relative;
    display: inline-block;
    width: 80px;
    height: 23px
}

.switch_status input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider_status {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #e6f4eeff;
    transition: 0.4s;
    border-radius: 34px;
}

.slider_status:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 2px;
    bottom: 3.5px;
    background-color: white;
    transition: 0.4s;
    border-radius: 50%;
    z-index: 2;
}

.slider_status:after {
    content: "Inactive";
    color: #64748b;
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    font-weight: 600;
    font-family: sans-serif;
}

input:checked+.slider_status {
    background-color: #2ecc71;
}

input:checked+.slider_status:before {
    transform: translateX(60px);
}

input:checked+.slider_status:after {
    content: "Active";
    left: 12px;
    right: auto;
    color: white;
}

.group-card-header:deep {
    gap: 0px;
}

.password-toggle-icon {
    position: absolute;
    right: 12px;
    top: 16.5px;
    transform: translateY(-50%);
    color: #64748b;
    cursor: pointer;
    font-size: 13px;
    z-index: 10;
}

.password-toggle-icon:hover {
    color: #416fd6;
}

.password-change-btn {
    position: absolute;
    right: 12px;
    top: 16.5px;
    transform: translateY(-50%);
    background-color: #eff6ff;
    color: #3b82f6;
    border: 1px solid #dbeafe;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    z-index: 10;
    white-space: nowrap;
    transition: all 0.2s;
}

.password-change-btn:hover {
    background-color: #3b82f6;
    color: #ffffff;
    border-color: #3b82f6;
}

.password-change-cancel-btn {
    position: absolute;
    right: 12px;
    top: 16.5px;
    transform: translateY(-50%);
    background-color: #fef2f2;
    color: #ef4444;
    border: 1px solid #fee2e2;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    z-index: 10;
    white-space: nowrap;
    transition: all 0.2s;
}

.password-change-cancel-btn:hover {
    background-color: #ef4444;
    color: #ffffff;
    border-color: #ef4444;
}

.padding-toggle {
    padding-right: 35px !important;
}

.padding-change-btn {
    padding-right: 85px !important;
}

.padding-cancel-btn {
    padding-right: 75px !important;
}
</style>

<style scoped src="../assets/css/group-and-team.css"></style>
