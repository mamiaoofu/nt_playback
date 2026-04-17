<template>
  <div v-show="modelValue" class="audio-modal-backdrop">
    <div class="audio-modal">
      <div class="audio-card">
        <div class="card-header">
          <div class="header-title">
             <div class="d-flex align-items-center justify-content-center me-1" style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                  <i class="fa-solid fa-circle-play" style="color:#2b6cb0;font-size:18px"></i>
              </div>
              <h5 class="card-title mb-2 mt-1" style="font-size: 16px;">Audio Player</h5>
            </div>
          <button class="btn-icon-close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="audio-info-container">
          <div class="info-row">
            <div class="label">File Name:</div>
            <div class="value truncate" :title="metadata.fileName || shortName">{{ metadata.fileName || shortName }}
            </div>
          </div>
           <div class="info-row">
            <div class="label">Start Date & Time:</div>
            <div class="value">{{ metadata.from || '-' }}</div>
          </div>
           <div class="info-row">
            <div class="label">End Date & Time:</div>
            <div class="value">{{ metadata.to || '-' }}</div>
          </div>
          <div class="info-row">
            <div class="label">Duration:</div>
            <div class="value">{{ formatTime(currentDuration) }}</div>
          </div>
          <div class="info-row">
            <div class="label">Customer Number:</div>
            <div class="value">{{ metadata.customerNumber || '-' }}</div>
          </div>
          <div class="info-row">
            <div class="label">Extension:</div>
            <div class="value">{{ metadata.extension || '-' }}</div>
          </div>
          <div class="info-row">
            <div class="label">Agent:</div>
            <div class="value">{{ metadata.agent || '-' }}</div>
          </div>
          <div class="info-row">
            <div class="label">Call Direction:</div>
            <div class="value"><span class="badge-mint">{{ metadata.callDirection || 'Unknown' }}</span></div>
          </div>
        </div>

        <div class="wave-area-styled">
          <canvas ref="canvasRef" class="wave-canvas" @mousedown="onMouseDown"></canvas>
        </div>

        <div class="progress-section">
          <div class="progress-wrap-styled" @click="seekFromClick($event)">
            <div class="progress-bar-thick">
              <div class="progress-pos-thick"
                :style="{ width: (audioDuration ? (currentTime / audioDuration * 100) : 0) + '%' }"></div>
            </div>
          </div>
          <div class="time-labels">
            <div class="time-text">{{ formatTime(currentTime) }}</div>
            <div class="time-text">{{ formatTime(audioDuration) }}</div>
          </div>
        </div>

        <div class="control-section-styled">
          <div class="vol-controls">
            <i class="fa-solid fa-volume-high text-blue-500"></i>
            <div class="vol-stack">
              <input type="range" min="0" max="1" step="0.01" v-model.number="volume" class="vol-slider-styled" />
              <div class="vol-label-text">{{ Math.round(volume * 100) }}/100</div>
            </div>
          </div>
          <div class="main-controls">
            <button class="btn-skip" @click="rewind"><i class="fa-solid fa-backward text-gray-600"></i></button>
            <button class="btn-play-large" @click="togglePlay"><i :class="playing ? 'fa-solid fa-pause' : 'fa-solid fa-play'" /></button>
            <button class="btn-skip" @click="forward"><i class="fa-solid fa-forward text-gray-600"></i></button>
          </div>
          <div class="empty-space-right"></div>
        </div>

        <div class="footer-styled">
          <button v-if="showDownload" class="btn-blue-block" @click="downloadAudio">Download</button>
          <button class="btn-gray-block" @click="close">Close</button>
        </div>
      </div>

      <audio ref="audioRef" preload="metadata" crossorigin="use-credentials"></audio>
    </div>
    <ModalDowload v-model="showDownloadModal" :progress="downloadProgress" :speed="downloadSpeed" :remaining="downloadRemaining" />
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, toRefs } from 'vue'
import ModalDowload from './ModalDowload.vue'
import { useAuthStore } from '../stores/auth.store'

