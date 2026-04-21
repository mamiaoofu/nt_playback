<template>
  <div class="search-group" :style="style">
    <i v-if="showIcon" class="fa-solid fa-magnifying-glass search-icon"></i>
    <input ref="inputRef" :value="modelValue" @input="onInput" @keyup.enter="onEnter"
      :placeholder="placeholder" class="form-control form-control-sm search-input" />
    <i v-if="modelValue" class="fa-solid fa-xmark fa-times clear-icon" @click.stop="onClear"></i>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, defineExpose } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  placeholder: { type: String, default: 'Search...' },
  showIcon: { type: Boolean, default: true },
  style: { type: Object, default: () => ({}) },
  debounce: { type: Number, default: 800 }
})
const emit = defineEmits(['update:modelValue', 'typing', 'enter', 'clear'])

const inputRef = ref(null)
let debounceTimer = null

function onInput(e) {
  const v = e.target.value
  emit('update:modelValue', v)
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { emit('typing', v) }, props.debounce)
}

function onEnter() { emit('enter') }

function onClear() {
  emit('update:modelValue', '')
  emit('clear')
  // keep focus behavior to parent via exposed focus()
}

defineExpose({
  focus() { if (inputRef.value && typeof inputRef.value.focus === 'function') inputRef.value.focus() }
})
</script>

<style scoped>
.search-group { position: relative; }
.search-group .search-icon { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); color: #9aa4ad; font-size: 12px; pointer-events: none }
.search-group .search-input { padding-left: 28px; padding-right: 28px }
.search-group .clear-icon { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); color: #9aa4ad; font-size: 12px; cursor: pointer }
</style>
