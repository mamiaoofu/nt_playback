<template>
  <MainLayout>
    <div class="main-wrapper-container">
      <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: 'Role & Permissions Configuration' }]" />
      <div class="card">
        <div class="card-body">
          <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
            <div class="d-flex align-items-center">
              <div class="d-flex align-items-center justify-content-center me-1"
                style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                <i class="fas fa-shield-alt" style="color: #2b6cb0; font-size: 18px"></i>
              </div>
              <h5 class="card-title mb-2 mt-1">Base Roles</h5>
            </div>
          </div>

          <div class="roles-grid" id="baseRolesGrid">
            <div class="role-box" data-role="1" @click.stop="authStore.hasPermission('Edit Base Roles') && openEditRole(1, 'base')">
              <div class="role-box-header">
                <div class="role-box-icon">
                  <i class="fas fa-crown"></i>
                </div>
                <span class="role-box-badge">Click to edit</span>
              </div>
              <div class="role-box-name">Administrator</div>
              <div class="role-box-desc">Full system access</div>
            </div>
            <div class="role-box" data-role="2" @click.stop="authStore.hasPermission('Edit Base Roles') && openEditRole(2, 'base')">
              <div class="role-box-header">
                <div class="role-box-icon">
                  <i class="fas fa-clipboard-check"></i>
                </div>
                <span class="role-box-badge">Click to edit</span>
              </div>
              <div class="role-box-name">Auditor</div>
              <div class="role-box-desc">Read & audit access</div>
            </div>
            <div class="role-box" data-role="3" @click.stop="authStore.hasPermission('Edit Base Roles') && openEditRole(3, 'base')">
              <div class="role-box-header">
                <div class="role-box-icon">
                  <i class="fas fa-headset"></i>
                </div>
                <span class="role-box-badge">Click to edit</span>
              </div>
              <div class="role-box-name">Operator/Agent</div>
              <div class="role-box-desc">Standard operations</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card card-custom-role">
        <div class="card-body">
          <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
            <div class="d-flex align-items-center">
              <div class="d-flex align-items-center justify-content-center me-1"
                style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                <i class="fas fa-users-cog" style="color: #2b6cb0; font-size: 18px"></i>
              </div>
              <h5 class="card-title mb-2 mt-1">Custom Roles</h5>
            </div>
            <div style="display: flex; align-items: center; gap: 10px">
              <div data-v-2dc54a20="" class="search-group" style="width: 260px; position: relative">
                <i data-v-2dc54a20="" class="fa-solid fa-magnifying-glass search-icon"></i>
                <input data-v-2dc54a20="" v-model="searchQuery" type="text" class="form-control form-control-sm search-input"
                  placeholder="Search..." fdprocessedid="lf0zjn" />
              </div>
              <button v-if="authStore.hasPermission('Add New Custom Roles')" type="button" class="btn-role btn-primary btn-sm" id="addRoleBtn" @click.stop="openCreateRole">
                <i class="fas fa-plus"></i>
                Add New Role
              </button>
            </div>
          </div>

          <div class="custom-roles-list" id="customRolesList">
            <div v-if="loading" class="empty-state" style="display:flex;align-items:center;justify-content:center;padding:24px;">
              <div>Loading...</div>
            </div>
            <template v-else>
              <div v-if="filteredRoles.length" class="custom-roles-container">
                  <div v-for="role in filteredRoles" :key="role.id" class="custom-role-item"
                    @click.stop="authStore.hasPermission('Edit Custom Roles') && openEditRole(role.id, 'edit')">
                  <div class="custom-role-info">
                    <div class="custom-role-name">{{ role.name }}</div>
                    <span class="custom-role-perms">Permissions</span>
                  </div>
                  <div class="custom-role-actions">
                    <span v-if="authStore.hasPermission('Edit Custom Roles')" class="role-box-badge">Click to edit</span>
                    <button v-if="authStore.hasPermission('Delete Custom Roles')" type="button" class="group-delete-btn" @click.stop="deleteCustomRole(role.id)">
                      <i class="fas fa-trash" style="font-size: 12px;"></i>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">
                <i class="fa-solid fa-dove"></i>
                <p v-if="!userPermissionOther.length">No custom roles yet. Click "Add New Role" to create one.</p>
                <p v-else>No roles found matching your search.</p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
  <ModalConfiguration v-model="showBaseRoleModal" :role-id="selectedBaseRoleId" :role-name="selectedBaseRoleName" :mode="selectedModalMode" @role-created="onRoleCreated" @role-updated="onRoleUpdated" />
</template>
<script setup>
import MainLayout from '../layouts/MainLayout.vue';
import Breadcrumbs from '../components/Breadcrumbs.vue'
import ModalConfiguration from '../components/ModalConfiguration.vue'
import { useRole } from '../composables/useRole'

const {
  userPermissionOther,
  authStore,
  loading,
  showBaseRoleModal,
  selectedBaseRoleId,
  selectedBaseRoleName,
  selectedModalMode,
  searchQuery,
  filteredRoles,
  fetchIndexRoles,
  openEditRole,
  openCreateRole,
  deleteCustomRole,
  onRoleCreated,
  onRoleUpdated
} = useRole()
</script>

<style scoped src="../assets/css/role.css"></style>