// --- Script ส่วนใหญ่ยังคงเดิม ---
const props = defineProps({ modelValue: Boolean, src: String, metadata: { type: Object, default: () => ({}) }, filters: { type: Object, default: () => ({}) } })
const { modelValue, src, metadata, filters } = toRefs(props)
const emit = defineEmits(['update:modelValue'])
const audioRef = ref(null)
const playing = ref(false)
const audioDuration = ref(0)
const canvasRef = ref(null)
let audioCtx = null
let animationId = null
const audioBuffer = ref(null)
const peaks = ref([])
const currentTime = ref(0)
const volume = ref(0.5)
const isDragging = ref(false)
let dragTimeout = null
const audioUrl = ref(null)

const authStore = useAuthStore()
const canDownload = computed(() => authStore.hasPermission('Download Voice File'))

const showDownload = computed(() => {
  const d = metadata.value && metadata.value.download
  const isTicket = !!(filters && filters.value && (filters.value.is_ticket === 'true' || filters.value.is_ticket === true))
  const isFileShare = !!(filters && filters.value && (filters.value.file_share === 'true' || filters.value.file_share === true))
  console.log('showDownload computed:', { d, isTicket, isFileShare, canDownload: canDownload.value })
  if (d === true) return true
  // if (isTicket === false && isFileShare === false) return canDownload
  
  return false
})

// Local download modal state
const showDownloadModal = ref(false)
const downloadProgress = ref(0)
const downloadSpeed = ref('0.0 MB/s')
const downloadRemaining = ref('00:00:00')

const finishDownloadModal = async (minMs = 3000, start = Date.now()) => {
  try {
    const elapsed = Math.max(0, Date.now() - start)
    const wait = Math.max(0, minMs - elapsed)
    await new Promise(res => setTimeout(res, wait))
    downloadProgress.value = Math.min(100, downloadProgress.value || 100)
    downloadRemaining.value = ''
    downloadSpeed.value = downloadSpeed.value || '0.0 MB/s'
    showDownloadModal.value = false
  } catch (e) { console.warn('finishDownloadModal failed', e) }
}

const shortName = computed(() => {
  if (!src.value) return ''
  try { return decodeURIComponent(src.value.split('/').pop()) } catch (e) { return src.value }
})

const currentDuration = computed(() => audioDuration.value || (metadata.value && metadata.value.duration) || 0)

function formatTime(t) {
  if (!t && t !== 0) return '00:00'
  const sec = Math.floor(t || 0)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

async function loadAudio() {
  if (!src.value) return
  audioBuffer.value = null
  peaks.value = []

  try {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      audioCtx = new AudioContext()
    }

    const response = await fetch(src.value, { credentials: 'include' })
    const blob = await response.blob()

    // สร้าง Blob URL สำหรับเล่นเสียง (แก้ปัญหา Seek ไม่ได้)
    if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = URL.createObjectURL(blob)
    if (audioRef.value) {
      audioRef.value.src = audioUrl.value
      audioRef.value.load()
      if (modelValue.value) {
        audioRef.value.volume = Math.max(0, Math.min(1, volume.value))
        audioRef.value.play().then(() => {
          playing.value = true
          requestAnimationFrame(draw)
        }).catch(() => {})
      }
    }

    const arrayBuffer = await blob.arrayBuffer()
    const decoded = await audioCtx.decodeAudioData(arrayBuffer)

    audioBuffer.value = decoded
    processPeaks(decoded)
    draw()
  } catch (e) {
    console.error("Failed to load audio waveform", e)
    // Fallback: ถ้าโหลด Blob ไม่ได้ ให้ลองใช้ src เดิม
    if (audioRef.value && src.value) audioRef.value.src = src.value
  }
}

function processPeaks(buffer) {
  console.log('Processing peaks for buffer with', buffer.numberOfChannels, 'channels and length', buffer.length)
  const width = 200 // ลดจำนวนลงเพื่อให้ได้กราฟแบบแท่งที่หนาขึ้น (Modern Bar Look)
  const result = []

  for (let c = 0; c < buffer.numberOfChannels; c++) {
    const data = buffer.getChannelData(c)
    const step = Math.ceil(data.length / width)
    const chanPeaks = []

    for (let i = 0; i < width; i++) {
      let min = 1.0
      let max = -1.0
      for (let j = 0; j < step; j++) {
        const idx = (i * step) + j
        if (idx < data.length) {
          const val = data[idx]
          if (val < min) min = val
          if (val > max) max = val
        }
      }
      if (min > max) { min = 0; max = 0 }
      chanPeaks.push({ min, max })
    }
    result.push(chanPeaks)
  }
  peaks.value = result
}

