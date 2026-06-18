<template>
  <MainLayout>
    <div class="main-wrapper container-fluid py-3">
      <div class="col-lg-12">
        <div class="card">
          <div class="card-body card-body-datatable">
            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
              <div class="d-flex align-items-center">
                <div class="d-flex align-items-center justify-content-center me-1"
                  style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                  <i class="fas fa-file-alt" style="color: #2b6cb0; font-size: 18px"></i>
                </div>
                <h5 class="card-title mb-2 mt-1">Log Retention</h5>
              </div>
            </div>

            <TableTemplate
              :columns="columns"
              :rows="logs"
              :loading="loading"
              :total-items="logs.length"
              :per-page="10"
              :current-page="1"
            >
              <template #cell-id="{ row }">
                {{ row.id }}
              </template>
              <template #cell-task_type="{ row }">
                {{ row.task_type === 'MANUAL' ? 'Auto-Loop' : row.task_type === 'AUTO_EXECUTION' ? 'One time' : row.task_type }}
              </template>
              <template #cell-status="{ row }">
                <span class="role-badge" :class="row.status.toLowerCase()">
                  {{ row.status }}
                </span>
              </template>
              <template #cell-created_at="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
              <template #cell-action="{ row }">
                <div class="group-card-actions">
                  <button v-if="row.file_log_path" 
                    type="button" class="group-send-btn" @click="downloadLog(row.id)">
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
import { ref, onMounted } from 'vue';
import axios from 'axios';
import MainLayout from '../../layouts/MainLayout.vue';
import TableTemplate from '../../components/TableTemplate.vue';
import { showToast } from '../../assets/js/function-all';

const API_BASE = '/api/v1/retention';
const logs = ref([]);
const loading = ref(false);

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  const pad = (num) => String(num).padStart(2, '0');
  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const date = pad(d.getDate());
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  return `${year}-${month}-${date} ${hours}:${minutes}`;
};

const columns = [
  { key: 'id', label: 'Log ID' },
  { key: 'task_type', label: 'Type' },
  { key: 'delete_option', label: 'Delete Option' },
  { key: 'index_count', label: 'Index Count' },
  { key: 'time_period', label: 'Time Period' },
  { key: 'user_create', label: 'User' },
  { key: 'status', label: 'Status' },
  { key: 'created_at', label: 'Date Created' },
  { key: 'action', label: 'Action', sortable: false }
];

const fetchLogs = async () => {
  loading.value = true;
  try {
    const res = await axios.get(`${API_BASE}/logs/`);
    logs.value = res.data;
  } catch (err) {
    console.error("Failed to fetch logs", err);
    showToast("Failed to fetch logs", "error");
  } finally {
    loading.value = false;
  }
};

const downloadLog = (logId) => {
  window.open(`${API_BASE}/logs/${logId}/download/`, '_blank');
};

onMounted(() => {
  fetchLogs();
});
</script>

<style scoped src="../../assets/css/user-management.css"></style>
<style scoped>
.role-badge.success { background: #dcfce7; color: #166534; }
.role-badge.failed { background: #fee2e2; color: #991b1b; }
.text-muted { color: #94a3b8; font-size: 12px; }
</style>
