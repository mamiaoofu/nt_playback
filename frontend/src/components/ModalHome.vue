<template>
  <div v-if="modelValue" class="modal-backdrop" @click.self="close" id="myFavoriteSearchModal">
    <div class="modal-box">
      <div class="modal-header">
        <h5 class="modal-title">My Favorite Search</h5>
        <button type="button" class="btn-close" @click="close"></button>
      </div>
      <div class="modal-body">
        <div class="tabs-header">
          <ul class="nav nav-tabs" style="border-bottom: none;">
            <li class="nav-item">
              <a class="nav-link" :class="{ active: activeTab === 'list' }" href="#" @click.prevent="activeTab = 'list'">List My Favorite</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" :class="{ active: activeTab === 'add' }" id="tab-btn-add" href="#" @click.prevent="activeTab = 'add'">Create My Favorite</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" :class="{ active: activeTab === 'edit' }" href="#" @click.prevent="activeTab = 'edit'">Edit My Favorite</a>
            </li>
          </ul>
          <div v-if="activeTab === 'list'" class="search-group" style="width: 260px; position: relative;">
            <i class="fa-solid fa-magnifying-glass search-icon"></i>
            <input type="text" v-model="searchTerm" class="form-control form-control-sm search-input"
              placeholder="Search...">
          </div>
        </div>

        <div class="tabs-content">
          <div :class="['tab-pane', { active: activeTab === 'list' }]">
            <div class="card-header-role" style="justify-content: space-between; align-items: center;">
              <div style="display: flex; align-items: center; gap: 12px;"></div>
              <div style="display: flex; align-items: center; gap: 10px;"></div>
            </div>

            <div class="card card-custom-role" style="border: 2px dashed #e2e8f0;">
              <div id="customRolesList" class="custom-roles-list" style="padding: 10px;height: 396px !important; overflow:auto !important;">
                <template v-if="favorites && favorites.length">
                  <div v-for="favorite in filteredFavorites" :key="favorite.id" class="custom-role-item"
                    @click="applyFavorite(favorite)" style="cursor: pointer;" :data-id="favorite.id">
                    <div class="group-card-main">
                      <div class="group-card-header">
                        <span class="group-card-title">{{ favorite.favorite_name }}</span>
                        <span class="group-card-group-badge">My Favorite</span>
                      </div>
                      <div class="group-card-desc">{{ favorite.description || 'No description provided for this favorite.' }}</div>
                    </div>
                    <div class="custom-role-actions" @click.stop>
                      <span class="role-box-badge" style="cursor: pointer;" @click.stop="editFavorite(favorite)">Click
                        to edit</span>
                      <button type="button" class="group-delete-btn" @click.stop="deleteFavorite(favorite.id)"
                        title="Delete My Favorite">
                        <i class="fas fa-trash"></i>
                      </button>
                    </div>
                  </div>
                </template>
                <div v-else class="empty-state" style="cursor: pointer; padding: 40px 0; text-align: center; color: #94a3b8;" @click="activeTab = 'add'">
                  <i class="fa-solid fa-plus-circle" style="font-size: 24px; margin-bottom: 10px;"></i>
                  <p>No favorites yet. Click to create.</p>
                </div>
                <div v-show="filteredFavorites.length === 0 && favorites && favorites.length" class="empty-state">
                  <i class="fa-solid fa-dove"></i>
                  <p>No My Favorite found matching your search.</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Add Tab (simplified, kept structure) -->
          <div :class="['tab-pane', { active: activeTab === 'add' }]">
              <div class="tab-placeholder">
              <div class="favorite-card">
                <form id="addFavoriteForm" @submit.prevent>
                  <div class="permissions-grid-1">
                      <div class="input-group" v-has-value>
                        <input v-model="addForm.firstName" required type="text" name="favoriteName" autocomplete="off" :class="['input', { 'form-input-modal': addNameTaken }]" maxlength="30">
                        <label class="title-label">Favorite name</label>
                        <div v-show="addNameTaken" class="validate" id="validateAddMyfavoriteName"><i class="fa-solid fa-circle-exclamation"></i> This name is already in the system.</div>
                      </div>
                    <div class="input-group" v-has-value>
                      <input v-model="addForm.description" required type="text" name="descriptionModal" autocomplete="off" class="input" maxlength="100">
                      <label class="title-label">Description</label>
                    </div>
                  </div>

                  <div class="permissions-grid-3">
                    <div class="input-group">
                      <CustomSelect class="select-search select-checkbox" v-model="addForm.databaseServer"
                        :options="mainDbOptions" placeholder="Database Server" name="databaseServerModal" />
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.from" v-flatpickr="{ target: addForm, key: 'from' }" ref="fromInputAdd" required type="text" name="fromModal" autocomplete="off" class="input">
                      <label class="title-label">From</label>
                      <span class="calendar-icon" @click="fromInputAdd && fromInputAdd.focus()"><i class="fa-regular fa-calendar"></i></span>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.to" v-flatpickr="{ target: addForm, key: 'to' }" ref="toInputAdd" required type="text" name="toModal" autocomplete="off" class="input">
                      <label class="title-label">To</label>
                      <span class="calendar-icon" @click="toInputAdd && toInputAdd.focus()"><i class="fa-regular fa-calendar"></i></span>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.duration" v-flatpickr="{ target: addForm, key: 'duration', mode: 'duration_range',  options: { enableTime: true, noCalendar: true, enableSeconds: true, time_24hr: true, dateFormat: 'H:i:S', defaultHour: 0, defaultMinute: 0 } }" required type="text" name="durationModal" autocomplete="off" class="input" >
                      <label class="title-label">Duration</label>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.fileName" required type="text" name="fileNameModal" autocomplete="off" class="input">
                      <label class="title-label">File Name</label>
                    </div>

                    <div class="input-group">
                      <CustomSelect class="select-checkbox" v-model="addForm.callDirection"
                        :options="[{ label: 'All', value: 'All' }, { label: 'Internal', value: 'Internal' }, { label: 'Inbound', value: 'Inbound' }, { label: 'Outbound', value: 'Outbound' }]"
                        placeholder="Call Direction" name="callDirectionModal" />
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.customerNumber" required type="text" name="customerNumberModal" autocomplete="off" class="input">
                      <label class="title-label">Customer Number</label>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.extension" required type="text" name="extensionModal" autocomplete="off" class="input">
                      <label class="title-label">Extension</label>
                    </div>

                    <div class="input-group">
                      <CustomSelect class="select-search select-checkbox" :class="{ up: 'up' }" v-model="addForm.agent" :options="agentOptions" placeholder="Agent" name="agentModal" />
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.fullName" required type="text" name="fullNameModal" autocomplete="off" class="input" >
                      <label class="title-label">Full Name</label>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="addForm.customField" required type="text" name="customFieldModal" autocomplete="off" class="input">
                      <label class="title-label">Custom Field</label>
                    </div>
                  </div>

                </form>
              </div>
            </div>
          </div>

          <div :class="['tab-pane', { active: activeTab === 'edit' }]">
            <div id="edit-placeholder" :class="['empty-tab-placeholder', { 'd-none': !showEditPlaceholder }]" style="cursor: pointer;" @click="activeTab = 'list'">
              <i class="fa-solid fa-pen-to-square"></i>Select a my favorite to edit.
            </div>
            <div id="edit-form-container" :class="['tab-placeholder', { 'd-none': !showEditForm }]" >
              <div class="favorite-card">
                <form id="addFavoriteForm" @submit.prevent>
                  <div class="permissions-grid-1">
                    <div class="input-group" v-has-value>
                      <input v-model="editForm.firstName" required type="text" name="favoriteName" autocomplete="off" :class="['input', { 'form-input-modal': editNameTaken }]"  maxlength="30">
                      <input v-model="editForm.id" required type="text" name="favoriteId" autocomplete="off" class="input d-none">
                      <label class="title-label">Favorite name</label>
                      <div v-show="editNameTaken" class="validate" id="validateEditMyfavoriteName"><i class="fa-solid fa-circle-exclamation"></i> This name is already in the system.</div>
                    </div>
                    <div class="input-group" v-has-value>
                      <input v-model="editForm.description" required type="text" name="descriptionModal" autocomplete="off" class="input"  maxlength="50">
                      <label class="title-label">Description</label>
                    </div>
                  </div>

                  <div class="permissions-grid-3">
                    <div class="input-group">
                      <CustomSelect class="select-search select-checkbox" v-model="editForm.databaseServer"
                        :options="mainDbOptions" placeholder="Database Server" name="databaseServerEdit" />
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.from" v-flatpickr="{ target: editForm, key: 'from' }" ref="fromInput" required type="text" name="fromModal" autocomplete="off" class="input">
                      <label class="title-label">From</label>
                      <span class="calendar-icon" @click="fromInput && fromInput.focus()"><i
                          class="fa-regular fa-calendar"></i></span>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.to" v-flatpickr="{ target: editForm, key: 'to' }" ref="toInput" required type="text" name="toModal" autocomplete="off" class="input">
                      <label class="title-label">To</label>
                      <span class="calendar-icon" @click="toInput && toInput.focus()"><i
                          class="fa-regular fa-calendar"></i></span>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.duration" v-flatpickr="{ target: editForm, key: 'duration', mode: 'duration_range',  options: { enableTime: true, noCalendar: true, enableSeconds: true, time_24hr: true, dateFormat: 'H:i:S', defaultHour: 0, defaultMinute: 0 } }" required type="text" name="durationModal" autocomplete="off" class="input" >
                      <label class="title-label">Duration</label>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.fileName" required type="text" name="fileNameModal" autocomplete="off" class="input" >
                      <label class="title-label">File Name</label>
                    </div>

                    <div class="input-group">
                      <CustomSelect class="select-checkbox" v-model="editForm.callDirection"
                        :options="[{ label: 'All', value: 'All' }, { label: 'Internal', value: 'Internal' }, { label: 'Inbound', value: 'Inbound' }, { label: 'Outbound', value: 'Outbound' }]"
                        placeholder="Call Direction" name="callDirectionEdit" />
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.customerNumber" required type="text" name="customerNumberModal" autocomplete="off" class="input" >
                      <label class="title-label">Customer Number</label>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.extension" required type="text" name="extensionModal" autocomplete="off" class="input">
                      <label class="title-label">Extension</label>
                    </div>

                    <div class="input-group">
                      <CustomSelect class="select-search select-checkbox" v-model="editForm.agent" :options="agentOptions" placeholder="Agent" name="agentEdit" />
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.fullName" required type="text" name="fullNameModal" autocomplete="off" class="input" >
                      <label class="title-label">Full Name</label>
                    </div>

                    <div class="input-group" v-has-value>
                      <input v-model="editForm.customField" required type="text" name="customFieldModal" autocomplete="off" class="input">
                      <label class="title-label">Custom Field</label>
                    </div>
                  </div>

                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button v-if="activeTab === 'add'" id="btn-reset-fav" class="btn-role btn-secondary" @click.prevent="resetAddForm()"
          style="margin-right: auto;">
          <i class="fas fa-undo"></i>
          Reset
        </button>

        <button class="btn-role btn-secondary" @click="close()">
          <i class="fas fa-times"></i>
          Cancel
        </button>

        <button v-if="activeTab === 'add' || activeTab === 'edit'" id="btn-save-fav" class="btn-role btn-primary"
          :disabled="(activeTab === 'add' && addNameTaken) || (activeTab === 'edit' && editNameTaken)"
          @click.prevent="saveFavorite()">
          <i class="fas fa-save"></i>
          Save Changes
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, computed, reactive, onMounted, watch, nextTick } from 'vue'
import { API_ADD_MY_FAVORITE_SEARCH, API_CHECK_MY_FAVORITE_NAME } from '../api/paths'
import { showToast , confirmDelete } from '../assets/js/function-all'
import { ensureCsrf, getCsrfToken } from '../api/csrf'
import CustomSelect from './CustomSelect.vue'