function draw() {
  console.log('Drawing waveform, peaks length:', peaks.value.length)
  if (!canvasRef.value) return
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')

  if (canvas.width !== canvas.offsetWidth || canvas.height !== canvas.offsetHeight) {
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight
  }
  const width = canvas.width
  const height = canvas.height
  ctx.clearRect(0, 0, width, height)

  if (!audioBuffer.value || peaks.value.length === 0) {
    ctx.fillStyle = "#9ca3af"
    ctx.font = "12px Arial"
    ctx.fillText("Loading...", 10, height / 2)
    return
  }

  const drawChannel = (channelIndex, colorStart, colorEnd, yBase, h) => {
    if (channelIndex >= peaks.value.length) return
    const chanPeaks = peaks.value[channelIndex]

    // คำนวณขนาดแท่งกราฟ
    const totalBars = chanPeaks.length
    const barSlotWidth = width / totalBars
    const gap = Math.max(1, barSlotWidth * 0.3) // เว้นช่องว่าง 30%
    const barWidth = Math.max(1, barSlotWidth - gap)

    // สร้าง Gradient ไล่สีแนวตั้ง
    const gradient = ctx.createLinearGradient(0, yBase, 0, yBase + h)
    gradient.addColorStop(0, colorStart)
    gradient.addColorStop(1, colorEnd)
    ctx.fillStyle = gradient

    for (let i = 0; i < totalBars; i++) {
      const { min, max } = chanPeaks[i]
      let magnitude = max - min
      if (magnitude < 0.01) magnitude = 0.01 // ให้มีขีดเล็กๆ แม้ช่วงเงียบ

      const barHeight = magnitude * (h / 2) * 0.9
      const x = i * barSlotWidth + (gap / 2)
      const y = yBase + (h / 2) - (barHeight / 2)

      // วาดแท่งกราฟแบบมน (Rounded Rect)
      ctx.beginPath()
      if (ctx.roundRect) {
        ctx.roundRect(x, y, barWidth, barHeight, 4)
      } else {
        ctx.rect(x, y, barWidth, barHeight)
      }
      ctx.fill()
    }
  }

  // Labels & Drawing Logic
  ctx.font = "bold 11px 'Segoe UI', sans-serif"

  if (peaks.value.length > 1) {
    // กรณี Stereo (Dual Channel): แยก Agent บน / Customer ล่าง
    drawChannel(1, '#60a5fa', '#2563eb', 0, height / 2)      // Agent: ฟ้าอ่อน -> ฟ้าเข้ม
    ctx.fillStyle = "#2563eb"
    ctx.fillText("Agent", 8, 16)

    drawChannel(0, '#34d399', '#059669', height / 2, height / 2) // Customer: เขียวอ่อน -> เขียวเข้ม
    ctx.fillStyle = "#059669"
    ctx.fillText("Customer", 8, (height / 2) + 16)

    // เส้นแบ่งครึ่งบางๆ
    ctx.beginPath()
    ctx.strokeStyle = 'rgba(0,0,0,0.05)'
    ctx.moveTo(0, height / 2)
    ctx.lineTo(width, height / 2)
    ctx.stroke()
  } else {
    // กรณี Mono: วาดรวมเต็มพื้นที่
    drawChannel(0, '#60a5fa', '#2563eb', 0, height)
    ctx.fillStyle = "#2563eb"
    ctx.fillText("Mono", 8, 16)
  }

  // Cursor
  const curTime = (playing.value && audioRef.value) ? audioRef.value.currentTime : currentTime.value
  const duration = audioBuffer.value.duration
  if (duration > 0) {
    const progress = curTime / duration
    const x = progress * width

    // Highlight ช่วงที่เล่นไปแล้ว
    ctx.fillStyle = 'rgba(37, 99, 235, 0.05)'
    ctx.fillRect(0, 0, x, height)

    // เส้น Cursor สีแดง
    ctx.beginPath()
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 2
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }

  if (playing.value) animationId = requestAnimationFrame(draw)
}

