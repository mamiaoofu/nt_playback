<template>
    <MainLayout>
        <div class="main-wrapper container-fluid-home py-3" style="display:flex; flex-direction:column; height:100%;">
            <div class="row row-container">
                <!-- Left: Database List -->
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
                                <div class="d-flex align-items-center">
                                    <div class="d-flex align-items-center justify-content-center me-1"
                                         style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                                        <i class="fas fa-database" style="color: #2b6cb0; font-size: 18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Database List</h5>
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

                            <div v-if="!selectedDbId" class="empty-state" style="height: 300px; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                                <i class="fas fa-network-wired" style="font-size: 48px; opacity: 0.3; margin-bottom: 12px;"></i>
                                <p>Select a database from the list to view or edit its Network Share configuration.</p>
                            </div>

                            <template v-else>
                                <div class="permissions-grid-2">
                                    <div class="input-group" v-has-value style="grid-column: span 2;">
                                        <input v-model="form.networkPath" required type="text" name="networkPath" autocomplete="off" class="input">
                                        <label class="title-label">Network Path</label>
                                    </div>
                                    <div class="input-group" v-has-value>
                                        <input v-model="form.username" required type="text" name="username" autocomplete="off" class="input">
                                        <label class="title-label">Username</label>
                                    </div>
                                    <div class="input-group" v-has-value>
                                        <input v-model="form.password" required type="password" name="password" autocomplete="off" class="input">
                                        <label class="title-label">Password</label>
                                    </div>
                                    <!-- Active Toggle -->
                                    <div class="form-check form-switch mt-3 ms-2" style="grid-column: span 2; display: flex; align-items: center; gap: 8px;">
                                        <input class="form-check-input" type="checkbox" id="isActiveSwitch" v-model="form.isActive">
                                        <label class="form-check-label mb-0" for="isActiveSwitch" style="font-weight: 500; font-size: 14px; color: #1e293b;">
                                            Active Storage Config
                                        </label>
                                    </div>
                                </div>

                                <div class="button-group mt-4 d-flex gap-2">
                                    <button class="btn btn-primary btn-role btn-sm" type="button" @click="saveChanges" :disabled="saving">
                                        <i class="fas fa-save"></i> {{ saving ? 'Saving...' : 'Save Changes' }}
                                    </button>
                                    <button v-if="form.hasConfig" class="btn btn-secondary btn-role btn-sm" type="button" @click="deleteConfig" :disabled="deleting" style="color: #ef4444; border-color: #fee2e2;">
                                        <i class="fas fa-trash"></i> {{ deleting ? 'Deleting...' : 'Delete Config' }}
                                    </button>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MainLayout from '../layouts/MainLayout.vue'
import { API_NETWORK_SHARE_CONFIG } from '../api/paths'
import { showToast } from '../assets/js/function-all'
import { getCsrfToken } from '../api/csrf'

const databases = ref([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const searchQuery = ref('')
const selectedDbId = ref(null)

const form = ref({
    database_id: null,
    networkPath: '',
    username: '',
    password: '',
    isActive: true,
    hasConfig: false
})

const filteredDatabases = computed(() => {
    if (!searchQuery.value.trim()) return databases.value
    const q = searchQuery.value.toLowerCase()
    return databases.value.filter(db => 
        db.database_name.toLowerCase().includes(q) || 
        (db.description && db.description.toLowerCase().includes(q)) ||
        (db.networkPath && db.networkPath.toLowerCase().includes(q))
    )
})

const loadSettings = async () => {
    loading.value = true
    try {
        const res = await fetch(API_NETWORK_SHARE_CONFIG(), { credentials: 'include' })
        if (res.ok) {
            const json = await res.json()
            if (json.status === 'success') {
                databases.value = json.data
                
                // Keep selection if possible
                if (selectedDbId.value) {
                    const selected = databases.value.find(db => db.database_id === selectedDbId.value)
                    if (selected) selectDatabase(selected)
                }
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

const selectDatabase = (db) => {
    selectedDbId.value = db.database_id
    form.value = {
        database_id: db.database_id,
        networkPath: db.networkPath || '',
        username: db.username || '',
        password: db.password || '',
        isActive: db.isActive === 1,
        hasConfig: db.hasConfig
    }
}

const saveChanges = async () => {
    saving.value = true
    try {
        const csrfToken = getCsrfToken()
        const payload = {
            database_id: form.value.database_id,
            networkPath: form.value.networkPath,
            username: form.value.username,
            password: form.value.password,
            isActive: form.value.isActive ? 1 : 0
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
            await loadSettings()
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

const deleteConfig = async () => {
    if (!confirm('Are you sure you want to delete the configuration for this database?')) return
    deleting.value = true
    try {
        const csrfToken = getCsrfToken()
        const res = await fetch(API_NETWORK_SHARE_CONFIG(), {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            body: JSON.stringify({ database_id: selectedDbId.value }),
            credentials: 'include'
        })
        const json = await res.json()
        if (json.status === 'success') {
            showToast(json.message || 'Settings deleted successfully', 'success')
            selectedDbId.value = null
            form.value = {
                database_id: null,
                networkPath: '',
                username: '',
                password: '',
                isActive: true,
                hasConfig: false
            }
            await loadSettings()
        } else {
            showToast(json.message || 'Failed to delete settings', 'error')
        }
    } catch (err) {
        console.error('Error deleting Network Share settings:', err)
        showToast('Error deleting settings', 'error')
    } finally {
        deleting.value = false
    }
}

onMounted(() => {
    loadSettings()
})
</script>

<style scoped>
@import "../assets/css/group-and-team.css";
@import "../assets/css/user-form.css";

.option.option-search::marker {
    display: none;
}

li.option.option-search {
    list-style: none;
}
</style>
