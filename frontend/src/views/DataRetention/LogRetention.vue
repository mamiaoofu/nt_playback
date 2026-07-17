<template>
  <MainLayout>
    <ModalDowload v-model="downloading" :progress="downloadProgress" :speed="downloadSpeed" :remaining="downloadRemaining" />
    <div class="main-wrapper container-fluid py-3">
      <div class="col-lg-12">
        <div class="card">
          <div class="card-body card-body-datatable">
            
            <!-- Header Row with Title and Search Input -->
            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 12px">
              <div class="d-flex align-items-center">
                <div class="d-flex align-items-center justify-content-center me-1"
                  style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                  <i class="fas fa-file-alt" style="color: #2b6cb0; font-size: 18px"></i>
                </div>
                <h5 class="card-title mb-2 mt-1">Retention Log</h5>
              </div>
              
              <div class="d-flex align-items-center">
                 <div style="width:260px;">
                    <SearchInput ref="searchInputRef" v-model="searchQuery" :placeholder="'Search...'"
                      @typing="onTyping" @clear="clearSearchQuery" />
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

            <!-- Filter Row -->
            <div style="margin-bottom: 12px;">
              <form id="filterForm" class="filter-row">

                <div class="input-group">
                  <CustomSelect class="select-search select-checkbox" v-model="filters.action" :options="actionOptions" placeholder="Select Action" name="action" />
                </div>

                <div :class="['input-group', { 'has-value': !!filters.running_date }]">
                  <input ref="runningDateInput" v-flatpickr="{ target: filters, key: 'running_date', noTime: true }" required type="text" name="running_date" autocomplete="off" class="input">
                  <label class="floating-label">Running Date</label>
                  <span class="calendar-icon" @click="runningDateInput && runningDateInput.focus()"><i class="fa-regular fa-calendar"></i></span>
                </div>

                <div :class="['input-group', { 'has-value': !!filters.from_date }]">
                  <input ref="startInput" v-flatpickr="{ target: filters, key: 'from_date' }" required type="text" name="from_date" autocomplete="off" class="input">
                  <label class="floating-label">From</label>
                  <span class="calendar-icon" @click="startInput && startInput.focus()"><i class="fa-regular fa-calendar"></i></span>
                </div>

                <div :class="['input-group', { 'has-value': !!filters.to_date }]">
                  <input ref="endInput" v-flatpickr="{ target: filters, key: 'to_date' }" required type="text" name="to_date" autocomplete="off" class="input">
                  <label class="floating-label">To</label>
                  <span class="calendar-icon" @click="endInput && endInput.focus()"><i class="fa-regular fa-calendar"></i></span>
                </div>

                <div class="input-group" style="flex: 0 0 auto;">
                  <button type="button" class="btn btn-light" id="resetFilterBtn" @click="resetFilters" style="height: 31px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 12px; margin-top: -7px;">
                    <i class="fas fa-undo"></i> Reset
                  </button>
                </div>

              </form>
            </div>

            <!-- Table Template -->
            <TableTemplate
              :columns="columns"
              :rows="paginatedLogs"
              :loading="loading"
              :total-items="totalItems"
              :per-page="perPage"
              :per-page-options="perPageOptions"
              :current-page="currentPage"
              :start-index="startIndex"
              :sort-column="sortColumn"
              :sort-direction="sortDirection"
              @page-change="handlePageChange"
              @per-change="handlePerPageChange"
              @sort-change="handleSortChange"
            >
              <template #cell-index="{ index }">
                {{ startIndex + index + 1 }}
              </template>
              <template #cell-retention_id="{ row }">
                {{ row.retention_id }}
              </template>
              <template #cell-action="{ row }">
                {{ row.action }}
              </template>
              <template #cell-retention_type="{ row }">
                {{ row.retention_type }}
              </template>
              <template #cell-retention_period="{ row }">
                {{ row.retention_period }}
              </template>
              <template #cell-times="{ row }">
                {{ row.times }}
              </template>
              <template #cell-index_count="{ row }">
                {{ row.index_count }}
              </template>
              <template #cell-running_date="{ row }">
                {{ row.running_date }}
              </template>
              <template #cell-created_by="{ row }">
                {{ row.created_by }}
              </template>
              <template #cell-description="{ row }">
                {{ row.description }}
              </template>
              <template #cell-ip_address="{ row }">
                {{ row.ip_address }}
              </template>
              <template #cell-timestamp="{ row }">
                {{ row.timestamp }}
              </template>
              <template #cell-client_type="{ row }">
                {{ row.client_type }}
              </template>
              <template #cell-audio_files="{ row }">
                <div class="group-card-actions">
                  <button v-if="row.download_url" 
                    type="button" class="group-send-btn" @click="downloadLog(row.download_url)">
                    <i class="fas fa-download" style="font-size: 12px;"></i>
                  </button>
                  <span v-else class="text-muted">No File</span>
                </div>
              </template>
            </TableTemplate>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import axios from 'axios';
