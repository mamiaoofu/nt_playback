<template>
  <MainLayout>
    <div class="main-wrapper container-fluid py-3">
      <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: pageTitle }]" />
      <ModalDowload v-model="downloading" :progress="downloadProgress" :speed="downloadSpeed" :remaining="downloadRemaining" />
      <div class="col-lg-12">
        <div class="card">
          <div class="card-body card-body-datatable" style="position: relative;">
            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px;">
              <div class="d-flex align-items-center">
                <div class="d-flex align-items-center justify-content-center me-1"
                  style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                  <i class="fas fa-clipboard-check" style="color:#2b6cb0;font-size:18px"></i>
                </div>
                <h5 class="card-title mb-2 mt-1">{{ pageTitle }}</h5>
              </div>
              <div class="d-flex align-items-center">
                 <div style="width:260px;">
                    <SearchInput ref="searchInputRef" v-model="searchQuery" :placeholder="'Search...'" @typing="onTyping" @clear="clearSearchQuery" />
                  </div>
                  <div v-if="canExport" class="ms-2 export-group" ref="exportWrap">
                    <button type="button" class="btn btn-primary btn-sm export-icon" @click.stop="toggleExport" :aria-expanded="exportOpen">
                      <i class="fa-solid fa-download" style="color: #fff;"></i>
                    </button>
                    <ul v-show="exportOpen" class="export-dropdown" @click.stop>
                      <li>
                        <label class="dropdown-item">
                          <input type="checkbox" v-model="exportSelections.pdf" style="margin-right:8px;"> PDF
                        </label>
                      </li>
                      <li>
                        <label class="dropdown-item">
                          <input type="checkbox" v-model="exportSelections.excel" style="margin-right:8px;"> Excel
                        </label>
                      </li>
                      <li>
                        <label class="dropdown-item">
                          <input type="checkbox" v-model="exportSelections.csv" style="margin-right:8px;"> CSV
                        </label>
                      </li>
                      <li style="padding:8px;">
                        <div class="export-actions">
                          <button class="btn btn-sm btn-light export-action-btn" type="button" @click="cancelExport">Cancel</button>
                          <button class="btn btn-sm btn-primary export-action-btn" type="button" @click="confirmExport">Confirm</button>
                        </div>
                      </li>
                    </ul>
                  </div>
              </div>
            </div>

            <div>
              <form v-if="canView" id="filterForm" class="filter-row">

                <div class="input-group" >
                  <CustomSelect class="select-search select-checkbox" v-model="filters.ticketID" :options="ticketOptions" :placeholder="typeUrl === 'delegate' ? 'Delegate ID' : 'Ticket ID'" name="ticketID" />
                </div>

                <div class="input-group" >
                  <CustomSelect class="select-search select-checkbox" v-model="filters.createdBy" :options="createdByOptions" placeholder="Create By" name="createdBy" />
                </div>

                <div :class="['input-group', { 'has-value': !!filters.start_date }]">
                  <input ref="startInput" v-flatpickr="{ target: filters, key: 'start_date'}" required type="text" name="start_date" autocomplete="off" class="input">
                  <label class="floating-label">From</label>
                  <span class="calendar-icon" @click="startInput && startInput.focus()"><i class="fa-regular fa-calendar"></i></span>
                </div>
                <div :class="['input-group', { 'has-value': !!filters.end_date }]">
                  <input ref="endInput" v-flatpickr="{ target: filters, key: 'end_date'}" required type="text" name="end_date" autocomplete="off" class="input">
                  <label class="floating-label">To</label>
                  <span class="calendar-icon" @click="endInput && endInput.focus()"><i class="fa-regular fa-calendar"></i></span>
                </div>

                <div class="input-group" style="flex: 0 0 auto;">
                  <button type="button" class="btn btn-light" id="resetFilterBtn" @click="resetFilters" style="height: 31px; border: 1px solid #e2e8f0;border-radius: 10px;font-size: 12px;margin-top: -7px;">
                    <i class="fas fa-undo"></i> Reset
                  </button>
                </div>

              </form>
            </div>

            <div class="table-area">
            <TableTemplate
              :columns="columns"
              :rows="paginatedRecords"
              :start-index="startIndex"
              :loading="loading"
              :per-page="perPage"
              :per-page-options="perPageOptions"
              :current-page="currentPage"
              :total-items="totalItems"
              :sort-column="sortColumn"
              :sort-direction="sortDirection"
              @sort-change="onSortChange"
              @page-change="changePage"
              @per-change="setPerPage"
              @delete="onRowDelete">

              <template #cell-status="{ row }" v-if="(typeUrl === 'delegate' && (authStore.hasPermission('Change Delegate File Status') && authStore.hasPermission('Delegate Management'))) || (typeUrl === 'ticket' && (authStore.hasPermission('Change Ticket File Status') && authStore.hasPermission('Ticket Management')))">
                  <label class="switch_status">
                      <input type="checkbox" :checked="row.status"
                          @change="() => toggleUserStatus(row.user_id, row.id)" />
                      <span class="slider_status round"></span>
                  </label>
              </template>

              <template #cell-limit_access_time="{ row }" v-if="typeUrl === 'ticket'">
                <div v-if="row.limit_access_time || row.limit_access_time === 0">
                  {{ row.access_time }} / {{ row.limit_access_time }}
                </div>
                <div v-else>
                  -
                </div>
              </template>

                <template #cell-download="{ row }">
                  <div class="text-start">
                    <i v-if="row.download === true || row.dowload === true" class="fa-solid fa-check" style="color:green"></i>
                    <i v-else class="fa-solid fa-xmark" style="color:red"></i>
                  </div>
                </template>

              <template #cell-action="{ row }" v-if="typeUrl === 'ticket'">
                  <div class="input-group" >
                  <button type="button" class="group-send-btn" id="Resend" @click="resendTicket(row.id, row.user_id)" >
                    <i class="fa-solid fa-envelope" ></i>
                  </button>
                </div>
              </template>

            </TableTemplate>
            </div>

          </div>
        </div>
      </div>
    </div>
    <ModalRecentFileShare v-model="recentModalOpen" :resultType="recentResultType" :resultData="recentResultData" />
  </MainLayout>
