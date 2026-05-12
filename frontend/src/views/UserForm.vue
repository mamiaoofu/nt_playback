<template>
    <MainLayout>
        <div class="main-wrapper container-fluid-home py-3">
            <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: 'User Management', to: '/user-management' }, { text: mode === 'edit' ? 'Save User' : 'Add User' }]" />

            <div class="row col-lg-12">
                <div class="col-lg-6" style="margin-bottom: 14px;">
                    <div class="card card-left">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-start justify-content-between"
                                    style="margin-bottom: 18px;">
                                    <div class="d-flex align-items-center">
                                        <div class="d-flex align-items-center justify-content-center me-1"
                                            style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                            <i class="fas fa-user-plus" style="color:#2b6cb0;font-size:18px"></i>
                                        </div>
                                        <h5 class="card-title mb-2 mt-1">User Information</h5>
                                    </div>
                                    <div class="d-flex align-items-center">
                                        <div style="display: flex; gap: 8px;">
                                            <button v-if="showDomainAccountBtn" class="customize-btn" type="button" @click="toggleDomainAccountMode" style="position:relative; height: 38px;">
                                                <i class="fas fa-network-wired" style="margin-right: 6px;"></i> Domain account
                                            </button>
                                            <button class="customize-btn" type="button" id="clearUserInfoBtn"
                                                @click="clearUserInfo" style="position:relative; height: 38px;">
                                                <i class="fas fa-eraser" style="margin-right: 6px;"></i> Clear
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div class="permissions-grid-1">
                                    <div class="input-group" style="margin-bottom: 12.2px;" :class="{'has-value': isDomainAccountMode || form.username}">
                                        <input v-if="!isDomainAccountMode" v-model="form.username" required type="text" name="username" autocomplete="off" :class="['input', { 'form-input-modal': usernameCheck || errors.username }]" maxlength="30" >
                                        <CustomSelect v-else :class="['select-search', { 'select-toggle-error': usernameCheck || errors.username }]" v-model="form.username" :options="adUserOptions" :always-up="false" :placeholder="loadingAdUsers ? 'Loading AD Users...' : 'Select AD User*'" name="adUserModal" />
                                        <label v-if="!isDomainAccountMode" class="title-label">Username*</label>
                                        <div v-show="usernameCheck" class="validate"><i class="fa-solid fa-circle-exclamation"></i> This username is already in the system.</div>
                                        <div v-show="errors.username && !usernameCheck" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.username === 'string' ? errors.username : 'This field is required.' }}</div>
                                    </div>
                                </div>

                                <div class="permissions-grid-2">
                                    <div class="input-group" v-has-value v-if="mode !== 'edit' && !isDomainAccountMode">
                                        <input v-model="form.password" :required="!isDomainAccountMode" :type="passwordVisible ? 'text' : 'password'" name="password" autocomplete="off" :class="['input', { 'form-input-modal': errors.password }]" maxlength="30">
                                        <button type="button" class="toggle-visibility" @click="passwordVisible = !passwordVisible" aria-label="Toggle password visibility">
                                            <i :class="passwordVisible ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
                                        </button>
                                        <label class="title-label">Password*</label>
                                        <div v-show="errors.password" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.password === 'string' ? errors.password : 'This field is required.' }}</div>
                                    </div>
                                    <div class="input-group" v-has-value v-if="mode !== 'edit' && !isDomainAccountMode">
                                        <input v-model="form.confirmPassword" :required="!isDomainAccountMode" :type="confirmPasswordVisible ? 'text' : 'password'" name="confirmPassword" autocomplete="off" :class="['input', { 'form-input-modal': errors.confirmPassword }]" maxlength="30">
                                        <button type="button" class="toggle-visibility" @click="confirmPasswordVisible = !confirmPasswordVisible" aria-label="Toggle confirm password visibility">
                                            <i :class="confirmPasswordVisible ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
                                        </button>
                                        <label class="title-label">Confirm Password*</label>
                                        <div v-show="errors.confirmPassword" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.confirmPassword === 'string' ? errors.confirmPassword : 'This field is required.' }}</div>
                                    </div>
                                    <div class="input-group" v-has-value>
                                        <input v-model="form.firstName" required type="text" name="firstName" autocomplete="off" :class="['input', { 'form-input-modal': errors.firstName }]" maxlength="30">
                                        <label class="title-label">First Name*</label>
                                        <div v-show="errors.firstName" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.firstName === 'string' ? errors.firstName : 'This field is required.' }}</div>
                                    </div>
                                    <div class="input-group" v-has-value>
                                        <input v-model="form.lastName" required type="text" name="lastName" autocomplete="off" :class="['input', { 'form-input-modal': errors.lastName }]" maxlength="30">
                                        <label class="title-label">Last Name*</label>
                                        <div v-show="errors.lastName" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.lastName === 'string' ? errors.lastName : 'This field is required.' }}</div>
                                    </div>
                                    <div class="input-group" v-has-value v-if="!isDomainAccountMode">
                                        <input v-model="form.email" required type="text" name="email" autocomplete="off" class="input" maxlength="30">
                                        <label class="title-label">Email</label>
                                        <div v-show="errors.email" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.email === 'string' ? errors.email : 'Please enter a valid email address.' }}</div>
                                    </div>
                                    <div class="input-group" v-has-value v-if="!isDomainAccountMode">
                                        <input v-model="form.phone" required type="text" name="phone" autocomplete="off" class="input" maxlength="10">
                                        <label class="title-label">Phone</label>
                                    </div>
                                    <div class="input-group">
                                        <CustomSelect :class="['select-search', { 'select-toggle-error': errors.group }]" v-model="selectedGroupId" :options="groupOptions" :always-up="false" placeholder="Select Group*" name="groupModal" />
                                        <div v-show="errors.group" class="validate"><i class="fa-solid fa-circle-exclamation"></i> This dropdown is required.</div>
                                    </div>
                                    <div class="input-group" :class="{ 'select-disabled': !selectedGroupId }">
                                        <CustomSelect :class="['select-search', { 'select-toggle-error': errors.team }]" v-model="selectedTeamId" :always-up="false" :options="teamOptions" placeholder="Select Team*" name="teamModal" />
                                        <div v-show="errors.team" class="validate"><i class="fa-solid fa-circle-exclamation"></i> This dropdown is required.</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
                <div class="col-lg-6" style="margin-bottom: 14px;">
                    <!-- Select Role Card -->
                    <div class="card card-right">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-start justify-content-between"
                                    style="margin-bottom: 18px;">
                                    <div class="d-flex align-items-center">
                                        <div class="d-flex align-items-center justify-content-center me-1"
                                            style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                            <i class="fas fa-shield-alt" style="color:#2b6cb0;font-size:18px"></i>
                                        </div>
                                        <h5 class="card-title mb-2 mt-1">Select Role</h5>
                                    </div>
                                </div>

                                <div v-show="errors.role" class="validate"><i class="fa-solid fa-circle-exclamation"></i> This Select Role is required.</div>
                                <div class="role-cards" id="roleCards" :class="{ disabled: roleCardsDisabled }">
                                    <label class="role-card" :class="[ { selected: selectedBaseRoleKey==='administrator' }, { 'role-card-error': errors.role } ]" @click.prevent="selectBaseRole('administrator')">
                                        <input type="checkbox" name="role" value="administrator" :checked="selectedBaseRoleKey==='administrator'">
                                        <div class="role-icon"><i class="fas fa-crown"></i></div>
                                        <div class="role-name">Administrator</div>
                                        <div class="role-desc">Full system access</div>
                                    </label>
                                    <label class="role-card" :class="[ { selected: selectedBaseRoleKey==='auditor' }, { 'role-card-error': errors.role } ]" @click.prevent="selectBaseRole('auditor')">
                                        <input type="checkbox" name="role" value="auditor" :checked="selectedBaseRoleKey==='auditor'">
                                        <div class="role-icon"><i class="fas fa-clipboard-check"></i></div>
                                        <div class="role-name">Auditor</div>
                                        <div class="role-desc">Read & audit access</div>
                                    </label>
                                    <label class="role-card" :class="[ { selected: selectedBaseRoleKey==='operator' }, { 'role-card-error': errors.role } ]" @click.prevent="selectBaseRole('operator')">
                                        <input type="checkbox" name="role" value="operator" :checked="selectedBaseRoleKey==='operator'">
                                        <div class="role-icon"><i class="fas fa-headset"></i></div>
                                        <div class="role-name">Operator</div>
                                        <div class="role-desc">Standard operations</div>
                                    </label>
                                </div>

                                <div class="custom-role-row" style="display: flex; gap: 12px; align-items: stretch;">
                                    <div class="custom-dropdown" id="otherRoleDropdown" :class="{ open: otherRoleOpen, selected: selectedCustomRoleId }" style="flex: 1;">
                                        <div class="dropdown-selected" @click="toggleOtherRoleDropdown">
                                            <span class="dropdown-text">
                                                <i v-if="selectedCustomRoleId" class="fas fa-user" style="margin-right: 8px;"></i>
                                                {{ selectedCustomRoleName || 'Select Custom Role' }}
                                            </span>
                                            <i class="fas fa-chevron-down dropdown-arrow"></i>
                                        </div>
                                        <div class="dropdown-options">
                                            <div v-if="customRoles.length === 0" class="dropdown-option disabled" style="color: #94a3b8; cursor: default; pointer-events: none;">
                                                <i class="fas fa-info-circle"></i>
                                                <span>No custom roles available</span>
                                            </div>
                                            <div v-else>
                                                <div v-for="role in customRoles" :key="role.id" class="dropdown-option" :class="{ selected: selectedCustomRoleId === role.id }" @click="selectCustomRole(role)">
                                                    <i class="fas fa-user"></i>
                                                    <span>{{ role.name }}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <input type="hidden" name="otherRole" id="otherRoleInput" :value="selectedCustomRoleId || ''">
                                    </div>
                                    <button class="customize-btn" type="button" @click="clearCustomRole"
                                        style="display: flex; align-items: center; justify-content: center; margin: 0;">
                                        <i class="fas fa-eraser" style="margin-right: 6px;"></i> Clear
                                    </button>
                                </div>


                            </div>
                        </div>
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-start justify-content-between"
                                    style="margin-bottom: 18px;">
                                    <div class="d-flex align-items-center">
                                        <div class="d-flex align-items-center justify-content-center me-1"
                                            style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                            <i class="fas fa-database" style="color:#2b6cb0;font-size:18px"></i>
                                        </div>
                                        <h5 class="card-title mb-2 mt-1">Select Database Server</h5>
                                    </div>
                                    <div class="d-flex align-items-center">
                                        <button type="button" class="btn-role btn-secondary" @click="resetDatabase"
                                            style="margin-right: 6px">
                                            <i class="fas fa-undo"></i>
                                            Reset to Default
                                        </button>
                                        <button class="customize-btn" type="button" @click="clearDatabaseScope">
                                            <i class="fas fa-eraser" style="margin-right: 6px;"></i> Clear
                                        </button>
                                    </div>
                                </div>

                                <div class="database-grid">
                                    <label class="db-card">
                                        <input type="checkbox" value="all" :checked="selectedAllDatabases" @change="toggleAllDatabases">
                                        <span class="db-checkbox"></span>
                                        <span class="db-name">All Databases</span>
                                    </label>
                                    <label class="db-card" v-for="db in databases" :key="db.id">
                                        <input type="checkbox" :value="db.id" :checked="selectedDatabaseIds.includes(String(db.id))" @change="() => toggleDatabase(db)">
                                        <span class="db-checkbox"></span>
                                        <span class="db-name">{{ db.database_name }}</span>
                                    </label>
                                </div>

                            </div>
                        </div>
                    </div>

                </div>

                <div class="col-lg-12">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px;">
                                <div class="d-flex align-items-center">
                                    <div class="d-flex align-items-center justify-content-center me-1"
                                        style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                        <i class="fas fa-key" style="color:#2b6cb0;font-size:18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Permissions</h5>
                                </div>
                            </div>

                            <div class="permissions-grid" id="permissionsGrid">
                                <template v-for="type in orderedTypes" :key="type">
                                    <div v-if="groupedPermissions[type] && groupedPermissions[type].length"
                                        class="permission-group-header">{{ typeLabels[type] }}</div>

                                    <label v-for="perm in groupedPermissions[type]" :key="perm.action"
                                        :class="['permission-item']">
                                        <input type="checkbox" disabled :data-permission="perm.action" :checked="!!selectedPermissions[perm.action]" @change="() => togglePermission(perm)">
                                        <span class="perm-checkbox"></span>
                                        <span class="perm-label">{{ perm.name }}</span>
                                    </label>
                                </template>
                            </div>

                            <div class="button-group">
                                <button class="btn btn-primary" type="button" @click="submit">
                                    <i class="fas fa-check"></i>
                                    {{ mode === 'edit' ? 'Save User' : 'Add User' }}
                                </button>
                                <button class="btn btn-secondary" @click="cancel">
                                    <i class="fas fa-times"></i>
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </MainLayout>
</template>

<script setup>
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import CustomSelect from '../components/CustomSelect.vue'
import { useUserForm } from '../composables/useUserForm'

const props = defineProps({ 
    mode: { type: String, default: null },
    initialData: { type: Object, default: null }
})

const {
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
    teamOptions,
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
    fetchGetAllRolesPermissions,
    isDomainAccountMode,
    adUsers,
    loadingAdUsers,
    adUserOptions,
    showDomainAccountBtn,
    fetchAdUsers,
    toggleDomainAccountMode
} = useUserForm(props)
</script>

<style scoped src="../assets/css/user-form.css"></style>
