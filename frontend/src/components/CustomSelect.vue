<template>
  <div class="custom-select-root" :class="{ 'is-open': open, 'has-value': hasValue, 'up': up, 'up-internal': up }" ref="root">
    <button type="button" :class="['select-toggle', attrs.class]" @click="toggle" @keydown.down.prevent="openList"
      @keydown.up.prevent="openList" :aria-expanded="open" :aria-haspopup="true">
      <span class="selected-text">{{ hasValue ? selectedLabel : '' }}</span>
      <span class="chev" aria-hidden><i class="fa-solid fa-angle-down" style="font-size: 12px;"></i></span>
    </button>
    <label class="floating-label">{{ placeholder }}</label>

    <teleport to="body">
      <ul v-if="open" ref="menuRef" :class="['options', { up: up }]" :style="menuStyle" role="listbox">
        <li v-if="searchable" class="option option-search">
          <div class="search-input-wrap">
            <i class="fa-solid fa-magnifying-glass search-icon" aria-hidden="true"></i>
            <input ref="searchInputRef" v-model="searchTerm" class="form-control form-control-sm select-search-input"
              placeholder="Search..." />
            <i v-if="searchTerm" class="fa-solid fa-xmark fa-times clear-icon" aria-hidden="true" @click.stop="clearSearch"></i>
          </div>
        </li>
      <div class="options-inner">
        <li v-for="(opt, idx) in filteredOptions" :key="idx" :class="[ opt.isGroup ? 'option-group' : 'option', { selected: !opt.isGroup && isSelected(opt.value) } ]"
          @mouseenter="hoverIndex = idx" @mouseleave="hoverIndex = null" role="option">
          <template v-if="opt.isGroup">
            <div class="opt-group-label">{{ opt.label }}</div>
          </template>
          <template v-else>
            <div @click="onOptionClick(opt.value)" class="option-row">
              <template v-if="checkboxable">
                <input type="checkbox" :checked="isSelected(opt.value)" @click.stop @change="select(opt.value)" />
                <span class="opt-label">{{ opt.label }}</span>
              </template>
              <template v-else>
                <span class="opt-label">{{ opt.label }}</span>
              </template>
              <span class="opt-check" aria-hidden v-if="!checkboxable && opt.value === modelValue"><i class="fa-solid fa-check"></i></span>
            </div>
          </template>
        </li>
        <li v-if="filteredOptions.length === 0" class="option option-empty" role="option">
          <div class="option-row">
            <span class="opt-label no-options">No options found</span>
          </div>
        </li>
      </div>

      </ul>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch, useAttrs } from 'vue'
