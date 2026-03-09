<template>
  <div class="table-container">
    <div class="table-responsive table-scroll" ref="tableScroll">
      <table class="table table-sm table-striped">
        <thead class="table-primary">
          <tr>
            <th v-for="col in filteredColumns" :key="col.key" :style="colWidthStyle(col)" 
                @click="col.sortable !== false ? onSort(col.key) : null" 
                :class="{ 'cursor-pointer': col.sortable !== false }">
              <div class="d-flex justify-content-between align-items-center">
                <slot :name="`header-${col.key}`" :column="col">
                  <span>{{ col.label }}</span>
                </slot>
                <i v-if="col.sortable !== false" class="fa-solid" :class="getSortIcon(col.key)" style="margin-left: 5px; opacity: 0.5;font-size: 9px;"></i>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="((!rows || rows.length === 0) && !loading)">
            <td :colspan="filteredColumns.length" style="--bs-table-bg-type: #fff;border-bottom-width: 0px;">
              <div class="empty-state">
                <i class="fa-solid fa-dove"></i>
                <p>No matching records found.</p>
              </div>
            </td>
          </tr>
          <tr v-else v-for="(r, idx) in rows" :key="r.id ?? idx" @dblclick.stop="$emit('row-dblclick', r)" @click="onRowClick(idx, r)" :class="{ 'selected-row': props.showSelection && selectedIndex === idx }">
            <td v-for="col in filteredColumns" :key="col.key" :style="colWidthStyle(col)">
              <slot :name="`cell-${col.key}`" :row="r" :index="idx">
                <template v-if="col.isIndex">{{ startIndex + idx + 1 }}</template>
                <template v-else-if="col.tooltip">
                  <div class="file-name-cell" :class="{ 'is-active': tooltipIndex === idx }"
                    @mouseenter="onTooltipEnter($event, idx, r[col.key])" @mouseleave="onTooltipLeave">
                    <span class="truncated">{{ col.labelKey ? (r[col.labelKey] || '') : truncate(r[col.key], 50) }}</span>
                  </div>
                </template>
                <template v-else-if="callDirectionKey && col.key === callDirectionKey">
                  <span :class="['badge', callDirectionClass(r[col.key])]">{{ r[col.key] }}</span>
                </template>
                <template v-else-if="col.isAction">
                  <div class="group-card-actions">
                    <button
                      :id="`click-to-edit-${getActionId(r) ?? r.id ?? idx}`"
                      class="group-edit-btn"
                      @click.stop="$emit('edit', r, getActionId(r))">
                      Click to edit
                    </button>
                    <button
                      :id="`group-delete-btn-${getActionId(r) ?? r.id ?? idx}`"
                      type="button"
                      class="group-delete-btn"
                      @click.stop="$emit('delete', r, getActionId(r))">
                      <i class="fas fa-trash" style="font-size: 12px;"></i>
                    </button>
                    <button
                      v-if="store.hasPermission('Reset password')"
                      :id="`group-reset-btn-${getActionId(r) ?? r.id ?? idx}`"
                      type="button"
                      class="group-reset-btn"
                      @click.stop="$emit('reset', r, getActionId(r))">
                      <i class="fa-solid fa-key" style="font-size: 12px;"></i>
                    </button>
                  </div>
                </template>
                <template v-else-if="col.key === 'status'">
                  <template v-if="r[col.key] === true || String(r[col.key]).toLowerCase() === 'true'">
                    <span class="badge badge-success">Active</span>
                  </template>
                  <template v-else-if="r[col.key] === false || String(r[col.key]).toLowerCase() === 'false'">
                    <span class="badge badge-danger">Expired</span>
                  </template>
                  <template v-else>
                    {{ r[col.key] }}
                  </template>
                </template>
                <template v-else>{{ r[col.key] }}</template>
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="loading" class="table-overlay">
      <div class="overlay-box">Processing...</div>
    </div>
  </div>

  <teleport to="body">
    <div v-if="tooltipIndex !== null" ref="tooltipEl"
      :class="['file-name-tooltip tooltip show', tooltipPlacement === 'top' ? 'tooltip-top' : 'tooltip-bottom']"
      :style="tooltipStyle" @mouseenter="cancelHide" @mouseleave="onTooltipLeave" @mousedown.stop @mouseup.stop
      @click.stop>
      <div class="tooltip-arrow"></div>
          <div class="tooltip-inner d-flex align-items-center">
            <div class="file-content me-2">
              <div v-if="tooltipHeader" class="file-name-header">{{ tooltipHeader }}</div>
              <div class="file-full">{{ tooltipBody }}</div>
            </div>
            <button class="btn btn-sm btn-outline-secondary btn-copy" @click="copyFileName(tooltipText, tooltipIndex)"
              :aria-label="copiedIndex === tooltipIndex ? 'Copied' : 'Copy'">
              <i :class="copiedIndex === tooltipIndex ? 'fa-solid fa-check' : 'fa-regular fa-copy'"></i>
            </button>
          </div>
    </div>
  </teleport>
  <div class="d-flex justify-content-between align-items-center mt-2 pagination-div">
    <div>
      <div class="show-entries">
        Show
        <div class="custom-select-wrap" ref="perWrap" :class="{ up: perDropdownUp, open: perDropdownOpen }">
          <button type="button" class="custom-select-toggle" @click="togglePerDropdown">
            <span class="selected">{{ formatNumber(props.perPage) }}</span>
            <i class="fa-solid fa-caret-down "></i>
          </button>
          <ul v-if="perDropdownOpen" class="custom-select-menu" @click="perDropdownOpen = false">
            <li v-for="opt in props.perPageOptions" :key="opt" :class="{ active: opt === props.perPage }"
              @click="setPerPage(opt)">{{ formatNumber(opt) }}</li>
          </ul>
        </div>
        entries per page, Showing {{ formatNumber(startItem) }} to {{ formatNumber(endItem) }} of {{ formatNumber(props.totalItems) }} entries
      </div>
    </div>
    <nav>
      <ul class="pagination pagination-sm mb-0">
        <li class="page-item" :class="{ disabled: props.currentPage === 1 }"><button class="page-link"
            @click="changePage(props.currentPage - 1)">Previous</button></li>
        <li class="page-item" v-for="p in pagesToShow" :key="String(p)"
          :class="[{ active: p === props.currentPage }, { disabled: p === '...' }]">
          <button v-if="p !== '...'" class="page-link" @click="changePage(p)">{{ formatNumber(p) }}</button>
          <span v-else class="page-link">…</span>
        </li>
        <li class="page-item" :class="{ disabled: props.currentPage === totalPages }"><button class="page-link"
            @click="changePage(props.currentPage + 1)">Next</button></li>
      </ul>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  startIndex: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  callDirectionKey: { type: String, default: '' },
  // whether to visually highlight the selected row (use from pages that need it)
  showSelection: { type: Boolean, default: false },
  // optional key (supports dot-path) to derive an action id from a row
  actionIdKey: { type: String, default: '' },
  // pagination-related props (UI-only)
  perPage: { type: Number, default: 50 },
  perPageOptions: { type: Array, default: () => [50, 100, 500, 1000] },
  currentPage: { type: Number, default: 1 },
  totalItems: { type: Number, default: 0 },
  sortColumn: { type: String, default: '' },
  sortDirection: { type: String, default: '' }
})