import '../assets/js/sweetalert2@11.min.js'
import '../assets/css/modal-favorite.css'

const props = defineProps({ modelValue: { type: Boolean, default: false }, favorites: { type: Array, default: () => [] }, mainDbOptions: { type: Array, default: () => [] }, agentOptions: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue', 'apply', 'edit', 'delete'])
const activeTab = ref('list')
const searchTerm = ref('')

const filters = reactive({ databaseServer: '' })

const filteredFavorites = computed(() => {
  const q = String(searchTerm.value || '').trim().toLowerCase()
  if (!q) return props.favorites
  return props.favorites.filter(f => (String(f.favorite_name || '') + ' ' + String(f.description || '')).toLowerCase().includes(q))
})

const fromInputAdd = ref(null)
const toInputAdd = ref(null)
const fromInput = ref(null)
const toInput = ref(null)

// add form state
const addForm = reactive({
  firstName: '',
  description: '',
  databaseServer: '',
  from: '',
  to: '',
  duration: '',
  fileName: '',
  callDirection: [],
  customerNumber: '',
  extension: '',
  agent: '',
  fullName: '',
  customField: ''
})

// edit form state
const editForm = reactive({
  id: null,
  firstName: '',
  description: '',
  databaseServer: '',
  from: '',
  to: '',
  duration: '',
  fileName: '',
  callDirection: [],
  customerNumber: '',
  extension: '',
  agent: '',

  fullName: '',
  customField: ''
})

// control visibility of the edit-placeholder helper text
const showEditPlaceholder = ref(true)
// control visibility of the edit form container
const showEditForm = ref(false)

// reset placeholder when modal opens
watch(() => props.modelValue, (val) => {
  // Reset to list tab whenever the modal is opened or closed
  activeTab.value = 'list'
  if (val) {
    showEditPlaceholder.value = true
    showEditForm.value = false
  }
})

function close() { emit('update:modelValue', false) }
function applyFavorite(f) { emit('apply', f); emit('update:modelValue', false) }
function editFavorite(f) {
  // populate editForm from favorite.raw_data and metadata
  try {
    // clear previous edit values first so missing keys don't retain old values
    try { resetEditForm() } catch (e) {}
    const raw = typeof f.raw_data === 'string' ? JSON.parse(f.raw_data || '{}') : (f.raw_data || {})
    editForm.id = f.id || null
    editForm.firstName = f.favorite_name || ''
    editForm.description = f.description || ''

    // map raw keys
    const keyMap = {
      database_name: 'databaseServer',
      start_date: 'from',
      end_date: 'to',
      file_name: 'fileName',
      duration: 'duration',
      customer: 'customerNumber',
      agent: 'agent',
      call_direction: 'callDirection',
      extension: 'extension',
      full_name: 'fullName',
      custom_field: 'customField'
    }
    console.log(' editFavorite raw data:', raw)
    for (const [k, v] of Object.entries(raw)) {
      const t = keyMap[k]
      if (!t || !Object.prototype.hasOwnProperty.call(editForm, t)) continue

      // normalize multi-select fields (these CustomSelects use checkbox mode)
      if (['databaseServer', 'agent', 'callDirection'].includes(t)) {
        // build an array of values
        let vals = []
        if (v == null || v === '') {
          vals = []
        } else if (Array.isArray(v)) {
          vals = v.slice()
        } else if (typeof v === 'string') {
          if (v.indexOf(',') !== -1) vals = v.split(',').map(x => x.trim()).filter(Boolean)
          else vals = [v]
        } else {
          vals = [v]
        }

        // convert types/casing to match option values
        if (t === 'databaseServer' || t === 'agent') {
          // ids: convert numeric strings to numbers
          vals = vals.map(x => { const s = String(x).trim(); return /^\d+$/.test(s) ? Number(s) : s })
        }
        if (t === 'callDirection') {
          // normalize to capitalized form (Inbound, Outbound, Internal, All)
          vals = vals.map(x => { const s = String(x || '').trim(); return s ? (s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()) : s })
        }

        editForm[t] = vals
      } else {
        editForm[t] = v
      }
    }
    // hide the placeholder helper, show edit form and switch to edit tab
    showEditPlaceholder.value = false
    showEditForm.value = true
    activeTab.value = 'edit'
    // sync duration input value into flatpickr instance after DOM updates
    nextTick(() => {
      try {
        const el = document.querySelector('#edit-form-container input[name="durationModal"]')
        if (el) {
          // set the raw input value (v-model already updated editForm.duration)
          el.value = editForm.duration || ''
          // update has-value class
          try { el.parentNode && el.parentNode.classList.toggle('has-value', (el.value || '').toString().trim() !== '') } catch(e){}
          // normalize and sync flatpickr instance: handle "start - end" and comma-separated values
          try {
            const inst = el._flatpickrInstance || el._flatpickr
            const dstrRaw = editForm.duration ?? ''
            const dstr = String(dstrRaw).trim()
            let normDur = dstr
            if (Array.isArray(dstrRaw)) {
              normDur = dstrRaw.map(x => String(x || '').trim()).filter(Boolean).join(' - ')
            } else if (dstr.indexOf(',') !== -1 && !dstr.includes(' - ')) {
              normDur = dstr.split(',').map(x => String(x || '').trim()).filter(Boolean).join(' - ')
            }
            // update model and input to normalized string
            try { editForm.duration = normDur } catch (e) {}
            try { el.value = normDur } catch (e) {}

            const parseTimeToDate = (s) => {
              if (!s) return null
              const parts = String(s).split(':').map(x => parseInt(x, 10) || 0)
              const d = new Date()
              d.setHours(parts[0] || 0, parts[1] || 0, parts[2] || 0, 0)
              return d
            }

            if (inst && typeof inst.setDate === 'function') {
              if (!normDur) {
                try { inst.clear() } catch (e) {}
                try {
                  if (el._flatpickrToContainer) {
                    const inputs = el._flatpickrToContainer.querySelectorAll('input')
                    inputs.forEach(i => i.value = '00')
                  }
                } catch (e) {}
              } else if (normDur.includes(' - ')) {
                const [startStr, endStr] = normDur.split(' - ').map(x => x.trim())
                const sd = parseTimeToDate(startStr)
                const ed = parseTimeToDate(endStr)
                if (sd && ed) {
                  try { inst.setDate([sd, ed], true) } catch (e) {}
                  // ensure input shows normalized separator after flatpickr updates it
                  setTimeout(() => { try { el.value = normDur } catch (e) {} }, 50)
                } else if (sd) {
                  try { inst.setDate(sd, true) } catch (e) {}
                  setTimeout(() => { try { el.value = startStr } catch (e) {} }, 50)
                } else {
                  try { inst.clear() } catch (e) {}
                }
              } else if (normDur.indexOf(':') !== -1) {
                const d = parseTimeToDate(normDur)
                if (d) {
                  try { inst.setDate(d, true) } catch (e) {}
                  setTimeout(() => { try { el.value = normDur } catch (e) {} }, 50)
                } else {
                  try { inst.clear() } catch (e) {}
                }
              } else {
                try { el.value = normDur } catch (e) {}
              }
            }
          } catch (e) {}
        }
      } catch (e) {}
    })
    // optionally focus first input in edit form after render
  } catch (e) {
    console.error('editFavorite parse error', e)
  }
}
async function deleteFavorite(id) {
  try {
    if (!id) return
    const confirmed = await confirmDelete()
    if (!confirmed) return

    const payload = { action: 'delete', favorite_id: id }
    const json = await postFavoriteAction(payload)
    if (json && json.status === 'success') {
      showToast(json.message || 'Deleted successfully', 'success')

      // Remove item from DOM immediately as a visual fallback
      try {
        const itemToRemove = document.querySelector(`#myFavoriteSearchModal .custom-role-item[data-id="${id}"]`)
        if (itemToRemove) itemToRemove.remove()

        const listContainer = document.getElementById('customRolesList')
        // if (listContainer && !listContainer.querySelector('.custom-role-item')) {
        //   listContainer.insertAdjacentHTML('afterbegin', `
        //       <div class="empty-state" onclick="document.getElementById('tab-btn-add') && document.getElementById('tab-btn-add').click()" style="cursor: pointer; padding: 40px 0; text-align: center; color: #94a3b8;">
        //           <i class="fa-solid fa-plus-circle" style="font-size: 24px; margin-bottom: 10px;"></i>
        //           <p>No favorites yet. Click to create.</p>
        //       </div>
        //       `)
        // }
      } catch (e) {
        console.warn('DOM remove fallback failed', e)
      }

      // notify parent to update reactive list
      emit('delete', id)
    } else {
      showToast(json.message || 'Failed to delete favorite', 'error')
    }
  } catch (e) {
    console.error('deleteFavorite error', e)
    showToast('Failed to delete favorite', 'error')
  }
}

// reset add form
function resetAddForm() {
  addForm.firstName = ''
  addForm.description = ''
  addForm.databaseServer = ''
  addForm.from = ''
  addForm.to = ''
  addForm.duration = ''
  addForm.fileName = ''
  addForm.callDirection = []
  addForm.customerNumber = ''
  addForm.extension = ''
  addForm.agent = ''
  addForm.fullName = ''
  addForm.customField = ''
  // sync has-value classes if needed
  try {
    const wrap = document.querySelector('#myFavoriteSearchModal .tab-placeholder')
    if (wrap) {
      const groups = wrap.querySelectorAll('.input-group')
      groups.forEach(g => {
        const input = g.querySelector('input, textarea, select')
        if (!input) return
        const val = input.value
        g.classList.toggle('has-value', val !== null && String(val).trim() !== '')
      })
    }
  } catch (e) {}
}

// reset edit form values
function resetEditForm() {
  editForm.id = null
  editForm.firstName = ''
  editForm.description = ''
  editForm.databaseServer = ''
  editForm.from = ''
  editForm.to = ''
  editForm.duration = ''
  editForm.fileName = ''
  editForm.callDirection = []
  editForm.customerNumber = ''
  editForm.extension = ''
  editForm.agent = ''
  editForm.fullName = ''
  editForm.customField = ''
  editNameTaken.value = false
  // sync has-value classes inside edit form container if visible
  try {
    const wrap = document.querySelector('#edit-form-container')
    if (wrap) {
      const groups = wrap.querySelectorAll('.input-group')
      groups.forEach(g => {
        const input = g.querySelector('input, textarea, select')
        if (!input) return
        const val = input.value
        g.classList.toggle('has-value', val !== null && String(val).trim() !== '')
      })
    }
  } catch (e) {}
}

// duplicate name check state & debounce timers
const addNameTaken = ref(false)
const editNameTaken = ref(false)
let _addNameTimer = null
let _editNameTimer = null

async function checkFavoriteNameAPI(name, favoriteId = null) {
  if (!name || String(name).trim() === '') return false
  try {
    const url = API_CHECK_MY_FAVORITE_NAME() + `?favoriteName=${encodeURIComponent(name)}${favoriteId ? `&favoriteId=${encodeURIComponent(favoriteId)}` : ''}`
    const res = await fetch(url, { method: 'GET', credentials: 'include' })
    if (!res.ok) return false
    const j = await res.json()
    return j && j.is_taken === true
  } catch (e) {
    console.error('checkFavoriteNameAPI error', e)
    return false
  }
}

// debounce watches
watch(() => addForm.firstName, (val) => {
  addNameTaken.value = false
  if (_addNameTimer) clearTimeout(_addNameTimer)
  _addNameTimer = setTimeout(async () => {
    if (!val || String(val).trim() === '') { addNameTaken.value = false; return }
    addNameTaken.value = await checkFavoriteNameAPI(val)
  }, 400)
})

watch(() => editForm.firstName, (val) => {
  editNameTaken.value = false
  if (_editNameTimer) clearTimeout(_editNameTimer)
  _editNameTimer = setTimeout(async () => {
    if (!val || String(val).trim() === '') { editNameTaken.value = false; return }
    editNameTaken.value = await checkFavoriteNameAPI(val, editForm.id)
  }, 400)
})

// helper to POST form data to backend endpoint used by create/edit
async function postFavoriteAction(formObj) {
  try {
    const fd = new FormData()
    for (const k of Object.keys(formObj)) {
      const v = formObj[k]
      if (Array.isArray(v)) fd.append(k, v.join(','))
      else if (v === null || v === undefined) fd.append(k, '')
      else fd.append(k, String(v))
    }
    // CSRF token is fetched at login/startup and cached; use cached token
    const csrfToken = getCsrfToken()
    const res = await fetch(API_ADD_MY_FAVORITE_SEARCH(), { method: 'POST', body: fd, credentials: 'include', headers: { 'X-CSRFToken': csrfToken || '' } })
    if (!res.ok) throw new Error('Network response not ok')
    return await res.json()
  } catch (e) {
    console.error('postFavoriteAction error', e)
    return { status: 'error', message: e.message }
  }
}

// using shared showToast from assets/js/toast.js

// Save handler for add/edit
async function saveFavorite() {
  if (activeTab.value === 'add') {
    const payload = {
      action: 'create',
      favorite_name: addForm.firstName || '(no name)',
      favorite_description: addForm.description || '',
      database_name: Array.isArray(addForm.databaseServer) ? addForm.databaseServer.join(',') : (addForm.databaseServer || ''),
      call_direction: Array.isArray(addForm.callDirection) ? addForm.callDirection.join(',') : (addForm.callDirection || ''),
      start_date: addForm.from || '',
      end_date: addForm.to || '',
      file_name: addForm.fileName || '',
      customer: addForm.customerNumber || '',
      extension: addForm.extension || '',
      agent: Array.isArray(addForm.agent) ? addForm.agent.join(',') : (addForm.agent || ''),
      full_name: addForm.fullName || '',
      duration: addForm.duration || '',
      custom_field: addForm.customField || ''
    }
    const json = await postFavoriteAction(payload)
    if (json && json.status === 'success') {
      // notify parent to refresh list
      showToast(`Create ${json.favorite.favorite_name} successfully`, 'success')
      emit('edit', json.favorite)
      // make sure tab is reset to list after successful save
      activeTab.value = 'list'
      // clear add form so values are not left behind
      try { resetAddForm() } catch (e) {}
    } else {
      showToast(json.message || 'Failed to create favorite', 'error')
    }
  } else if (activeTab.value === 'edit') {
    const payload = {
      action: 'edit',
      favorite_id: editForm.id,
      favorite_name: editForm.firstName || '(no name)',
      favorite_description: editForm.description || '',
      database_name: Array.isArray(editForm.databaseServer) ? editForm.databaseServer.join(',') : (editForm.databaseServer || ''),
      call_direction: Array.isArray(editForm.callDirection) ? editForm.callDirection.join(',') : (editForm.callDirection || ''),
      start_date: editForm.from || '',
      end_date: editForm.to || '',
      file_name: editForm.fileName || '',
      customer: editForm.customerNumber || '',
      extension: editForm.extension || '',
      agent: Array.isArray(editForm.agent) ? editForm.agent.join(',') : (editForm.agent || ''),
      full_name: editForm.fullName || '',
      duration: editForm.duration || '',
      custom_field: editForm.customField || ''
    }
    const json = await postFavoriteAction(payload)
    if (json && json.status === 'success') {
      showToast(`Edit ${json.favorite.favorite_name} successfully`, 'success')
      emit('edit', json.favorite)
      // make sure tab is reset to list after successful save
      activeTab.value = 'list'
      // clear edit form after successful save
      try { resetEditForm() } catch (e) {}
    } else {
      showToast(json.message || 'Failed to update favorite', 'error')
    }
  }
}
</script>

<style scoped>
.tabs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px
}

.tabs-header .tab-buttons {
  display: flex;
  gap: 8px
}

.tab-btn {
  padding: 6px 10px;
  border-radius: 6px;
  border: none;
  background: #f3f4f6;
  cursor: pointer
}

.tab-btn.active {
  background: #e2e8f0
}

.custom-role-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03)
}

