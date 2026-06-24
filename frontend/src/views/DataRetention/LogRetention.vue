<template>
  <MainLayout>
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
              </div>
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
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import MainLayout from '../../layouts/MainLayout.vue';
import TableTemplate from '../../components/TableTemplate.vue';
import { showToast } from '../../assets/js/function-all';

const API_BASE = '/api/v1/retention';
const logs = ref([]);
const loading = ref(false);

const searchQuery = ref('');
const currentPage = ref(1);
const perPage = ref(50);
const perPageOptions = [10, 25, 50, 100];
const sortColumn = ref('');
const sortDirection = ref('');

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
});
</script>

<style scoped src="../../assets/css/user-management.css"></style>
<style scoped>
.text-muted { color: #94a3b8; font-size: 12px; }
:deep(.table-scroll td),
:deep(.table-scroll th) {
  height: 34px !important;
  vertical-align: middle !important;
  padding: 0px 8px !important;
  box-sizing: border-box;
}
</style>