function onMouseDown(e) {
  console.log('onMouseDown called with', e)
  if (dragTimeout) { clearTimeout(dragTimeout); dragTimeout = null }
  if (!audioBuffer.value) return
  isDragging.value = true

  const targetTime = handleSeek(e)

  const a = audioRef.value
  if (a && targetTime !== undefined) {
    if (a.paused) {
      a.play().catch(() => { })
      playing.value = true
      requestAnimationFrame(draw)
    }
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e) {
  console.log('onMouseMove called with', e)
  if (isDragging.value) {
    handleSeek(e)
  }
}

function onMouseUp() {
  console.log('onMouseUp called')
  if (isDragging.value) {
    dragTimeout = setTimeout(() => { isDragging.value = false }, 200)
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }
}

function handleSeek(e) {
  console.log('handleSeek called with', e)
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = e.clientX - rect.left
  const width = rect.width
  if (width <= 0) return

  const pct = Math.max(0, Math.min(1, x / width))
  const duration = (audioBuffer.value && audioBuffer.value.duration) || audioDuration.value || (audioRef.value && audioRef.value.duration) || 0
  if (!duration || !isFinite(duration)) return

  const newTime = pct * duration
  const a = audioRef.value
  if (a) {
    a.currentTime = newTime
  }
  currentTime.value = newTime
  return newTime
}

function togglePlay() {
  console.log('togglePlay called')
  const a = audioRef.value
  if (!a) return
  if (a.paused) {
    a.play().catch(() => { });
    playing.value = true;
    requestAnimationFrame(draw)
  }
  else {
    a.pause();
    playing.value = false
    if (animationId) cancelAnimationFrame(animationId)
    draw()
  }
}

function seekFromClick(e) {
  console.log('seekFromClick called with', e)
  try {
    if (dragTimeout) { clearTimeout(dragTimeout); dragTimeout = null }
    const wrap = e.currentTarget
    const rect = wrap.getBoundingClientRect()
    const x = e.clientX - rect.left
    const pct = Math.max(0, Math.min(1, x / rect.width))
    isDragging.value = true
    if (audioDuration.value && audioDuration.value > 0) {
      const newTime = pct * audioDuration.value
      currentTime.value = newTime
      const a = audioRef.value
      if (a) {
        a.currentTime = newTime
        if (a.paused) { a.play().catch(() => { }); playing.value = true; requestAnimationFrame(draw) }
      }
    }
    dragTimeout = setTimeout(() => { isDragging.value = false }, 200)
  } catch (er) { console.warn('seekFromClick failed', er) }
}

function rewind() { const a = audioRef.value; if (!a) return; a.currentTime = Math.max(0, a.currentTime - 10) }
function forward() { const a = audioRef.value; if (!a) return; a.currentTime = Math.min((a.duration || 0), a.currentTime + 10) }

function close() { emit('update:modelValue', false); try { const a = audioRef.value; if (a) { a.pause(); a.currentTime = 0; playing.value = false; } } catch (e) { } }

async function downloadAudio() {
  if (!src.value) return
  showDownloadModal.value = true
  downloadProgress.value = 0
  downloadSpeed.value = '0.0 MB/s'
  downloadRemaining.value = ''
  const startTime = Date.now()

  try {
    const resp = await fetch(src.value, { credentials: 'include' })
    if (!resp.ok) throw new Error('Download failed: ' + resp.status)

    const contentLength = resp.headers.get('content-length')
    const totalBytes = contentLength ? parseInt(contentLength, 10) : null

    if (!resp.body || !resp.body.getReader) {
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = metadata.value.fileName || shortName.value || 'audio'
      document.body.appendChild(a)
      a.click()
      try {
        const lf = encodeURIComponent(metadata.value.fileName || shortName.value || 'audio')
        fetch(`/api/log/download/?file=${lf}`, { credentials: 'include' }).catch(() => {})
      } catch (e) { console.warn('log download error', e) }
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 3000)
      downloadProgress.value = 100
      downloadSpeed.value = '0.0 MB/s'
      await finishDownloadModal(3000, startTime)
      return
    }

    const reader = resp.body.getReader()
    const chunks = []
    let received = 0
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(value)
      received += (value && value.length) || (value && value.byteLength) || 0

      if (totalBytes) {
        const pct = Math.round((received / totalBytes) * 100)
        downloadProgress.value = Math.min(99, pct)
      } else {
        downloadProgress.value = Math.min(98, downloadProgress.value + 1)
      }

      const elapsedSec = Math.max(0.001, (Date.now() - startTime) / 1000)
      const speed = received / elapsedSec
      const mbps = speed / (1024 * 1024)
      if (isFinite(mbps)) downloadSpeed.value = `${mbps.toFixed(1)} MB/s`

      if (totalBytes && received > 0) {
        const remainSec = Math.max(0, Math.round((totalBytes - received) / (received / elapsedSec)))
        const mm = String(Math.floor(remainSec / 60)).padStart(2, '0')
        const ss = String(remainSec % 60).padStart(2, '0')
        downloadRemaining.value = `${mm}:${ss} min.`
      } else {
        downloadRemaining.value = ''
      }
    }

    const blob = new Blob(chunks)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = metadata.value.fileName || shortName.value || 'audio'
    document.body.appendChild(a)
    a.click()
    try {
      const lf = encodeURIComponent(metadata.value.fileName || shortName.value || 'audio')
      fetch(`/api/log/download/?file=${lf}`, { credentials: 'include' }).catch(() => {})
    } catch (e) { console.warn('log download error', e) }
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 3000)

    downloadProgress.value = 100
    await finishDownloadModal(3000, startTime)
  } catch (e) {
    console.error('downloadAudio error', e)
    showDownloadModal.value = false
  }
}