import MainLayout from '../../layouts/MainLayout.vue';
import TableTemplate from '../../components/TableTemplate.vue';
import CustomSelect from '../../components/CustomSelect.vue';
import SearchInput from '../../components/SearchInput.vue';
import ModalDowload from '../../components/ModalDowload.vue';
import { useAuthStore } from '../../stores/auth.store';
import { showToast, exportTableToFormat, logUserAction } from '../../assets/js/function-all';

const API_BASE = '/api/v1/retention';
const logs = ref([]);
const loading = ref(false);
const totalItems = ref(0);

const searchQuery = ref('');
const currentPage = ref(1);
const perPage = ref(50);
const perPageOptions = [10, 25, 50, 100];
const sortColumn = ref('');
const sortDirection = ref('');

const filters = ref({
  action: [],
  running_date: '',
  from_date: '',
  to_date: ''
});

const runningDateInput = ref(null);
const startInput = ref(null);
const endInput = ref(null);
const searchInputRef = ref(null);

let searchTimeout = null;
let filterTimeout = null;

const onTyping = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    currentPage.value = 1;
    fetchLogs();
    searchTimeout = null;
  }, 450);
};

const clearSearchQuery = () => {
  searchQuery.value = '';
  currentPage.value = 1;
  fetchLogs();
  nextTick(() => {
    if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') {
      searchInputRef.value.focus();
    }
  });
};

watch(filters, () => {
  if (filterTimeout) clearTimeout(filterTimeout);
  filterTimeout = setTimeout(() => {
    currentPage.value = 1;
    fetchLogs();
    filterTimeout = null;
  }, 350);
}, { deep: true });

const actionOptions = [
  { label: 'All Actions', value: 'all' },
  { label: 'Auto Execution Schedule Retention', value: 'Auto Execution Schedule Retention' },
  { label: 'Change Retention Permanent Delete', value: 'Change Retention Permanent Delete' },
  { label: 'Complete Delete Immediately Retention', value: 'Complete Delete Immediately Retention' },
  { label: 'Complete Delete Schedule Retention', value: 'Complete Delete Schedule Retention' },
  { label: 'Complete Soft Delete Immediately Retention', value: 'Complete Soft Delete Immediately Retention' },
  { label: 'Complete Soft Delete Schedule Retention', value: 'Complete Soft Delete Schedule Retention' },
  { label: 'Restore Data Immediately Retention', value: 'Restore Data Immediately Retention' },
  { label: 'Restore Data Schedule Retention', value: 'Restore Data Schedule Retention' },
  { label: 'Run Schedule Retention', value: 'Run Schedule Retention' },
  { label: 'Save and Run Immediately Retention', value: 'Save and Run Immediately Retention' },
  { label: 'Save and Run Schedule Retention', value: 'Save and Run Schedule Retention' },
  { label: 'Stop Schedule Retention', value: 'Stop Schedule Retention' }
];

const authStore = useAuthStore();

