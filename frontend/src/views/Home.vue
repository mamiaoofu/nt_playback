<template>
  <MainLayout>
    <div class="main-wrapper container-fluid-home py-3">
      <Breadcrumbs :items="[{ text: 'Home', to: '/' }]" />
      <ModalDowload v-model="downloading" :progress="downloadProgress" :speed="downloadSpeed" :remaining="downloadRemaining" />
      
      <div class="row col-lg-12">
        <div v-if="authStore.hasPermission('Query Audio')" class="col-lg-2">
          <div class="card">
            <div class="card-body">
              <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px;">
                <div class="d-flex align-items-center">
                  <div class="d-flex align-items-center justify-content-center me-1"
                    style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                    <i class="fa-solid fa-filter" style="color:#2b6cb0;font-size:18px"></i>
                  </div>
                  <h5 class="card-title mb-2 mt-1">Filters</h5>
                </div>
              </div>
              <!-- Content Filters-->
              <div class="filter-card">

                <div class="input-group" style="margin-top: 6px;">
                  <CustomSelect class="select-checkbox" v-model="filters.databaseServer"
                    :options="mainDbOptions"
                    placeholder="Database Server" name="databaseServer" />
                </div>

                <div class="input-group" v-has-value>
                  <input ref="fromInput" v-flatpickr="{ target: filters, key: 'from' }" required type="text" name="from"
                    autocomplete="off" class="input">
                  <label class="floating-label">From</label>
                  <span class="calendar-icon" @click="fromInput && fromInput.focus()"><i
                      class="fa-regular fa-calendar"></i></span>
                </div>

                <div class="input-group" v-has-value>
                  <input ref="toInput" v-flatpickr="{ target: filters, key: 'to' }" required type="text" name="to"
                    autocomplete="off" class="input">
                  <label class="floating-label">To</label>
                  <span class="calendar-icon" @click="toInput && toInput.focus()"><i
                      class="fa-regular fa-calendar"></i></span>
                </div>

                <div class="input-group" v-has-value>
                  <input ref="durationInput" v-model="filters.duration" v-flatpickr="{ target: filters, key: 'duration', mode: 'duration_range', options: { enableTime: true, noCalendar: true, enableSeconds: true, time_24hr: true, dateFormat: 'H:i:S', defaultHour: 0, defaultMinute: 0 } }" required type="text" name="duration" autocomplete="off" class="input">
                  <label class="floating-label">Duration</label>
                </div>

                <div class="input-group" v-has-value>
                  <input v-model="filters.fileName" required type="text" name="fileName" autocomplete="off" class="input">
                  <label class="floating-label">File Name</label>
                </div>

                <div class="input-group">
                  <CustomSelect class="select-checkbox"  v-model="filters.callDirection"
                    :options="callDirectionOptions"
                    placeholder="Call Direction" name="callDirection" />
                </div>

                <div class="input-group" v-has-value>
                  <input v-model="filters.customerNumber" required type="text" name="customerNumber" autocomplete="off" class="input">
                  <label class="floating-label">Customer Number</label>
                </div>

                <div class="input-group" v-has-value>
                  <input v-model="filters.extension" required type="text" name="extension" autocomplete="off" class="input">
                  <label class="floating-label">Extension</label>
                </div>

                <div class="input-group" >
                  <CustomSelect class="select-search select-checkbox" :class="{ up: 'up' }" v-model="filters.agent"
                    :options="agentOptions"
                    placeholder="Agent" name="agent" />
                </div>

                <div class="input-group" v-has-value>
                  <input v-model="filters.fullName" required type="text" name="fullName" autocomplete="off" class="input">
                  <label class="floating-label">Full Name</label>
                </div>

                <div class="input-group" v-has-value>
                  <input v-model="filters.customField" required type="text" name="customField" autocomplete="off" class="input">
                  <label class="floating-label">Custom Field</label>
                </div>

              </div>

              <div class="my-favorite-search">
                
                  <div class="d-flex justify-content-center" v-if="authStore.hasPermission('File Share')" style="padding-right: 12px;padding-left: 8px; position: relative;">
                      <button class="btn btn-light" type="button" id="fileShare" @click="onFileShareClick" style="width: 100%;text-align: left;font-size: 12px;margin-bottom: 6px; position: relative;">
                        <i class="fa-solid fa-share-nodes"></i> Delegate file 
                      </button>
                      <span v-if="showFileShareNotification" id="notiFileShare" class="badge badge-danger" style="position: absolute; top: -6px; right: 8px;width: 16px;"><i class="fa-solid fa-exclamation"></i></span>
                     </div>
                <div class="card">
                  <div class="card-body" style="padding: 8px;">

                    <div class="d-flex justify-content-center" v-if="authStore.hasPermission('My Favorite Search')" >
                      <button class="btn btn-light" type="button" id="addFavorite" @click="showFavoriteModal = true" style="width: 100%;text-align: left;font-size: 12px;margin-bottom: 4px;">
                        <i class="fa-regular fa-bookmark"></i> My Favorite Search
                      </button>
                    </div>

                    <div class="dropup d-flex justify-content-center" ref="recentWrap">
                      <button class="btn btn-light" type="button" @click.stop="toggleRecent" :aria-expanded="recentOpen" style="width: 100%;font-size: 12px;margin-bottom: 4px;">
                        <div style="text-align: left;"><i class="fa-regular fa-clock"></i> <span>Recent</span></div>
                      </button>
                      <ul v-show="recentOpen" class="recent-dropdown">
                        <li><button class="dropdown-item" type="button" @click="applyLatestRecent">Latest</button></li>
                        <li><button class="dropdown-item" type="button" @click="applyRecentRange('1h')">1 hour</button></li>
                        <li><button class="dropdown-item" type="button" @click="applyRecentRange('1d')">1 day</button></li>
                        <li><button class="dropdown-item" type="button" @click="applyRecentRange('1w')">1 week</button></li>
                        <li><button class="dropdown-item" type="button" @click="applyRecentRange('1m')">1 month</button></li>
                        <li><button class="dropdown-item" type="button" @click="applyRecentRange('1y')">1 year</button></li>
                        <!-- dynamic recent entries hidden (only static range menu shown) -->
                      </ul>
                      <label for="recentDropdown"></label>
                    </div>

                    <div class="col-lg-12">
                      <div class="row g-0-3">
                        <div class="col-lg-6">
                          <button class="btn btn-primary w-97" type="button" id="search_audio" style="font-size: 12px;"
                            @click="onSearch"><span>Search</span></button>
                        </div>
                        <div class="col-lg-6">
                          <button class="btn btn-light w-97" type="button" id="reset_audio"
                            style="border-color: #f2e1e1;font-size: 12px;" @click="onReset"><span>Reset</span></button>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
        <div :class="authStore.hasPermission('Query Audio') ? 'col-lg-10' : 'col-lg-12'">
          <div class="card">
            <div class="card-body card-body-datatable" style="height: calc(100vh - 160px);">
              <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px;">
                <div class="d-flex align-items-center">
                  <div class="d-flex align-items-center justify-content-center me-1"
                    style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                    <i class="fa-solid fa-file-audio" style="color:#2b6cb0;font-size:18px"></i>
                  </div>
                  <h5 class="card-title mb-2 mt-1">Audio Records</h5>
                </div>
                <div class="d-flex align-items-center">
                    <button v-if="authStore.hasPermission('File Share')" class="btn btn-light" id="shareBtn" style="position: relative;margin-right: 8px;font-size: 11px;color: #495669;font-weight: 600;" @click="openShare">
                        <i class="fa-solid fa-share-nodes"></i> File Share
                        <span v-if="selectedCount > 0" class="badge badge-danger" id="shareCount">{{ selectedCount }}</span>
                      </button>
                  <div style="width:260px;">
                    <SearchInput ref="searchInputRef" v-model="searchQuery" :placeholder="'Search...'"
                      @typing="onTyping" @enter="onSearch" @clear="clearSearchQuery" />
                  </div>
                  <div v-if="authStore.hasPermission('Export Recordings')" class="ms-2 export-group" ref="exportWrap">
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
                      <li v-if="authStore.hasPermission('Download Audio')">
                        <label class="dropdown-item">
                          <input type="checkbox" v-model="exportSelections.voice" style="margin-right:8px;"> Voice
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

                <TableTemplate
                    :columns="columns"
                    :rows="paginatedRecords"
                    :start-index="startIndex"
                    :loading="loading"
                    show-selection
                    call-direction-key="call_direction"
                    :per-page="perPage"
                    :per-page-options="perPageOptions"
                    :current-page="currentPage"
                    :total-items="totalItems"
                    :sort-column="sortColumn"
                    :sort-direction="sortDirection"
                    @sort-change="onSortChange"
                    @edit="onRowEdit"
                    @delete="onRowDelete"
                    @row-dblclick="onRowDblClick"
                    @page-change="changePage"
                    @per-change="setPerPage">

                  <template #header-checked>
                    <input type="checkbox" class="form-check-input" :checked="selectAllChecked" @change.stop="toggleSelectAll" />
                  </template>

                  <template #cell-checked="{ row, index }">
                    <input type="checkbox" class="form-check-input" :checked="!!row.checked" @change.stop="toggleRowSelection(row)" />
                  </template>

                </TableTemplate>

              <!-- Content Audio Records-->
            </div>
          </div>
        </div>

      </div>
    </div>
  </MainLayout>
  <ModalHome v-if="authStore.hasPermission('My Favorite Search')" v-model="showFavoriteModal" :favorites="favoriteSearchAll" :mainDbOptions="mainDbOptions" :agentOptions="agentOptions" @apply="applyFavorite" @edit="editFavorite" @delete="deleteFavorite" />
  <ModalFileShare v-model="showShareModal" :files="selectedFiles" @share="onCreate" />
  <AudioPlayer v-model="showAudioModal" :src="audioSrc" :metadata="audioMetadata" />