onMounted(() => {
  const a = audioRef.value
  if (!a) return
  const onLoaded = () => { audioDuration.value = a.duration || 0 }
  const onTime = () => { if (!isDragging.value) currentTime.value = a.currentTime }
  const onEnd = () => { playing.value = false; currentTime.value = 0; }
  a.addEventListener('loadedmetadata', onLoaded)
  a.addEventListener('timeupdate', onTime)
  a.addEventListener('ended', onEnd)
  if (src.value) loadAudio()
  onBeforeUnmount(() => {
    if (animationId) cancelAnimationFrame(animationId)
    if (audioCtx) audioCtx.close()
    a.removeEventListener('loadedmetadata', onLoaded)
    a.removeEventListener('timeupdate', onTime)
    a.removeEventListener('ended', onEnd)
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
    if (dragTimeout) clearTimeout(dragTimeout)
  })
})

watch(volume, (v) => {
  const a = audioRef.value
  if (!a) return
  a.volume = Math.max(0, Math.min(1, v))
})

// Auto-play when the modal is opened (useful for double-click from table)
watch(modelValue, (v) => {
  const a = audioRef.value
  if (!a) return
  if (v) {
    // ensure volume applied
    a.volume = Math.max(0, Math.min(1, volume.value))
    const tryPlay = () => {
      a.play().then(() => { playing.value = true; requestAnimationFrame(draw) }).catch(() => { })
    }
    if (a.readyState >= 2) tryPlay()
    else {
      a.addEventListener('canplay', tryPlay, { once: true })
      setTimeout(tryPlay, 300)
    }
  } else {
    try { a.pause(); playing.value = false } catch (e) { }
  }
})

watch(() => src.value, (n) => {
  const a = audioRef.value
  if (!a) return
  playing.value = false
  currentTime.value = 0
  audioDuration.value = 0
  if (n) {
    loadAudio()
    // ลบการกำหนด a.src = n ตรงนี้ออก เพราะเราให้ loadAudio จัดการผ่าน Blob แล้ว
  }
})

watch(currentTime, () => {
  if (!playing.value) requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
})
</script>