const filteredColumns = computed(() => {
  return props.columns.filter(col => col.key !== 'selection' || props.showSelection)
})

const emit = defineEmits(['edit', 'delete', 'reset', 'page-change', 'per-change', 'row-dblclick', 'row-click', 'sort-change'])

// Pinia auth store instance (used for permission checks in template)
const store = useAuthStore()

const activeTooltip = ref(null)
// selected row index for visual highlight
const selectedIndex = ref(null)

function onRowClick(idx, row) {
  try {
    selectedIndex.value = idx
    emit('row-click', row)
  } catch (e) { console.warn('onRowClick error', e) }
}
const tooltipIndex = ref(null)
const tooltipText = ref('')
const tooltipRect = ref(null)
const tooltipStyle = ref(null)
const tooltipEl = ref(null)
const tooltipPlacement = ref('top')
let hideTimer = null
const copiedIndex = ref(null)

const tooltipHeader = computed(() => {
  const text = tooltipText.value || ''
  if (!text) return ''
  const parts = String(text).split(/\r?\n/)
  const first = parts[0] || ''
  const lower = first.toLowerCase()
  if (parts.length > 1 && (lower.startsWith('file name') || lower.startsWith('email'))) return first
  return ''
})

const tooltipBody = computed(() => {
  const text = tooltipText.value || ''
  if (!text) return ''
  const parts = String(text).split(/\r?\n/)
  const first = parts[0] || ''
  const lower = first.toLowerCase()
  if (parts.length > 1 && (lower.startsWith('file name') || lower.startsWith('email'))) return parts.slice(1).join('\n')
  return text
})

