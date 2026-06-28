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
                 <div style="width:260px; position: relative;">
                    <input type="text" v-model="searchQuery" class="form-control" placeholder="Search..." 
                           style="border-radius: 20px; padding: 6px 36px 6px 16px; font-size: 13px; height: 34px; border: 1.5px solid #d1d5db;" />
                    <i class="fas fa-search" style="position: absolute; right: 14px; top: 10px; color: #94a3b8;"></i>
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
                  <input ref="runningDateInput" v-flatpickr="{ target: filters, key: 'running_date' }" required type="text" name="running_date" autocomplete="off" class="input">
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
              :total-items="filteredLogs.length"
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
              <template #cell-no="{ index }">
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
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';
import MainLayout from '../../layouts/MainLayout.vue';
import TableTemplate from '../../components/TableTemplate.vue';
import CustomSelect from '../../components/CustomSelect.vue';
import ModalDowload from '../../components/ModalDowload.vue';
import { useAuthStore } from '../../stores/auth.store';
import { showToast, exportTableToFormat, logUserAction } from '../../assets/js/function-all';

const API_BASE = '/api/v1/retention';
const logs = ref([]);
const loading = ref(false);

const searchQuery = ref('');
const currentPage = ref(1);
const perPage = ref(50);
const perPageOptions = [10, 25, 50, 100];
const sortColumn = ref('');
const sortDirection = ref('');

const filters = ref({
  action: '',
  running_date: '',
  from_date: '',
  to_date: ''
});

const runningDateInput = ref(null);
const startInput = ref(null);
const endInput = ref(null);

const actionOptions = computed(() => {
  const actions = new Set(logs.value.map(log => log.action).filter(Boolean));
  return Array.from(actions).map(action => ({
    label: action,
    value: action
  }));
});

const authStore = useAuthStore();

const exportOpen = ref(false);
const exportWrap = ref(null);
const exportSelections = reactive({ pdf: false, excel: false, csv: false });

const downloading = ref(false);
const downloadProgress = ref(0);
const downloadSpeed = ref('0 MB/s');
const downloadRemaining = ref('');

const requiredExportPermission = computed(() => 'Save As Retention Log');
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

  const rowsToExport = filteredLogs.value || [];
  const exportColumns = columns.filter(c => c && c.key !== 'no' && c.key !== 'audio_files');
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
                startIndex: 0,
                fileNamePrefix: 'Retention Log',
                returnBlob: true
              });
              if (res && res.blob) {
                const extMap = { excel: 'xls', csv: 'csv', pdf: 'pdf' };
                const ext = extMap[fmt] || fmt;
                const name = res.fileName || `Retention Log ${timestampForName}.${ext}`;
                zip.file(name, res.blob);
                try { markTaskDone(res.blob.size); } catch (e) {}

                const fmtLabel = fmt === 'excel' ? 'Excel' : (fmt === 'csv' ? 'CSV' : 'PDF');
                logUserAction('Save As Retention Log', `File Name : ${name}, ${fmtLabel}`, 'success');
              } else {
                anyFailed = true;
                try { markTaskDone(); } catch (e) {}
              }
            } catch (e) {
              anyFailed = true;
              console.error('export into zip failed', e);
              try { markTaskDone(); } catch (er) {}
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
      try {
        const res = await exportTableToFormat(fmt, 'Retention Log', {
          rows: rowsToExport || [],
          columns: exportColumns,
          startIndex: 0,
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

          const fmtLabel = fmt === 'excel' ? 'Excel' : (fmt === 'csv' ? 'CSV' : 'PDF');
          const filenameStr = res.fileName || `Retention Log ${timestampForName}`;
          logUserAction('Save As Retention Log', `File Name : ${filenameStr}, ${fmtLabel}`, 'success');
        } else {
          try { markTaskDone(); } catch (e) {}
        }
      } catch (e) {
        console.error('export failed', fmt, e);
        try { if (typeof showToast === 'function') showToast(`Export ${fmt} failed`, 'error'); } catch (er) {}
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
  filters.value.action = '';
  filters.value.running_date = '';
  filters.value.from_date = '';
  filters.value.to_date = '';
  currentPage.value = 1;
};

const columns = [
  { key: 'no', label: 'No.', sortable: false },
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
    const res = await axios.get(`${API_BASE}/logs/`, { withCredentials: true });
    logs.value = res.data;
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

// Client-side search & sort & pagination
const filteredLogs = computed(() => {
  let result = [...logs.value];
  
  if (filters.value.action) {
    result = result.filter(item => item.action === filters.value.action);
  }
  
  if (filters.value.running_date) {
    result = result.filter(item => item.running_date && item.running_date.startsWith(filters.value.running_date));
  }
  
  if (filters.value.from_date) {
    result = result.filter(item => {
      const dates = item.retention_period ? item.retention_period.match(/\d{4}-\d{2}-\d{2}/g) : null;
      if (dates && dates.length > 0) {
        return dates[0] >= filters.value.from_date;
      }
      return false;
    });
  }
  
  if (filters.value.to_date) {
    result = result.filter(item => {
      const dates = item.retention_period ? item.retention_period.match(/\d{4}-\d{2}-\d{2}/g) : null;
      if (dates && dates.length > 0) {
        const itemEnd = dates.length > 1 ? dates[1] : dates[0];
        return itemEnd <= filters.value.to_date;
      }
      return false;
    });
  }
  
  if (searchQuery.value) {
    const query = searchQuery.value.trim().toLowerCase();
    result = result.filter(item => {
      return (
        String(item.retention_id).toLowerCase().includes(query) ||
        String(item.action).toLowerCase().includes(query) ||
        String(item.retention_type).toLowerCase().includes(query) ||
        String(item.retention_period).toLowerCase().includes(query) ||
        String(item.times).toLowerCase().includes(query) ||
        String(item.index_count).toLowerCase().includes(query) ||
        String(item.running_date).toLowerCase().includes(query) ||
        String(item.created_by).toLowerCase().includes(query) ||
        String(item.description).toLowerCase().includes(query) ||
        String(item.ip_address).toLowerCase().includes(query) ||
        String(item.timestamp).toLowerCase().includes(query) ||
        String(item.client_type).toLowerCase().includes(query)
      );
    });
  }
  
  if (sortColumn.value && sortDirection.value) {
    const col = sortColumn.value;
    const isDesc = sortDirection.value === 'desc';
    result.sort((a, b) => {
      let valA = a[col] ?? '';
      let valB = b[col] ?? '';
      
      // numeric check for index_count
      if (col === 'index_count') {
        const numA = Number(valA) || 0;
        const numB = Number(valB) || 0;
        return isDesc ? numB - numA : numA - numB;
      }
      
      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();
      
      if (valA < valB) return isDesc ? 1 : -1;
      if (valA > valB) return isDesc ? -1 : 1;
      return 0;
    });
  }
  
  return result;
});

const paginatedLogs = computed(() => {
  const start = (currentPage.value - 1) * perPage.value;
  return filteredLogs.value.slice(start, start + perPage.value);
});

const startIndex = computed(() => (currentPage.value - 1) * perPage.value);

const handlePageChange = (p) => {
  currentPage.value = p;
};

const handlePerPageChange = (opt) => {
  perPage.value = opt;
  currentPage.value = 1;
};

const handleSortChange = ({ column, direction }) => {
  sortColumn.value = column;
  sortDirection.value = direction;
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