<style scoped>
/* Utility Classes (Tailwind-like) */
.text-blue-600 {
  color: #2563eb;
}

.text-blue-500 {
  color: #3b82f6;
}

.text-gray-600 {
  color: #4b5563;
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.audio-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  padding: 20px;
}

.audio-modal {
  width: 30%;
  max-width: 600px;
}

/* ลดความกว้างลงให้ดูเหมือน Card */

/* Card Styling ใหม่ */
.audio-card {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
}

/* Header ใหม่ใน Card */
.card-header {
  padding: 20px 24px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
}

.header-title i {
  font-size: 1.5rem;
}

.btn-icon-close {
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 4px;
}

.btn-icon-close:hover {
  color: #4b5563;
}

/* Info Container สีเทา */
.audio-info-container {
  padding: 20px 24px;
  background: #f9fafb;
  border-radius: 12px;
  margin: 0 24px 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
}

.info-row .label {
  color: #6b7280;
  font-weight: 500;
}

.info-row .value {
  font-weight: 600;
  color: #374151;
  text-align: right;
  max-width: 60%;
}

/* Badge สีเขียวมิ้นต์ */
.badge-mint {
  background: #d1fae5;
  color: #065f46;
  padding: 4px 12px;
  border-radius: 999px;
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
}

/* Waveform แบบแท่งจำลอง */
.wave-area-styled {
  padding: 10px 24px 0;
}

.wave-canvas {
  width: 100%;
  height: 120px;
  display: block;
  cursor: pointer;
  background-color: #deefff;
  border-radius: 12px;
  padding: 6px;
  border: 1px solid #f3f4f6;
}

/* Progress Bar หนาๆ */
.progress-section {
  padding: 10px 24px 16px;
}

.progress-wrap-styled {
  height: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.progress-bar-thick {
  height: 10px;
  width: 100%;
  background: #e5e7eb;
  border-radius: 999px;
  position: relative;
  overflow: hidden
}

.progress-pos-thick {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: #3b82f6;
  border-radius: 999px;
  transition: width 0.1s linear;
}

.time-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}

.time-text {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

/* Controls Layout ใหม่ */
.control-section-styled {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px 32px;
}

.vol-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.vol-slider-styled {
  height: 8px;
  accent-color: #3b82f6;
}

.vol-label-text {
  font-size: 10px;
  color: #6b7280;
  font-weight: 500;
  width: 30px;
}

/* Stack slider and label vertically and center */
.vol-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.vol-stack .vol-slider-styled {
  width: 60px;
  margin-top: 14px;
}

.vol-stack .vol-label-text {
  width: auto;
  text-align: center;
}

.main-controls {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  z-index: 1;
}

.btn-skip {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #f3f4f6;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-skip:hover {
  background: #e5e7eb;
}

.btn-play-large {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #3b82f6;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.5);
  transition: background 0.2s, transform 0.1s;
}

.btn-play-large:hover {
  background: #2563eb;
}

.btn-play-large:active {
  transform: scale(0.95);
}

.empty-space-right {
  flex: 1;
}

/* ดันให้ปุ่ม play อยู่ตรงกลาง */

/* Footer ปุ่มใหญ่เต็ม */
.footer-styled {
  display: flex;
  gap: 16px;
  padding: 0 24px 24px;
}

.btn-blue-block {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 10px;
  background: #3b82f6;
  color: #fff;
  border-radius: 12px;
  text-decoration: none;
  font-weight: 600;
  transition: background 0.2s;
  border: none;
  cursor: pointer;
  font-size: 12px;
  box-sizing: border-box;
}

.btn-blue-block:hover {
  background: #2563eb;
}

.btn-gray-block {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #374151;
  border: none;
  height: 36px;
  padding: 10px;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 12px;
  box-sizing: border-box;
}

.btn-gray-block:hover {
  background: #e5e7eb;
}

/* Make footer buttons share equal width and fill the footer */
.footer-styled > .btn-blue-block,
.footer-styled > .btn-gray-block {
  flex: 1 1 0;
  min-width: 0;
}

.fa-play {
  margin-left: 2px;
}
</style>