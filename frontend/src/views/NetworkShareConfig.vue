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
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="search-group" style="width:220px; position:relative;">
                                        <li class="option option-search">
                                            <div class="search-input-wrap">
                                                <i class="fa-solid fa-magnifying-glass search-icon"></i>
                                                <input v-model="searchQuery" type="text"
                                                       class="form-control form-control-sm search-input"
                                                       placeholder="Search..." />
                                                <i v-if="searchQuery" class="fa-solid fa-xmark fa-times clear-icon" aria-hidden="true" @click.stop="searchQuery = ''"></i>
                                            </div>
                                        </li>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Card List of Databases -->
                            <div class="custom-roles-list" style="max-height: calc(100vh - 260px); overflow-y: auto;">
                                <template v-if="loading">
                                    <div class="table-overlay" style="height: 300px; display: flex; align-items: center; justify-content: center;">
                                        <div class="overlay-box">Loading databases...</div>
                                    </div>
                                </template>
                                <template v-else>
                                    <div v-if="filteredDatabases.length" class="group-list">
                                        <div v-for="db in filteredDatabases" :key="db.database_id" 
                                             :class="['group-card-item', { active: selectedDbId === db.database_id }]"
                                             @click.stop="selectDatabase(db)">
                                            <div class="group-card-main">
                                                <div class="group-card-header">
                                                    <span class="group-card-title">{{ db.database_name }}</span>
                                                    <span :class="['role-badge', db.hasConfig ? 'auditor' : 'administrator']">
                                                        {{ db.hasConfig ? 'Configured' : 'Not Configured' }}
                                                    </span>
                                                </div>
                                                <div class="group-card-desc">
                                                    {{ db.networkPath || db.description || 'No description or network path provided.' }}
                                                </div>
                                            </div>
                                            <div class="group-card-actions">
                                                <button class="group-edit-btn">
                                                    Configure
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-else class="empty-state">
                                        <i class="fa-solid fa-dove"></i>
                                        <p>No databases found.</p>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right: Config Form -->
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-4">
                                <div class="d-flex align-items-center justify-content-center me-1"
                                     style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                                    <i class="fas fa-network-wired" style="color: #2b6cb0; font-size: 18px"></i>
                                </div>
                                <h5 class="card-title mb-2 mt-1">Network Share Settings</h5>
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
                                                        <span class="group-card-title">{{ share.networkPath }}</span>
                                                        <div style="display: inline-flex; align-items: center; gap: 8px;">
                                                            <span class="group-card-group-badge" style="margin-left: 8px; background: #eff6ff; color: #3b82f6; border: 1px solid #dbeafe; font-size: 9px; font-weight: 600; padding: 2px 8px; border-radius: 12px; white-space: nowrap;">
                                                                Database: {{ share.mainDbName }}
                                                            </span>
                                                            <span v-if="share.isActive" class="group-card-group-badge" style="margin-left: 8px; background: #ecfdf5; color: #10b981; border: 1px solid #a7f3d0; font-size: 9px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">
                                                                Active
                                                            </span>
                                                            <span v-else class="group-card-group-badge" style="margin-left: 8px; background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; font-size: 9px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">
                                                                Inactive
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <div class="group-card-desc" style="margin-top: 4px; display: flex; align-items: center; gap: 15px; font-size: 10px; color: #64748b;">
                                                        <span><i class="fas fa-database" style="margin-right: 4px; font-size: 10px; color: #94a3b8;"></i> Main DB ID: {{ share.mainDbId || '-' }}</span>
                                                        <span><i class="fas fa-user" style="margin-right: 4px; font-size: 10px; color: #94a3b8;"></i> Username: {{ share.username || '-' }}</span>
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
                                    <input required v-model="form.password" type="password" autocomplete="off" class="input" :class="{ 'form-input-modal': errors.password }">
                                    <label class="title-label">Password</label>
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
            showToast('Failed to load databases', 'error')
        }
    } catch (err) {
        console.error('Error loading Network Share settings:', err)
        showToast('Error loading databases', 'error')
    } finally {
        loading.value = false
    }
}

const databaseOptions = computed(() => {
    return Array.isArray(databases.value) 
        ? databases.value.map(db => ({ label: db.database_name, value: db.id })) 
        : []
})

const openCreateModal = () => {
    isEdit.value = false
    editId.value = null
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
}

const saveChanges = async () => {
    errors.value.networkPath = ''
    errors.value.username = ''
    errors.value.password = ''
    
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
</style>

<style scoped src="../assets/css/group-and-team.css"></style>