const exportOpen = ref(false);
const exportWrap = ref(null);
const exportSelections = reactive({ pdf: false, excel: false, csv: false });

const downloading = ref(false);
const downloadProgress = ref(0);
const downloadSpeed = ref('0 MB/s');
const downloadRemaining = ref('');

const requiredExportPermission = computed(() => 'Save as Retention Log');
const canExport = computed(() => authStore.hasPermission(requiredExportPermission.value));

const toggleExport = () => {
  if (!canExport.value) return;
  exportOpen.value = !exportOpen.value;
};

const cancelExport = () => {
  exportSelections.pdf = false;
  exportSelections.excel = false;
  exportSelections.csv = false;
  exportOpen.value = false;
};

const confirmExport = async () => {
  const picks = [];
  if (exportSelections.pdf) picks.push('pdf');
  if (exportSelections.excel) picks.push('excel');
  if (exportSelections.csv) picks.push('csv');
  exportOpen.value = false;
  await onExportFormat(picks);
  exportSelections.pdf = false;
  exportSelections.excel = false;
  exportSelections.csv = false;
};

const onExportFormat = async (formatOrFormats) => {
  if (!canExport.value) return;
  let formats = [];
  if (typeof formatOrFormats === 'string') formats = [formatOrFormats];
  else if (Array.isArray(formatOrFormats)) formats = formatOrFormats;
  else formats = [];

  if (formats.length === 0) return;

  const rowsToExport = paginatedLogs.value || [];
  const exportColumns = columns.filter(c => c && c.key !== 'audio_files');
  const multipleOutput = formats.length > 1;

  const fmtTimestamp = (d) => {
    const yy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mi = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    return `${yy}${mm}${dd}${hh}${mi}${ss}`;
  };
  const timestampForName = fmtTimestamp(new Date());

  let startTime = 0;
  let totalBytes = 0;
  let completedTasks = 0;
  const totalTasks = formats.length || 1;

  const markTaskDone = (bytes) => {
    try {
      completedTasks += 1;
      if (bytes && typeof bytes === 'number') totalBytes += bytes;
      const pct = Math.round((completedTasks / totalTasks) * 100);
      downloadProgress.value = Math.min(100, pct);
      const elapsed = Math.max(0.001, (Date.now() - startTime) / 1000);
      const speed = totalBytes / elapsed;
      const mbps = speed / (1024 * 1024);
      if (isFinite(mbps)) downloadSpeed.value = `${mbps.toFixed(1)} MB/s`;
      const avgPerTask = elapsed / completedTasks;
      const remainSec = Math.max(0, Math.round(avgPerTask * (totalTasks - completedTasks)));
      const mm = String(Math.floor(remainSec / 60)).padStart(2, '0');
      const ss = String(remainSec % 60).padStart(2, '0');
      downloadRemaining.value = `${mm}:${ss} min.`;
    } catch (e) {
      console.warn('markTaskDone failed', e);
    }
  };

  const finishDownloading = (minDisplayMs = 3000) => {
    try {
      const elapsed = Math.max(0, Date.now() - startTime);
      const wait = Math.max(0, minDisplayMs - elapsed);
      setTimeout(() => {
        try {
          const pct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 100;
          downloadProgress.value = Math.min(100, Math.max(0, pct));
          downloadRemaining.value = '';
          downloadSpeed.value = downloadSpeed.value || '0.0 MB/s';
          downloading.value = false;
        } catch (e) { /* ignore */ }
      }, wait);
    } catch (e) {
      console.warn('finishDownloading failed', e);
    }
  };

  try {
    downloading.value = true;
    downloadProgress.value = 0;
    downloadSpeed.value = '0 MB/s';
    downloadRemaining.value = '';
    startTime = Date.now();

    if (multipleOutput) {
      try {
        try {
          await import('../../assets/js/jszip.min.js');
        } catch (e) { /* ignore */ }

        if (window.JSZip) {
          const zip = new window.JSZip();
          let anyFailed = false;
          for (const fmt of formats) {
            try {
              const res = await exportTableToFormat(fmt, 'Retention Log', {
                rows: rowsToExport || [],
                columns: exportColumns,
                startIndex: startIndex.value,
                fileNamePrefix: 'Retention Log',
                returnBlob: true
              });
              const fmtLabel = fmt === 'excel' ? 'Excel' : (fmt === 'csv' ? 'CSV' : 'PDF');
              if (res && res.blob) {
                const extMap = { excel: 'xls', csv: 'csv', pdf: 'pdf' };
                const ext = extMap[fmt] || fmt;
                const name = res.fileName || `Retention Log ${timestampForName}.${ext}`;
                zip.file(name, res.blob);
                try { markTaskDone(res.blob.size); } catch (e) {}

                logUserAction('Save as Retention Log', `File Name : ${name}, ${fmtLabel}`, 'success');
              } else {
                anyFailed = true;
                try { markTaskDone(); } catch (e) {}
                logUserAction('Save as Retention Log', `File Name : Retention Log ${timestampForName}, ${fmtLabel}, error=Failed to generate blob`, 'error');
              }
            } catch (e) {
              anyFailed = true;
              console.error('export into zip failed', e);
              try { markTaskDone(); } catch (er) {}
              const fmtLabel = fmt === 'excel' ? 'Excel' : (fmt === 'csv' ? 'CSV' : 'PDF');
              logUserAction('Save as Retention Log', `File Name : Retention Log ${timestampForName}, ${fmtLabel}, error=${e?.message || e}`, 'error');
            }
          }
          const zipBlob = await zip.generateAsync({ type: 'blob' });
          const zipName = `Retention Log ${timestampForName}.zip`;
          const a = document.createElement('a');
          a.href = URL.createObjectURL(zipBlob);
          a.download = zipName;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(a.href), 3000);
          if (anyFailed) try { showToast('Some exports failed while creating ZIP', 'warning'); } catch (e) {}
          finishDownloading();
          return;
        }
      } catch (e) {
        console.error('ZIP creation failed', e);
      }
    }

    for (const fmt of formats) {
      const fmtLabel = fmt === 'excel' ? 'Excel' : (fmt === 'csv' ? 'CSV' : 'PDF');
      try {
        const res = await exportTableToFormat(fmt, 'Retention Log', {
          rows: rowsToExport || [],
          columns: exportColumns,
          startIndex: startIndex.value,
          fileNamePrefix: 'Retention Log',
          returnBlob: true
        });
        if (res && res.blob) {
          try {
            const url = URL.createObjectURL(res.blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = res.fileName || `Retention Log ${timestampForName}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 3000);
          } catch (e) {
            console.warn('trigger blob download failed', e);
          }
          try { markTaskDone(res.blob.size); } catch (e) {}

          const filenameStr = res.fileName || `Retention Log ${timestampForName}`;
          logUserAction('Save as Retention Log', `File Name : ${filenameStr}, ${fmtLabel}`, 'success');
        } else {
          try { markTaskDone(); } catch (e) {}
          logUserAction('Save as Retention Log', `File Name : Retention Log ${timestampForName}, ${fmtLabel}, error=Failed to generate blob`, 'error');
        }
      } catch (e) {
        console.error('export failed', fmt, e);
        try { if (typeof showToast === 'function') showToast(`Export ${fmt} failed`, 'error'); } catch (er) {}
        logUserAction('Save as Retention Log', `File Name : Retention Log ${timestampForName}, ${fmtLabel}, error=${e?.message || e}`, 'error');
      }
    }

    finishDownloading();
  } catch (err) {
    console.error('onExportFormat error', err);
    try { if (typeof showToast === 'function') showToast('Export failed', 'error'); } catch (e) {}
  } finally {
    try { if (downloading.value) { finishDownloading(); } } catch (e) {}
  }
};

const onDocClick = (e) => {
  if (exportWrap.value && !exportWrap.value.contains(e.target)) exportOpen.value = false;
};

const resetFilters = () => {
  filters.value.action = [];
  filters.value.running_date = '';
  filters.value.from_date = '';
  filters.value.to_date = '';
  sortColumn.value = '';
  sortDirection.value = '';
  currentPage.value = 1;
  
  if (runningDateInput.value && runningDateInput.value._flatpickrInstance) {
    runningDateInput.value._flatpickrInstance.clear();
  }
  if (startInput.value && startInput.value._flatpickrInstance) {
    startInput.value._flatpickrInstance.clear();
  }
  if (endInput.value && endInput.value._flatpickrInstance) {
    endInput.value._flatpickrInstance.clear();
  }
  
  fetchLogs();
};

const columns = [
  { key: 'index', label: '#', isIndex: true, sortable: true },
  { key: 'retention_id', label: 'Retention ID' },
  { key: 'action', label: 'Action' },
  { key: 'retention_type', label: 'Retention Type' },
  { key: 'retention_period', label: 'Retention Period' },
  { key: 'times', label: 'Times' },
  { key: 'index_count', label: 'Index Count' },
  { key: 'running_date', label: 'Running Date' },
  { key: 'created_by', label: 'Created By' },
  { key: 'description', label: 'Description', tooltip: true },
  { key: 'ip_address', label: 'IP Address' },
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'client_type', label: 'Client Type' },
  { key: 'audio_files', label: 'Audio Files', sortable: false }
];

const fetchLogs = async () => {
  loading.value = true;
  try {
    const start = (currentPage.value - 1) * perPage.value;
    const params = new URLSearchParams();
    params.set('draw', '1');
    params.set('start', String(start));
    params.set('length', String(perPage.value));
    params.set('search[value]', searchQuery.value || '');

    if (sortColumn.value && sortDirection.value) {
      params.set('sort[0][field]', sortColumn.value);
      params.set('sort[0][dir]', sortDirection.value);
    }

    if (filters.value.action && filters.value.action.length > 0) {
      params.set('action', filters.value.action.join(','));
    }
    if (filters.value.running_date) {
      params.set('running_date', filters.value.running_date);
    }
    if (filters.value.from_date) {
      params.set('from_date', filters.value.from_date);
    }
    if (filters.value.to_date) {
      params.set('to_date', filters.value.to_date);
    }

    const res = await axios.get(`${API_BASE}/logs/?${params.toString()}`, { withCredentials: true });
    logs.value = res.data.data || [];
    totalItems.value = res.data.recordsFiltered ?? res.data.recordsTotal ?? logs.value.length;
  } catch (err) {
    console.error("Failed to fetch logs", err);
    showToast("Failed to fetch logs", "error");
  } finally {
    loading.value = false;
  }
};

const downloadLog = (downloadUrl) => {
  if (downloadUrl) {
    window.open(downloadUrl, '_blank');
  }
};

const filteredLogs = computed(() => logs.value);
const paginatedLogs = computed(() => logs.value);

const startIndex = computed(() => (currentPage.value - 1) * perPage.value);

const handlePageChange = (p) => {
  currentPage.value = p;
  fetchLogs();
};

const handlePerPageChange = (opt) => {
  perPage.value = opt;
  currentPage.value = 1;
  fetchLogs();
};

const handleSortChange = ({ column, direction }) => {
  sortColumn.value = column;
  sortDirection.value = direction;
  currentPage.value = 1;
  fetchLogs();
};

onMounted(() => {
  fetchLogs();
  document.addEventListener('click', onDocClick);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick);
});
</script>

<style scoped>
@import "../../assets/css/user-management.css";
@import "../../assets/css/user-log.css";

.text-muted { color: #94a3b8; font-size: 12px; }
:deep(.table-scroll td),
:deep(.table-scroll th) {
  height: 34px !important;
  vertical-align: middle !important;
  padding: 0px 8px !important;
  box-sizing: border-box;
}
</style>