const props = defineProps({
  modelValue: { type: [String, Number, Array], default: '' },
  options: { type: Array, required: true },
  placeholder: { type: String, default: '' },
  alwaysHasValue: { type: Boolean, default: false },
  alwaysUp: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const attrs = useAttrs()
const open = ref(false)
const hoverIndex = ref(null)
const root = ref(null)
const up = ref(false)
const searchable = ref(false)
const checkboxable = ref(false)
const searchTerm = ref('')
const searchInputRef = ref(null)
const menuRef = ref(null)
const menuStyle = ref({})

// Normalize props.options into a flat list that may include group headers.
// Supported input shapes:
// - Simple list: [{ label, value }, ...] or ['a', 'b']
// - Grouped: [{ group: 'Base Roles', options: [...] }, { group: 'Custom Roles', options: [...] }]
const normalizedOptions = computed(() => {
  const out = []
  for (const o of props.options) {
    if (o && Array.isArray(o.options)) {
      out.push({ isGroup: true, label: o.group || '' })
      for (const item of o.options) {
        out.push(typeof item === 'string' ? { label: item, value: item } : item)
      }
    } else {
      out.push(typeof o === 'string' ? { label: o, value: o } : o)
    }
  }
  return out
})

const filteredOptions = computed(() => {
  const q = String(searchTerm.value || '').trim().toLowerCase()
  if (!searchable.value || !q) return normalizedOptions.value
  const items = normalizedOptions.value
  const res = []
  for (let i = 0; i < items.length; i++) {
    const it = items[i]
    if (it.isGroup) {
      // include group header only if at least one following non-group matches
      let found = false
      for (let j = i + 1; j < items.length && !items[j].isGroup; j++) {
        if (String(items[j].label).toLowerCase().includes(q)) { found = true; break }
      }
      if (found) res.push(it)
    } else {
      if (String(it.label).toLowerCase().includes(q)) res.push(it)
    }
  }
  return res
})

const selectedLabel = computed(() => {
  if (checkboxable.value && Array.isArray(props.modelValue)) {
    // Exclude any special 'all' option from the displayed labels/count
    const labels = normalizedOptions.value
      .filter(o => !o.isGroup && String(o.value).toLowerCase() !== 'all' && props.modelValue.includes(o.value))
      .map(o => o.label)
    const count = labels.length
    if (count === 0) return ''
    if (count === 1) return labels[0]
    return `${count} Selected`
  }
  const sel = normalizedOptions.value.find(o => o.value === props.modelValue)
  return sel ? sel.label : props.placeholder
})

function isSelected(v) {
  if (checkboxable.value) return Array.isArray(props.modelValue) && props.modelValue.indexOf(v) !== -1
  return v === props.modelValue
}

const hasValue = computed(() => {
  if (checkboxable.value && Array.isArray(props.modelValue)) {
    return props.modelValue.length > 0
  }
  return props.modelValue !== '' && props.modelValue !== null && props.modelValue !== undefined
})


function toggle() { open.value = !open.value }
function openList() { open.value = true }
function computeUp() {
  if (props.alwaysUp) { up.value = true; return } else if (props.alwaysUp === false) { up.value = false; return }
  if (!root.value) return
  const rect = root.value.getBoundingClientRect()
  // Use viewport space to decide. Prefer opening downward; only open up when below doesn't fit but above does.
  const viewportHeight = window.innerHeight
  const spaceBelow = viewportHeight - rect.bottom
  const spaceAbove = rect.top
  const estimatedMenuHeight = Math.min(400, normalizedOptions.value.length * 40 + 12)

  if (spaceBelow >= estimatedMenuHeight) {
    up.value = false
  } else if (spaceAbove >= estimatedMenuHeight) {
    up.value = true
  } else {
    // default to down; we'll clamp position later to keep it inside viewport
    up.value = false
  }
}

watch(open, async (val) => {
  if (val) {
    await nextTick()
    computeUp()
    await nextTick()
    // compute position after DOM rendered
    computePosition()
    window.addEventListener('resize', computePosition)
    window.addEventListener('scroll', computePosition, true)
  } else {
    up.value = false
    window.removeEventListener('resize', computePosition)
    window.removeEventListener('scroll', computePosition, true)
  }
})

async function computePosition() {
  if (!root.value) return
  const rect = root.value.getBoundingClientRect()
  const width = rect.width
  const left = rect.left + window.scrollX

  // initial top (prefer down), we'll correct after measuring actual menu height
  let top = rect.bottom + window.scrollY

  menuStyle.value = {
    position: 'absolute',
    top: `${top}px`,
    left: `${left}px`,
    width: `${width}px`,
    zIndex: 9999
  }

  await nextTick()
  const m = menuRef.value
  if (m) {
    const mrect = m.getBoundingClientRect()
    const menuHeight = mrect.height
    if (up.value) {
      top = rect.top + window.scrollY - menuHeight
    } else {
      top = rect.bottom + window.scrollY
    }

    // Clamp within viewport with small margin
    const viewportTop = window.scrollY
    const viewportBottom = window.scrollY + window.innerHeight
    if (top + menuHeight > viewportBottom - 8) {
      top = viewportBottom - menuHeight - 8
    }
    if (top < viewportTop + 8) {
      top = viewportTop + 8
    }

    // Also clamp left/right if needed
    let leftClamped = left
    const menuRight = leftClamped + mrect.width
    const viewportRight = window.scrollX + window.innerWidth
    if (menuRight > viewportRight - 8) {
      leftClamped = Math.max(8 + window.scrollX, viewportRight - mrect.width - 8)
    }

    menuStyle.value.top = `${top}px`
    menuStyle.value.left = `${leftClamped}px`
    menuStyle.value.width = `${Math.min(width, window.innerWidth - 16)}px`
  }
}
function select(v) {
  if (checkboxable.value) {
    const current = Array.isArray(props.modelValue) ? [...props.modelValue] : []
    const isAll = String(v).toLowerCase() === 'all'
    if (isAll) {
      // If 'All' was not selected, select every option; otherwise clear selection
      const allVals = normalizedOptions.value.map(o => o.value)
      const hasAllSelected = allVals.every(val => current.indexOf(val) !== -1)
      if (!hasAllSelected) {
        emit('update:modelValue', Array.from(new Set(allVals)))
      } else {
        emit('update:modelValue', [])
      }
    } else {
      const idx = current.indexOf(v)
      if (idx === -1) current.push(v)
      else current.splice(idx, 1)
      // remove 'all' keyword if present when selecting individual items
      const allIdx = current.findIndex(x => String(x).toLowerCase() === 'all')
      if (allIdx !== -1) current.splice(allIdx, 1)
      emit('update:modelValue', current)
    }
  } else {
    if (v === props.modelValue) emit('update:modelValue', '')
    else emit('update:modelValue', v)
    open.value = false
  }
}

function onOptionClick(v) {
  select(v)
}

function onDocClick(e) {
  const target = e.target
  if (root.value && root.value.contains(target)) return
  if (menuRef.value && menuRef.value.contains && menuRef.value.contains(target)) return
  open.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  if (root.value) {
    const cls = root.value.classList
    searchable.value = cls.contains('select-search')
    checkboxable.value = cls.contains('select-checkbox')
  }
})

function clearSearch() {
  searchTerm.value = ''
  nextTick(() => {
    if (searchInputRef.value && typeof searchInputRef.value.focus === 'function') searchInputRef.value.focus()
  })
}
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('resize', computePosition)
  window.removeEventListener('scroll', computePosition, true)
})
</script>

<style scoped>
.select-toggle.select-toggle-error {
  border: 1px solid rgb(245, 163, 163) !important;
  box-shadow: rgba(220, 53, 69, 0.25) 0px 0px 0px 0.2rem !important;
}

.input[type="checkbox" i] {
 cursor: pointer;
}
</style>
