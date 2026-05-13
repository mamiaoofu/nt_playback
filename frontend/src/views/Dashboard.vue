<template>
  <MainLayout>
    <div class="dashboard-root py-3" style="background-color: #f1f5f9; min-height: calc(100vh - 60px);">
      <div class="dashboard-container">
        <Breadcrumbs :items="[{ text: 'Dashboard', to: '/dashboard' }]" />

        <!-- Summary Cards -->
        <div class="summary-cards row g-3 mb-4">
          
          <!-- Users Card -->
          <div class="col-md-3">
            <div class="card h-100 shadow-sm border-0" style="border-radius: 12px;">
              <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <div class="d-flex align-items-center">
                    <div class="d-flex align-items-center justify-content-center me-1 icon-style">
                      <i class="fa-solid fa-users" style="color:#2b6cb0;font-size:18px"></i>
                    </div>
                    <h5 class="card-title mb-2 mt-1">Total Users</h5>
                  </div>
                  <div style="width: 140px;">
                    <CustomSelect 
                      v-model="selectedRole" 
                      :options="roleOptions" 
                      placeholder="All Roles" 
                      @update:modelValue="fetchStats"
                    />
                  </div>
                </div>
                <div style="font-size: 32px; font-weight: 700; color: #0f172a;">{{ stats.user_display_count || 0 }}</div>
              </div>
            </div>
          </div>

          <!-- Audio Plays Card -->
          <div class="col-md-3">
            <div class="card h-100 shadow-sm border-0" style="border-radius: 12px;">
              <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <div class="d-flex align-items-center">
                    <div class="d-flex align-items-center justify-content-center me-1 icon-style">
                      <i class="fa-solid fa-play-circle" style="color:#2b6cb0;font-size:18px"></i>
                    </div>
                    <h5 class="card-title mb-2 mt-1">Audio Plays</h5>
                  </div>
                  <div class="d-flex gap-1">
                    <div style="width: 100px;">
                      <CustomSelect 
                        v-model="audioPlaysDays" 
                        :options="dayOptions" 
                        placeholder="Days" 
                        @update:modelValue="fetchStats"
                      />
                    </div>
                    <div style="width: 100px;">
                      <CustomSelect 
                        v-model="audioPlaysStatus" 
                        :options="statusOptions" 
                        placeholder="Status" 
                        @update:modelValue="fetchStats"
                      />
                    </div>
                  </div>
                </div>
                <div style="font-size: 32px; font-weight: 700; color: #0f172a;">{{ stats.total_plays || 0 }}</div>
              </div>
            </div>
          </div>

          <!-- Disk Info Card -->
          <div class="col-md-3">
            <div class="card h-100 shadow-sm border-0" style="border-radius: 12px;">
              <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <div class="d-flex align-items-center">
                    <div class="d-flex align-items-center justify-content-center me-1 icon-style">
                      <i class="fa-solid fa-hard-drive" style="color:#2b6cb0;font-size:18px"></i>
                    </div>
                    <h5 class="card-title mb-2 mt-1">Disk Info</h5>
                  </div>
                </div>
                <div style="font-size: 14px; color: #334155; line-height: 1.6;">
                  <div><strong>Driver:</strong> {{ stats.disk_info?.driver }}</div>
                  <div><strong>Total:</strong> {{ stats.disk_info?.total }}</div>
                  <div><strong>Used:</strong> {{ stats.disk_info?.used }}</div>
                  <div><strong>Free:</strong> <span class="text-success fw-bold">{{ stats.disk_info?.free }}</span></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Licenses Card -->
          <div class="col-md-3">
            <div class="card h-100 shadow-sm border-0" style="border-radius: 12px;">
              <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <div class="d-flex align-items-center">
                    <div class="d-flex align-items-center justify-content-center me-1 icon-style">
                      <i class="fa-solid fa-id-badge" style="color:#2b6cb0;font-size:18px"></i>
                    </div>
                    <h5 class="card-title mb-2 mt-1">Licenses</h5>
                  </div>
                </div>
                <div v-if="licenseStore.loaded" style="font-size: 14px; color: #334155; line-height: 1.6;">
                  <div><strong>Expiry:</strong> {{ formatDate(licenseStore.expiryDate) }}</div>
                     <div v-if="licenseStore.maxMainDb"><strong>Max Main DB:</strong> {{ licenseStore.maxMainDb }}</div>
                     <div v-if="licenseStore.maxConcurrentUsers"><strong>Max Concurrent Users:</strong> {{ licenseStore.maxConcurrentUsers }}</div>
                     <div v-for="m in licenseStore.allowedMenus" :key="m"><strong>Allowed Menu:</strong> {{ m }}</div>
                </div>  
                <div v-else style="font-size: 14px; color: #94a3b8;">No license information available</div>
              </div>
            </div>
          </div>

        </div>

        <!-- Charts -->
        <div class="row g-3 mb-4">
          <div class="col-md-6">
            <div class="card shadow-sm border-0 p-4" style="border-radius: 12px;">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h3 class="card-title m-0" style="font-size: 16px; color: #64748b;">CPU Usage</h3>
                <span class="badge bg-primary" style="font-size: 16px; font-weight: 700; color: #fff;">{{ stats.cpu_percent || 0 }}%</span>
              </div>
              <div style="height: 250px;">
                <Line v-if="chartReady" :data="cpuChartData" :options="chartOptions" />
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="card shadow-sm border-0 p-4" style="border-radius: 12px;">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h3 class="card-title m-0" style="font-size: 16px; color: #64748b;">Memory Usage</h3>
                <span class="badge bg-success" style="font-size: 16px; font-weight: 700; color: #fff;">{{ stats.memory_percent || 0 }}%</span>
              </div>
              <div style="height: 250px;">
                <Line v-if="chartReady" :data="memChartData" :options="chartOptions" />
              </div>
            </div>
          </div>
        </div>

        <!-- Alarms Table -->
        <div class="card shadow-sm border-0 p-4" style="border-radius: 12px;">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="d-flex align-items-center">
              <div class="d-flex align-items-center justify-content-center me-1 icon-style">
                <i class="fa-solid fa-triangle-exclamation" style="color:#2b6cb0;font-size:18px"></i>
              </div>
              <h5 class="card-title mb-2 mt-1">Security Alarms</h5>
            </div>
            <button class="btn btn-sm btn-outline-primary" @click="fetchAlarms">
              <i class="fa-solid fa-arrows-rotate me-1"></i> Refresh
            </button>
          </div>
          
          <TableTemplate 
            :columns="alarmColumns" 
            :rows="alarms" 
            :loading="loadingAlarms"
            :totalItems="alarms.length"
            :perPage="100"
          >
            <template #cell-event="{ row }">
              <span class="fw-bold text-danger">{{ row.event }}</span>
            </template>
            <template #cell-ip_address="{ row }">
              <code class="text-primary">{{ row.ip_address }}</code>
            </template>
            <template #cell-actions="{ row }">
              <div class="d-flex gap-2 justify-content-end">
                <button v-if="row.user_id" class="btn btn-sm btn-warning py-1 px-2 d-flex align-items-center gap-1" @click="kickOut(row.user_id)">
                  <i class="fa-solid fa-right-from-bracket"></i> Kick
                </button>
                <button v-if="row.ip_address && row.ip_address !== '-'" class="btn btn-sm btn-danger py-1 px-2 d-flex align-items-center gap-1" @click="blockIp(row.ip_address)">
                  <i class="fa-solid fa-ban"></i> Block
                </button>
              </div>
            </template>
          </TableTemplate>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted, onUnmounted } from 'vue'