.group-card-title {
  font-weight: 600
}

.group-card-desc {
  font-size: 10px;
  color: #6b7280
}

.custom-role-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 10px;
}

@keyframes fadeInTab {
  from {
    opacity: 0;
    transform: translateY(5px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* แก้ไขข้อขัดแย้งกับ Bootstrap .modal */
#myFavoriteSearchModal .modal {
  display: flex !important;
  /* บังคับให้แสดงผล (แก้ display: none ของ Bootstrap) */
  position: relative !important;
  /* ให้จัดกึ่งกลางตาม Flexbox ของ Overlay */
  top: auto !important;
  /* ยกเลิกการจัดตำแหน่งแบบ Absolute/Fixed เดิม */
  left: auto !important;
  width: 90%;
  /* กำหนดความกว้างตาม Design เดิม */
  /* height: auto !important; */
  transform: scale(0.9);
  /* เริ่มต้นให้เล็กนิดนึงเพื่อรอ Animation */
  transition: all 0.3s ease;
  z-index: 1006;
}

#myFavoriteSearchModal.show .modal {
  transform: scale(1) !important;
  /* ขยายเต็มเมื่อแสดงผล */
}

/* Fix scrolling to be inside tabs-content only */
#myFavoriteSearchModal .modal-body {
  padding: 0 !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column;
  min-height: 0;
  /* ช่วยให้ Flex item หดตัวได้เมื่อ content ยาวเกิน */
}