</template>

<script setup>
import { computed } from 'vue'
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import TableTemplate from '../components/TableTemplate.vue'
import CustomSelect from '../components/CustomSelect.vue'
import SearchInput from '../components/SearchInput.vue'
import { useFileShareManagement } from '../composables/useFileShareManagement'
import ModalRecentFileShare from '../components/ModalRecentFileShare.vue'
import ModalDowload from '../components/ModalDowload.vue'

const {
    authStore,
    searchQuery,
    exportOpen,
    exportWrap,
    perPageOptions,
    perPage,
    currentPage,
    filters,
    startInput,
    endInput,
    searchInputRef,
    perWrap,
    perDropdownOpen,
    records,
    totalItems,
    loading,
    columns,
    requiredPermission,
    canView,
    canExport,
    totalPages,
    startIndex,
    paginatedRecords,
    type,
    sortColumn,
    sortDirection,
    ticketOptions,
    createdByOptions,
    recentModalOpen,
    recentResultData,
    recentResultType,
    typeUrl,
    pageTitle,
    exportSelections,
    downloading,
    downloadProgress,
    downloadSpeed,
    downloadRemaining,
    cancelExport,
    onTyping,
    setPerPage,
    changePage,
    clearSearchQuery,
    resetFilters,
    fetchData,
    toggleExport,
    onSortChange,
    onRowDelete,
    toggleUserStatus,
    resendTicket,
    confirmExport,
} = useFileShareManagement()


</script>
<style scoped src="../assets/css/user-log.css"></style>
<style scoped src="../assets/css/user-management.css"></style>