import { useLicenseStore } from '../stores/license.store'
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import CustomSelect from '../components/CustomSelect.vue'
import TableTemplate from '../components/TableTemplate.vue'
import { API_DASHBOARD_STATS, API_DASHBOARD_ALARMS, API_DASHBOARD_ACTION } from '../api/paths'
import axios from 'axios'
import { getCsrfToken } from '../api/csrf'
import { showToast } from '../assets/js/function-all'

// Chart.js imports
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const stats = shallowRef({})
const licenseStore = useLicenseStore()
const alarms = ref([])
const loadingAlarms = ref(false)
const selectedRole = ref('all')
const audioPlaysDays = ref('all')
const audioPlaysStatus = ref('success')
const chartReady = ref(true)

const roleOptions = computed(() => {
  const roles = stats.value.users_by_role ? Object.keys(stats.value.users_by_role) : []
  return [{ label: 'All Roles', value: 'all' }, ...roles.map(r => ({ label: r, value: r }))]
})

const dayOptions = [
  { label: 'All Time', value: 'all' },
  { label: 'Today', value: '1' },
  { label: 'Last 7 Days', value: '7' },
  { label: 'Last 30 Days', value: '30' }
]

const statusOptions = [
  { label: 'All Status', value: 'all' },
  { label: 'Success', value: 'success' },
  { label: 'Error', value: 'error' }
]