/* Allow select dropdowns to escape clipping of inner containers (show full list) */
#myFavoriteSearchModal .modal-body,
#myFavoriteSearchModal .tabs-content,
#myFavoriteSearchModal .favorite-card,
#myFavoriteSearchModal .custom-roles-list {
  overflow: visible !important;
}

.btn-secondary {
  background: #f1f5f9 !important;
  border: 1px solid #e2e8f0 !important;
  color: #64748b !important;
}

.btn-secondary:hover {
  background: #e2e8f0 !important;
  color: #1e293b !important;
}

/* Tabs Styling */
#myFavoriteSearchModal .tabs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  margin: 0px 24px 0 24px;
  flex-shrink: 0;
  gap: 24px;
}

.nav-tabs .nav-link {
    /* cursor: pointer; */
    padding: 8px 12px;
}
.nav-tabs .nav-link:hover {
    border-color: transparent;
    color: #416fd6;
}
.nav-tabs .nav-link.active {
    color: #416fd6;
    font-weight: 600;
    border-bottom: 2px solid #416fd6;
    background: transparent;
}

#myFavoriteSearchModal .tabs-content {
  flex: 1;
  overflow: hidden;
  /* ปิด scroll ที่ container ใหญ่ */
  padding: 12px 23px 11px 22px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