</template>

<script setup>
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import CustomSelect from '../components/CustomSelect.vue'
import ModalHome from '../components/ModalHome.vue'
import TableTemplate from '../components/TableTemplate.vue'
import SearchInput from '../components/SearchInput.vue'
import AudioPlayer from '../components/AudioPlayer.vue'
import ModalFileShare from '../components/ModalFileShare.vue'
import ModalDowload from '../components/ModalDowload.vue'
import { useHome } from '../composables/useHome'
import { ref } from 'vue'

const {
  authStore,
  filters,
  searchQuery,
  searchInputRef,
  perPageOptions,
  perPage,
  currentPage,
  perDropdownOpen,
  perDropdownUp,
  mainDbOptions,
  favoriteSearchAll,
  agentOptions,
  callDirectionOptions,
  perWrap,
  fromInput,
  toInput,
  durationInput,
  exportWrap,
  exportOpen,
  exportSelections,
  recentWrap,
  recentOpen,
  recentList,
  showFavoriteModal,
  showAudioModal,
  audioSrc,
  audioMetadata,
  records,
  totalItems,
  loading,
  sortColumn,
  sortDirection,
  columns,
  canExport,
  totalPages,
  startIndex,
  paginatedRecords,
  startItem,
  endItem,
  pagesToShow,
  selectedFiles,
  selectedCount,
  selectAllChecked,
  showShareModal,
  showFileShareNotification,
  downloading,
  downloadProgress,
  downloadSpeed,
  downloadRemaining,
  onTyping,
  clearSearchQuery,
  setPerPage,
  toggleRecent,
  applyRecent,
  applyRecentRange,
  applyLatestRecent,
  toggleExport,
  changePage,
  onSearch,
  onReset,
  applyFavorite,
  editFavorite,
  deleteFavorite,
  onExportFormat,
  confirmExport,
  cancelExport,
  onRowDblClick,
  onRowEdit,
  onRowDelete,
  onSortChange,
  toggleRowSelection,
  toggleSelectAll,
  onCreate,
  openShare
} = useHome()

function onFileShareClick() {
  filters.file_share = 'true'
  // hide notification badge when user opens File Share
  try {
    showFileShareNotification.value = false
  } catch (e) {
    // safe fallback if it's not a ref
    showFileShareNotification = false
  }
  onSearch()
}

</script>
<style scoped src="../assets/css/home.css"></style>
<style scoped>
#shareBtn { position: relative; }
.badge.badge-danger {
  position: absolute;
  top: -8px;
  right: -6px;
  width: 22px;
  height: 16px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  line-height: 1;
}
.form-check-input {
  width: 13px;
  height: 13px;

}

/* Export dropdown action buttons: make Cancel/Confirm expand to fill available width */
.export-actions {
  display: flex;
  gap: 6px;
}
.export-action-btn {
  flex: 1 1 auto;
  font-size: 8px;
}
</style>