const alarmColumns = [
  { key: 'time', label: 'Time', width: 170 },
  { key: 'event', label: 'Event', width: 140 },
  { key: 'message', label: 'Message' },
  { key: 'ip_address', label: 'IP Address', width: 130 },
  { key: 'actions', label: 'Actions', width: 160, sortable: false }
]

// History data for charts
const maxPoints = 20
const cpuHistory = ref(Array(maxPoints).fill(0))
const memHistory = ref(Array(maxPoints).fill(0))
const timeLabels = ref(Array(maxPoints).fill(''))

let pollInterval = null

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  scales: { y: { beginAtZero: true, max: 100 } },
  plugins: { legend: { display: false } }
}

const cpuChartData = computed(() => ({
  labels: [...timeLabels.value],
  datasets: [
    {
      label: 'CPU Usage %',
      backgroundColor: 'rgba(59, 130, 246, 0.2)',
      borderColor: '#3b82f6',
      borderWidth: 2,
      data: [...cpuHistory.value],
      fill: true,
      tension: 0.4,
      pointRadius: 0
    }
  ]
}))

const memChartData = computed(() => ({
  labels: [...timeLabels.value],
  datasets: [
    {
      label: 'Memory Usage %',
      backgroundColor: 'rgba(16, 185, 129, 0.2)',
      borderColor: '#10b981',
      borderWidth: 2,
      data: [...memHistory.value],
      fill: true,
      tension: 0.4,
      pointRadius: 0
    }
  ]
}))

async function fetchStats() {
  try {
    const params = {
      role: selectedRole.value,
      play_audio_days: audioPlaysDays.value,
      play_audio_status: audioPlaysStatus.value
    }
    const res = await axios.get(API_DASHBOARD_STATS(), { params, withCredentials: true })
    stats.value = res.data
    
    // Update charts
    const now = new Date()
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
    
    cpuHistory.value.push(res.data.cpu_percent || 0)
    cpuHistory.value.shift()
    
    memHistory.value.push(res.data.memory_percent || 0)
    memHistory.value.shift()

    timeLabels.value.push(timeStr)
    timeLabels.value.shift()
    
  } catch (err) {
    console.error('Fetch stats error:', err)
  }
}

async function fetchAlarms() {
  loadingAlarms.value = true
  try {
    const res = await axios.get(API_DASHBOARD_ALARMS(), { withCredentials: true })
    alarms.value = res.data.alarms || []
  } catch (err) {
    console.error('Fetch alarms error:', err)
  } finally {
    loadingAlarms.value = false
  }
}

async function kickOut(userId) {
  if (!confirm('Are you sure you want to kick out this user? They will be forced to log in again.')) return
  try {
    const res = await axios.post(API_DASHBOARD_ACTION(), {
      action: 'kick_out',
      user_id: userId
    }, {
      headers: { 'X-CSRFToken': getCsrfToken() },
      withCredentials: true
    })
    showToast(res.data.message || 'Action successful', 'success')
  } catch (err) {
    showToast(err.response?.data?.message || 'Error executing action', 'error')
  }
}

async function blockIp(ip) {
  if (!confirm(`Are you sure you want to block IP ${ip}? They will not be able to access the system.`)) return
  try {
    const res = await axios.post(API_DASHBOARD_ACTION(), {
      action: 'block_ip',
      ip_address: ip
    }, {
      headers: { 'X-CSRFToken': getCsrfToken() },
      withCredentials: true
    })
    showToast(res.data.message || 'IP Blocked successfully', 'success')
  } catch (err) {
    showToast(err.response?.data?.message || 'Error executing action', 'error')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  try {
    const d = new Date(dateStr)
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd} ${hh}:${min}`
  } catch {
    return dateStr
  }
}

onMounted(() => {
  fetchStats()
  fetchAlarms()
  licenseStore.fetchLicenseInfo()
  pollInterval = setInterval(() => {
    fetchStats()
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.dashboard-root {
  display: block !important;
  width: 100%;
}
.dashboard-container {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
  display: block !important;
}
.dashboard-root :deep(.custom-select-root .select-toggle) {
  font-size: 12px;
  padding: 4px 8px;
  background-color: #fff;
  border: 1px solid #cbd5e1;
  min-height: 32px;
}
.dashboard-root :deep(.floating-label) {
  display: none; /* Hide floating label to keep it clean in cards */
}

.layout-wrapper {
  position: absolute;
}
.icon-style {
  width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;
}
</style>
