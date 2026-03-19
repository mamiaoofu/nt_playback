<template>
    <MainLayout>
        <div class="main-wrapper container-fluid py-3">
            <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: 'User Management' }]" />
            <div class="col-lg-12">
                <div class="card">
                    <div class="card-body card-body-datatable">
                        <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
                            <div class="d-flex align-items-center">
                                <div class="d-flex align-items-center justify-content-center me-1"
                                    style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                                    <i class="fas fa-users" style="color: #2b6cb0; font-size: 18px"></i>
                                </div>
                                <h5 class="card-title mb-2 mt-1">User Management</h5>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width:260px;">
                                    <SearchInput ref="searchInputRef" v-model="searchQuery" :placeholder="'Search...'" @typing="onTyping" @enter="onSearch" @clear="clearSearchQuery" />
                                </div>
                                <router-link v-if="authStore.hasPermission('Add User')" to="/user-management/add">
                                <button class="btn-role btn-primary btn-sm" id="addGroupBtn"
                                    @click.stop="openCreateGroup">
                                    <i class="fas fa-plus"></i>
                                    Add User
                                </button>
                                </router-link>
                            </div>
                        </div>
                        <TableTemplate
                            :columns="columns"
                            :rows="paginatedRecords"
                            :start-index="startIndex"
                            :loading="loading"
                            action-id-key="user.id"
                            :per-page="perPage"
                            :per-page-options="perPageOptions"
                            :current-page="currentPage"
                            :total-items="totalItems"
                            :sort-column="sortColumn"
                            :sort-direction="sortDirection"
                            @sort-change="onSortChange"
                            @edit="onRowEdit"
                            @delete="onRowDelete"
                            @reset="onRowReset"
                            @page-change="changePage"
                            @per-change="setPerPage">

                            <template #cell-username="{ row }">
                                {{ row.user?.username || '' }}
                            </template>

                            <template #cell-full_name="{ row }">
                                {{ (row.user?.first_name || '') + ' ' + (row.user?.last_name || '') }}
                            </template>

                            <template #cell-email="{ row }">
                                {{ row.user?.email || '-' }}
                            </template>

                            <template #cell-role="{ row }">
                                <span
                                    :class="['role-badge', (['administrator', 'auditor', 'operator'].includes((row.permission || '').toLowerCase()) ? (row.permission || '').toLowerCase() : 'other')]">
                                    {{ row.permission || '-' }}
                                </span>
                            </template>

                            <template #cell-group="{ row }">
                                {{ extractGroup(row) || '-' }}
                            </template>

                            <template #cell-team="{ row }">
                                {{ extractTeam(row) || '-' }}
                            </template>

                            <template #cell-database_servers="{ row }">
                                <template v-if="getDbList(row).length <= 1">
                                    {{ getDbList(row)[0] || '-' }}
                                </template>
                                <template v-else>
                                    <span class="group-summary" @mouseenter="showDbTooltip($event, row)"
                                        @mouseleave="hideDbTooltip">
                                        Database Server ({{ getDbList(row).length }})
                                    </span>
                                </template>
                            </template>

                            <template #cell-phone="{ row }">
                                {{ row.phone || '-' }}
                            </template>

                            <template #cell-status="{ row }">
                                <label class="switch_status">
                                    <input type="checkbox" :checked="row.is_active"
                                        @change="() => toggleUserStatus(row.user?.id, row)" />
                                    <span class="slider_status round"></span>
                                </label>
                            </template>

                        </TableTemplate>

                        <teleport to="body">
                            <div v-if="dbTooltip.visible" ref="dbTooltipEl"
                                class="file-name-tooltip tooltip bs-tooltip-top show"
                                :class="dbTooltipPlacement === 'top' ? 'tooltip-top' : 'tooltip-bottom'"
                                :style="dbTooltip.style"
                                @mouseenter="cancelHideDb" @mouseleave="hideDbTooltip">
                                <div class="tooltip-arrow"></div>
                                <div class="tooltip-inner d-flex flex-column">
                                    <div class="tooltip-after">Database Server</div>
                                    <ul class="tooltip-after-list">
                                        <li v-for="(d, di) in dbTooltip.items" :key="di" style="margin:2px 0">- {{ d }}
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </teleport>

                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
</template>

<script setup>
import SearchInput from '../components/SearchInput.vue'
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import TableTemplate from '../components/TableTemplate.vue'
import { useUserManagement } from '../composables/useUserManagement'

const {
    authStore,
    searchQuery,
    searchInputRef,
    perWrap,
    perDropdownOpen,
    perPageOptions,
    perPage,
    currentPage,
    records,
    totalItems,
    loading,
    sortColumn,
    sortDirection,
    expanded,
    dbTooltip,
    dbTooltipEl,
    dbTooltipPlacement,
    columns,
    totalPages,
    startIndex,
    paginatedRecords,
    onTyping,
    onSearch,
    clearSearchQuery,
    onSortChange,
    setPerPage,
    changePage,
    onRowEdit,
    onRowDelete,
    onRowReset,
    extractGroup,
    extractTeam,
    getDbList,
    toggleUserStatus,
    showDbTooltip,
    hideDbTooltip,
    cancelHideDb,
    openCreateGroup
} = useUserManagement()
</script>

<style scoped src="../assets/css/user-management.css"></style>