#myFavoriteSearchModal .tab-pane {
  display: none;
  animation: fadeInTab 0.3s ease;
  flex: 1;
  min-height: 400px;
  flex-direction: column;
}

#myFavoriteSearchModal .tab-pane.active {
  display: flex;
}

@keyframes fadeInTab {
  from {
    opacity: 0;
    transform: translateY(5px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-tab-placeholder {
  padding: 60px 20px;
  text-align: center;
  color: #94a3b8;
  background: #ffffff;
  border-radius: 16px;
  border: 2px dashed #e2e8f0;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  height: 100%;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  transition: all 0.2s ease;
}

.empty-tab-placeholder:hover {
  border-color: #416fd6;
  background-color: #f8fafc;
  color: #416fd6;
}

.empty-tab-placeholder i {
  font-size: 32px;
  margin-bottom: 12px;
  opacity: 0.5;
  transition: all 0.2s ease;
}

.empty-tab-placeholder:hover i {
  opacity: 1;
  transform: scale(1.1);
}

.tab-placeholder {
  border: none;
  display: block;
  text-align: left;
  color: inherit;
  padding: 0;
  background: transparent;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.favorite-card {
  background: #ffffff;
  padding: 12px;
  border-radius: 16px;
  border: 2px dashed #e2e8f0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  overflow-y: auto;
  flex: 1;
  min-height: 400px;
}

.favorite-card::-webkit-scrollbar {
  width: 4px;
}

.favorite-card::-webkit-scrollbar-track {
  border: 2px dashed #e2e8f0;
  margin-top: 6px;
  margin-bottom: 6px;
}

.favorite-card::-webkit-scrollbar-thumb {
  background-color: #416fd6;
  border-radius: 4px;
}

.form-label-modal {
  font-size: 12px !important;
}

/* Ensure CustomSelect dropdowns inside modal appear above favorite-card and other containers */
#myFavoriteSearchModal .favorite-card {
  overflow: visible !important;
}
#myFavoriteSearchModal .options {
  z-index: 4000 !important;
  position: absolute !important;
}

.empty-tab-placeholder {
  padding: 60px 20px;
  text-align: center;
  color: #94a3b8;
  background: #ffffff;
  border-radius: 16px;
  border: 2px dashed #e2e8f0;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  height: 100%;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  transition: all 0.2s ease;
}

.empty-tab-placeholder:hover {
  border-color: #416fd6;
  background-color: #f8fafc;
  color: #416fd6;
}

.empty-tab-placeholder i {
  font-size: 32px;
  margin-bottom: 12px;
  opacity: 0.5;
  transition: all 0.2s ease;
}

.empty-tab-placeholder:hover i {
  opacity: 1;
  transform: scale(1.1);
}

.tab-placeholder {
  border: none;
  display: block;
  text-align: left;
  color: inherit;
  padding: 0;
  background: transparent;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.favorite-card {
  background: #ffffff;
  padding: 12px;
  border-radius: 16px;
  border: 2px dashed #e2e8f0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.favorite-card::-webkit-scrollbar {
  width: 4px;
}

.favorite-card::-webkit-scrollbar-track {
  border: 2px dashed #e2e8f0;
  margin-top: 6px;
  margin-bottom: 6px;
}

.favorite-card::-webkit-scrollbar-thumb {
  background-color: #416fd6;
  border-radius: 4px;
}

.form-label-modal {
  font-size: 12px !important;
}
/* Validation styles for modal inputs */
.form-input-modal {
  border: 1px solid rgb(245, 163, 163) !important;
  box-shadow: rgba(220, 53, 69, 0.25) 0px 0px 0px 0.2rem !important;
}
</style>