// per-page dropdown state (local UI)
const perWrap = ref(null)
const perDropdownOpen = ref(false)
const perDropdownUp = ref(false)
// ref to the scrollable table container so we can reset scroll when changing pages
const tableScroll = ref(null)

const togglePerDropdown = () => {
  perDropdownOpen.value = !perDropdownOpen.value
  if (perDropdownOpen.value) {
    const wrap = perWrap.value
    if (wrap) {
      const rect = wrap.getBoundingClientRect()
      const spaceBelow = window.innerHeight - rect.bottom
      const estimatedMenuHeight = Math.min(300, props.perPageOptions.length * 40 + 12)
      perDropdownUp.value = spaceBelow < estimatedMenuHeight
    } else {
      perDropdownUp.value = false
    }
  }
}

const onDocClick = (e) => { if (perWrap.value && !perWrap.value.contains(e.target)) perDropdownOpen.value = false }

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

const totalPages = computed(() => Math.max(1, Math.ceil(props.totalItems / props.perPage)))
const startIndexLocal = computed(() => (props.currentPage - 1) * props.perPage)
const paginatedRecords = computed(() => props.rows)
const startItem = computed(() => props.totalItems === 0 ? 0 : startIndexLocal.value + 1)
const endItem = computed(() => Math.min(props.totalItems, startIndexLocal.value + (props.rows.length || 0)))

const pagesToShow = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = props.currentPage

  // show all when small
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
    return pages
  }

  // beginning range: 1..5, ..., total
  if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
    return pages
  }

  // ending range: 1, ..., total-4 .. total
  if (current >= total - 3) {
    pages.push(1)
    pages.push('...')
    for (let i = total - 4; i <= total; i++) pages.push(i)
    return pages
  }

  // middle: 1, ..., current-1, current, current+1, ..., total
  pages.push(1)
  pages.push('...')
  pages.push(current - 1)
  pages.push(current)
  pages.push(current + 1)
  pages.push('...')
  pages.push(total)
  return pages
})

const changePage = (p) => {
  if (p < 1) p = 1
  if (p > totalPages.value) p = totalPages.value
  emit('page-change', p)
  // scroll the table container to top after page change
  nextTick(() => { try { if (tableScroll.value) tableScroll.value.scrollTop = 0 } catch (e) { /* ignore */ } })
}

const setPerPage = (opt) => {
  emit('per-change', opt)
  // ensure we reset to first page and request fresh data from parent
  emit('page-change', 1)
  perDropdownOpen.value = false
}

function truncate(s, max) {
  if (!s) return ''
  const str = String(s)
  if (str.length <= max) return str
  return str.slice(0, max - 3) + '...'
}

async function copyFileName(text, idx) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copiedIndex.value = idx
    setTimeout(() => { if (copiedIndex.value === idx) copiedIndex.value = null }, 1400)
  } catch (e) {
    console.error('copy failed', e)
  }
}

function onTooltipEnter(e, idx, text) {
  if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
  tooltipIndex.value = idx
  tooltipText.value = text
  tooltipRect.value = e.currentTarget.getBoundingClientRect()
  // render then adjust position
  nextTick(() => {
    try {
      const el = tooltipEl.value
      if (!el) return
      const tRect = el.getBoundingClientRect()
      const spaceAbove = tooltipRect.value.top
      const spaceBelow = window.innerHeight - tooltipRect.value.bottom
      const left = tooltipRect.value.left + (tooltipRect.value.width / 2)
      let top
      let transform
      if (spaceAbove > tRect.height + 8) {
        // place above
        top = tooltipRect.value.top - 8
        transform = 'translate(-50%, -100%)'
        tooltipPlacement.value = 'top'
      } else {
        // place below
        top = tooltipRect.value.bottom + 8
        transform = 'translate(-50%, 0)'
        tooltipPlacement.value = 'bottom'
      }
      tooltipStyle.value = { position: 'fixed', left: `${left}px`, top: `${top}px`, transform, zIndex: 9999, maxWidth: '760px', whiteSpace: 'normal' }
    } catch (err) {
      console.error('tooltip position error', err)
    }
  })
}

function onTooltipLeave() {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { tooltipIndex.value = null; tooltipText.value = ''; tooltipStyle.value = null }, 120)
}

function cancelHide() { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null } }

const callDirectionClass = (dir) => {
  if (!dir) return 'bg-secondary'
  const key = String(dir).toLowerCase()
  if (key === 'internal') return 'badge-warning'
  if (key === 'inbound') return 'badge-success'
  if (key === 'outbound') return 'badge-primary'
  return 'bg-secondary'
}

