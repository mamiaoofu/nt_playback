<template>
  <div v-if="modelValue" class="md-overlay" @click.self="close">
    <div class="md-card">
      <div class="md-icon-wrap">
        <i class="fa-solid fa-download"></i>
      </div>

      <div class="md-circle-wrap">
        <svg viewBox="0 0 120 120" class="md-circle">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          <circle cx="60" cy="60" r="44" class="md-ring-bg"/>
          <circle cx="60" cy="60" r="44" class="md-ring" :stroke-dasharray="dashString" :stroke-dashoffset="dashOffset" filter="url(#glow)"/>
          <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" class="md-percent">{{ progress }}%</text>
        </svg>
      </div>

      <div class="md-status">
        <div class="md-downloading"> 
          <span class="md-wave-text">DOWNLOADING...</span>
        </div>
        <div class="md-meta">
          <div>Speed: <strong>{{ speed || '0.0 MB/s' }}</strong></div>
          <div>Remaining: <strong>{{ remaining || '00:00:00' }}</strong></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  speed: { type: String, default: '0.0 MB/s' },
  remaining: { type: String, default: '00:00:00' }
})
const emit = defineEmits(['update:modelValue'])

const close = () => emit('update:modelValue', false)

const circumference = 2 * Math.PI * 44
const dash = computed(() => {
  const pct = Math.min(100, Math.max(0, Number(props.progress || 0)))
  return (pct / 100) * circumference
})
const dashString = computed(() => `${dash.value} ${Math.max(0, circumference - dash.value)}`)
const dashOffset = computed(() => Math.max(0, circumference - dash.value))
</script>

<style scoped>
.md-overlay {
  position: fixed; inset: 0; display:flex; align-items:center; justify-content:center; background: rgba(0,0,0,0.45); z-index: 2000;
}
.md-card { background: #0b1220; color: #fff; padding: 22px; width: 360px; border-radius: 12px; text-align:center; box-shadow: 0 8px 30px rgba(3,10,30,0.6); }
.md-icon-wrap { font-size: 28px; color: #4fd1ff; margin-bottom: 8px; }
.md-download-icon { background: rgba(79,209,255,0.06); padding: 10px; border-radius: 8px; }
.md-circle-wrap { width: 140px; height: 140px; margin: 8px auto; }
.md-circle { width: 100%; height: 100%; }
.md-ring-bg { fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 12; }
.md-ring { fill: none; stroke: #4fd1ff; stroke-width: 8; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 60px 60px; transition: stroke-dasharray 300ms linear; filter: drop-shadow(0 0 8px rgba(79,209,255,0.6)); }
.md-percent { font-size: 20px; fill: #ffffff; font-weight: 700; }
.md-status { margin-top: 6px; }
.md-downloading { margin-top: 6px; }
.md-wave-text { display:inline-block; font-weight:700; letter-spacing:1px; color:#cfefff; position:relative; overflow:hidden; }
.md-wave-text::before { content: ''; position:absolute; left:-100%; top:0; height:100%; width:100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent); animation: shimmer 1.6s linear infinite; }
@keyframes shimmer { 0% { left:-100% } 100% { left:100% } }
.md-meta { display:flex; justify-content:space-between; margin-top:10px; font-size:13px; color:#d7f7ff; }
</style>