function colWidthStyle(col) {
  if (!col || col.width === undefined || col.width === null) return null
  const w = col.width
  return { width: typeof w === 'number' ? `${w}px` : String(w) }
}

function getByPath(obj, path) {
  if (!path) return undefined
  const parts = String(path).split('.')
  let cur = obj
  for (const p of parts) {
    if (cur == null) return undefined
    cur = cur[p]
  }
  return cur
}

function getActionId(row) {
  if (!props.actionIdKey) return undefined
  try {
    return getByPath(row, props.actionIdKey)
  } catch (e) {
    return undefined
  }
}

function formatNumber(v) {
  if (v === null || v === undefined) return v
  // avoid formatting non-numeric placeholders
  if (v === '...') return v
  const str = String(v).replace(/,/g, '')
  const n = Number(str)
  if (Number.isNaN(n)) return v
  return n.toLocaleString('en-US')
}

const onSort = (key) => {
  let dir = 'asc'
  if (props.sortColumn === key) {
    dir = props.sortDirection === 'asc' ? 'desc' : 'asc'
  }
  emit('sort-change', { column: key, direction: dir })
}

const getSortIcon = (key) => {
  if (props.sortColumn !== key) return 'fa-sort'
  return props.sortDirection === 'asc' ? 'fa-sort-up' : 'fa-sort-down'
}
</script>

<style scoped>
.table-container {
  position: relative;
}

/* make the table body scrollable while keeping the header visible */
.table-scroll {
  max-height: 60vh;
  overflow: auto;
}

/* sticky header */
.table-scroll thead th {
  position: sticky;
  top: 0;
  z-index: 6;
  background: var(--bs-table-bg, #fff);
}
.file-name-cell {
  position: relative;
  display: inline-block;
  font-size: 10px;
  cursor: pointer;
}

.truncated {
  display: inline-block;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.file-name-cell .tooltip {
  font-size: 10px;
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translate(-50%, -6px);
  z-index: 1050;
  display: inline-block;
  border-radius: 6px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}

.file-name-cell .tooltip .tooltip-inner {
  display: inline-block;
  max-width: 560px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #fff;
  background: rgba(0, 0, 0, 0.85);
  padding: 6px 8px;
  border-radius: 6px;
}

.file-name-cell .tooltip .file-full {
  display: inline-block;
  max-width: 460px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #fff;
  user-select: text
}

.file-name-cell .btn-copy {
  font-size: 10px;
  padding: 2px 6px;
  margin-left: 8px
}

.file-name-cell .tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  border-width: 6px;
  border-style: solid;
  border-color: rgba(0, 0, 0, 0.85) transparent transparent transparent;
}

.file-name-cell .tooltip.tooltip-down {
  bottom: auto;
  border-width: 8px;
  top: 100%;
  transform: translate(-50%, 5px);
}

.file-name-cell .tooltip.tooltip-down::after {
  top: -11.5px;
  border-color: transparent transparent rgba(0, 0, 0, 0.85);
}

.file-name-cell.is-active .truncated {
  background: rgba(0, 0, 0, 0.04);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06);
  border-radius: 3px;
}


.table-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
}

.overlay-box {
  padding: 12px 18px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 6px
}

/* Floating tooltip (teleported to body) */
.file-name-tooltip {
  position: fixed;
  display: inline-block;
  z-index: 9999;
  pointer-events: auto;
}

  .file-name-tooltip .tooltip-inner {
  max-width: 760px;
  /* Preserve newlines and allow wrapping */
  white-space: pre-wrap;
  overflow: visible;
  text-overflow: clip;
  color: #fff;
  font-size: 10px;
  background: rgba(0, 0, 0, 0.85);
  padding: 6px 8px;
  border-radius: 6px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
  /* Ensure text is left-aligned and breaks nicely */
  text-align: left;
  word-break: break-word;
}

.file-name-tooltip .file-full {
  display: block;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
  max-width: 720px;
}

.file-name-tooltip .file-name-header {
  font-weight: 700;
  margin-bottom: 5px;
  text-align: left;
  font-size: 12px;
}

.file-name-tooltip .tooltip-arrow {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0
}

.file-name-tooltip.tooltip-top .tooltip-arrow {
  bottom: -5px;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid rgba(0, 0, 0, 0.85);
}

.table-container table tr.selected-row td {
  background-color: #49ABFF !important;
  color: #fff !important;
}

.file-name-tooltip.tooltip-bottom .tooltip-arrow {
  top: -5px;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid rgba(0, 0, 0, 0.85);
}

.cursor-pointer {
  cursor: pointer;
}
</style>
