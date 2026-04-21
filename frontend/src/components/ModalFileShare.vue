<template>
    <!-- Modal Share -->
    <div v-if="modelValue" class="modal-backdrop" id="fileShareModal">
        <div v-if="files && files.length" class="modal-box" style="max-width: 640px;">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 8px">
                    <div class="blue-icon"><i class="fa-solid fa-share-nodes"></i></div>
                    <h3 class="modal-title ad">File Share</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>

            <div class="modal-body">
                <div class="mb-2">You have selected <strong>{{ files.length }}</strong> files to grant access:</div>

                <div class="card card-custom-role" style="border: 2px dashed #e2e8f0;">
                    <div class="custom-roles-list" style="padding: 10px; max-height: 226px; overflow:auto;">
                        <div v-for="(f, idx) in files" :key="f.file_id || f.file_name + '-' + idx"
                            class="custom-role-item">
                            <div style="display:flex;align-items:center;gap:10px;">
                                <div class="blue-icon" style="font-size: 14px;width: 25px;height: 25px;"><i
                                        class="fa-solid fa-file-audio"></i></div>
                                <div class="group-card-main">
                                    <div class="group-card-header">
                                        <span class="group-card-title">{{ truncateFileName(f.file_name) }}</span>
                                    </div>
                                    <div class="group-card-desc">Customer number: {{ f.customer_number || f.customerNumber || '-' }} | Date: {{ formatDate(f.start_datetime) }}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="mt-3">
                    <div class="d-flex align-items-center" style="gap:12px; margin-top:6px;">
                        <div class="form-check" v-if="Store.hasPermission('Create Delegate File')">
                            <input class="form-check-input" type="radio" id="shareTypeUser" value="user" v-model="selectionType">
                            <label class="form-check-label" for="shareTypeUser">Deleagate</label>
                        </div>
                        <div class="form-check" v-if="Store.hasPermission('Create Ticket') ">
                            <input class="form-check-input" type="radio" id="shareTypeTicket" value="ticket" v-model="selectionType">
                            <label class="form-check-label" for="shareTypeTicket">Ticket</label>
                        </div>
                    </div>
                </div>

                <div class="permissions-grid-2">
                    <div v-if="selectionType === 'user'" class="input-group">
                        <CustomSelect class="select-search select-checkbox" v-model="shareUser" :always-up="true" :options="userOptions"  placeholder="User" name="shareUser" />
                    </div>

                    <div v-else class="input-group" v-has-value>
                        <input required type="text" name="emailTicket" autocomplete="off" class="input" v-model="emailTicket" maxlength="255">
                        <label class="title-label">Email</label>
                    </div>

                    <div class="input-group" v-has-value>
                        <input required type="number" name="limitAccessTimes" autocomplete="off" class="input" :class="{ 'input-disabled': selectionType === 'user' }" min="0" max="99" :disabled="selectionType === 'user'" v-model.number="limitAccessTimes">
                        <label class="title-label">Limit access times</label>
                    </div>
                     
                    <div class="input-group" v-has-value>
                        <input ref="fromInputAdd" v-model="start" v-flatpickr="{ target: picker, key: 'from' }" required type="text" name="fromModal" autocomplete="off" class="input">
                        <label class="title-label">From</label>
                        <span class="calendar-icon" @click="fromInputAdd && fromInputAdd.focus()"><i class="fa-regular fa-calendar"></i></span>
                    </div>

                    <div class="input-group" v-has-value>
                                              <input ref="toInputAdd" v-model="expire" v-flatpickr="{ target: picker, key: 'to' }" required type="text" name="toModal" autocomplete="off" class="input">
                      <label class="title-label">To</label>
                      <span class="calendar-icon" @click="toInputAdd && toInputAdd.focus()"><i class="fa-regular fa-calendar"></i></span>
                    </div>
                    
                </div>

                <div class="permissions-grid">
                    <div class="input-group" v-has-value>
                        <textarea rows="4" required type="text" name="descTicket" autocomplete="off" class="input" v-model="descTicket" style="height: auto;"></textarea>
                        <label class="title-label">Description</label>
                    </div>
                </div>

                <!-- Show Download label only when current selection type allows download based on permission -->
                <label class="form-label" style="font-weight: 500;" v-if="(selectionType === 'user' && Store.hasPermission('Download Delegate File')) || (selectionType === 'ticket' && Store.hasPermission('Download Ticket File'))">Download</label>


                <div class="d-flex align-items-center" style="gap:12px;" v-if="(selectionType === 'user' && Store.hasPermission('Download Delegate File')) || (selectionType === 'ticket' && Store.hasPermission('Download Ticket File'))">
                    <div class="form-check">
                        <input class="form-check-input" type="radio" id="permissionsYesDownload" value="true" v-model="permissions">
                        <label class="form-check-label" for="permissionsYesDownload">Yes</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" id="permissionsNoDownload" value="false" v-model="permissions">
                        <label class="form-check-label" for="permissionsNoDownload">No</label>
                    </div>
                </div>
            </div>

            <div class="modal-footer" style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;">
                <div style="display:flex;align-items:center;">
                    <button class="btn-role btn-secondary" @click="resetForm" style="margin:0; padding:8px 14px;"><i class="fas fa-eraser"></i> Reset</button>
                </div>
                <div style="display:flex;gap:8px;">
                    <button class="btn-role btn-secondary" @click="close"><i class="fas fa-times"></i> Cancel</button>
                    <button class="btn-role btn-primary" :disabled="files.length === 0" @click="onCreate"><i class="fa-solid fa-plus"></i> Create</button>
                </div>
            </div>
        </div>

        <div v-else class="modal-box" style="max-width: 520px;">
            <div class="modal-header">
                <h5 class="modal-title">No Files Selected</h5>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body" style="text-align: center; padding: 32px 24px;">
                <div style="font-size: 36px; color: #f6c23e;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <p style="margin-top: 12px; color: #6b7280;">Please select at least one audio file to share.</p>
            </div>
            <div class="modal-footer" style="justify-content: center;">
                <button class="btn-role btn-primary" @click="close">OK</button>
            </div>
        </div>
    </div>

    <!-- Modal Share complete -->
    <div v-if="showResult" class="modal-backdrop" id="fileShareResult">
        <div class="modal-box" style="max-width: 400px;">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 8px">
                    <div class="green-icon"><i class="fa-solid fa-share-nodes"></i></div>
                    <h3 class="modal-title ad" v-if="resultType === 'ticket'">Ticket Created Successfully</h3>
                    <h3 class="modal-title ad" v-else>File shared successfully!</h3>
                </div>
                <button type="button" class="btn-close" @click="closeResult"></button>
            </div>

            <div class="modal-body">
                <div v-if="resultType === 'ticket'">
                    <div style="text-align:center; margin-bottom:12px;">
                        <i class="fa-regular fa-check-circle" style="color:#10b981;margin-bottom: 15px;font-size: 45px;"></i>
                        <p style="margin:0">Ticket <strong style="color:#2563eb">{{ resultData.ticketCode }}</strong> created successfully!</p>
                    </div>

                    <div class="card card-detail-to" style="padding:16px; border:1px solid #e6eef8;">
                        <p style="margin:0 0 8px 0">Dear Sir ({{ resultData.recipient }}),</p>
                        <p style="margin:0 0 12px 0">An access ticket has been created for you to listen to specific audio records on SeekTrack.</p>
                        <div style="border:1px dashed #e6eef8; padding:12px; margin-bottom:12px;">
                            <div class="detail-file-share"><strong class="strong-title">Ticket Code:</strong> <span style="color:#2563eb">{{ resultData.ticketCode }}</span></div>
                            <div class="detail-file-share"><strong class="strong-title">Password:</strong> <code style="background:#f3f4f6; padding:4px 8px; border-radius:4px">{{ resultData.password }}</code>
                            </div>
                            <div class="detail-file-share"><strong class="strong-title">Valid Start:</strong> {{ resultData.validStart }}</div>
                            <div class="detail-file-share"><strong class="strong-title">Valid Expire:</strong> {{ resultData.validExpire }}</div>
                            <div class="detail-file-share"><strong class="strong-title">Limit Access Times:</strong> {{ resultData.limitAccessTimes }}</div>
                        </div>
                        <p style="margin:0 0 8px 0">Please visit our portal to login using the credentials above.</p>
                        <div style="margin-bottom:12px;"><a href="/login">https://192.168.1.90/login</a></div>
                        <div>
                            Best regards,<br>
                            <b>SeekTrack Team</b>
                        </div>
                    </div>
                </div>

                <div v-else>
                    <div style="text-align:center; margin-bottom:12px;">
                        <i class="fa-regular fa-check-circle" style="color:#10b981;margin-bottom: 15px;font-size: 45px;"></i>
                        <p style="margin:0">User <strong style="color:#2563eb">{{ resultData.recipient }}</strong> created successfully!</p>
                    </div>
                    <div class="card" style="padding:16px; border:1px solid #e6eef8;">
                        <p>Dear Sir,</p>
                        <p>Files are shared so you can listen to specific audio records on <br> SeekTrack.</p>
                        <div style="border:1px dashed #e6eef8; padding:12px; margin-bottom:12px;">
                            <div><strong>Valid Start:</strong> {{ resultData.validStart }}</div>
                            <div><strong>Valid Expire:</strong> {{ resultData.validExpire }}</div>
                        </div>
                        <p>You can find it in the ticket menu.</p>
                        <div style="margin-bottom:12px;"><a href="/login">https://192.168.1.95/ticket</a></div>
                        <div>
                            Best regards,<br>
                            <b>SeekTrack Team</b>
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="resultType === 'ticket'">
                <div class="modal-footer btn-file-share" style="justify-content: space-between;">
                    <button class="btn-role btn-secondary" @click="copyCardContent"><i class="fa-regular fa-copy" style="font-size: 12px;"></i> Copy form</button>
                    <button class="btn-role btn-primary" @click="sendResultByEmail"><i class="fa-regular fa-envelope" style="font-size: 12px;"></i> Send email</button>
                </div>
            </div>
            <div v-else>
                <div class="modal-footer btn-file-share" style="justify-content: space-between;">
                    <button class="btn-role btn-primary" @click="closeResult">OK</button>
                </div>
            </div>
            
        </div>
    </div>

    <!-- Modal Share error  -->
</template>


<script setup>
import { defineProps, defineEmits, ref, reactive, onMounted, watch, nextTick } from 'vue'
import CustomSelect from './CustomSelect.vue'
import { API_GET_USER_ALL, API_CREATE_FILE_SHARE } from '../api/paths'
import { getCsrfToken } from '../api/csrf'
import '../assets/css/modal-favorite.css'
import { showToast, confirmDelete, notify } from '../assets/js/function-all'
import { useAuthStore } from '../stores/auth.store'

const Store = useAuthStore()

const props = defineProps({ modelValue: { type: Boolean, default: false }, files: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue', 'share'])

const selectionType = ref(
    Store.hasPermission('Create Delegate File') ? 'user' : Store.hasPermission('Create Ticket') ? 'ticket' : ''
)

const shareUser = ref('')
const userOptions = ref([])
const permissions = ref('false')
// fetch users to populate select
const fetchUsers = async () => {
    try {
        const params = new URLSearchParams()
        params.set('draw', 1)
        params.set('start', 0)
        params.set('length', 1000)
        const res = await fetch(`${API_GET_USER_ALL('user')}?${params.toString()}`, { credentials: 'include' })
        if (!res.ok) throw new Error('Failed to fetch users')
        const json = await res.json()
        const list = json.data || []
        const opts = []
        for (const p of list) {
            const u = p.user ? p.user : p
            const uname = u?.username || ''
            const fullname = `${u?.first_name || ''} ${u?.last_name || ''}`.trim()
            const label = fullname ? `${uname} (${fullname})` : uname
            opts.push({ label, value: uname })
        }
        userOptions.value = opts
    } catch (e) {
        console.error('ModalFileShare fetchUsers error', e)
    }
}
const emailTicket = ref('')
const start = ref('')
const expire = ref('')
const descTicket = ref('')
const limitAccessTimes = ref(null)

// flatpickr target object — directive will write into `picker.from` / `picker.to`
const picker = reactive({ from: '', to: '' })

// validation/errors for start/expire
const errors = reactive({ start: false, expire: false })
// template refs for the picker inputs (if directive exposes them)
const fromInput = ref(null)
const fromInputAdd = ref(null)
const toInputAdd = ref(null)

// keep `start`/`expire` in sync with picker object written by v-flatpickr
watch(() => picker.from, (v) => { start.value = v })
watch(() => picker.to, (v) => { expire.value = v })

// When selection type changes, disable or enable the limit input and set defaults
watch(() => selectionType.value, (v) => {
    if (v === 'user') {
        limitAccessTimes.value = null
    } else {
        if (limitAccessTimes.value === null) limitAccessTimes.value = null
    }
})

// Clamp limitAccessTimes to allowed range (allow null for disabled/user, allow 0 as default meaning 'no limit')
watch(() => limitAccessTimes.value, (v) => {
    if (v === null) return
    const n = parseInt(v, 10)
    if (isNaN(n)) {
        limitAccessTimes.value = 0
        return
    }
    if (n < 0) limitAccessTimes.value = 0
    else if (n > 99) limitAccessTimes.value = 99
    else if (n !== v) limitAccessTimes.value = n
})

const showResult = ref(false)
const resultType = ref('')
const resultData = ref({})

async function genTicketCode() {
    try {
        const res = await fetch('/api/file-share/generate-ticket/', { credentials: 'include' })
        if (!res.ok) throw new Error('Failed to get ticket code')
        const j = await res.json()
        if (j && j.ok && j.ticketCode) return j.ticketCode
        throw new Error(j && j.error ? j.error : 'Invalid response')
    } catch (e) {
        console.error('genTicketCode error', e)
        // fallback to local generation if server fails
        const n = Math.floor(Math.random() * 900000) + 100000
        return `TKT-${n}`
    }
}

function genPassword() {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    let out = ''
    for (let i = 0; i < 6; i++) out += chars[Math.floor(Math.random() * chars.length)]
    return out
}

function close() { emit('update:modelValue', false) }

function resetForm() {
    selectionType.value = 'user'
    shareUser.value = ''
    emailTicket.value = ''
    descTicket.value = ''
    limitAccessTimes.value = null
    permissions.value = 'false'
    start.value = ''
    expire.value = ''
    errors.start = false
    errors.expire = false
    picker.from = ''
    picker.to = ''

    // clear visual input and flatpickr instance if present
    try {
        if (fromInput && fromInput.value) {
            try { fromInput.value.value = '' } catch (e) {}
            const inst = fromInput.value._flatpickrRangeInstance || fromInput.value._flatpickrInstance || fromInput.value._flatpickr
            try {
                if (inst && typeof inst.clear === 'function') inst.clear()
                else if (inst && typeof inst.setDate === 'function') inst.setDate([], true)
            } catch (e) {}
        }
    } catch (e) {}
}

async function onCreate() {
    const targetValue = selectionType.value === 'user' ? shareUser.value : emailTicket.value
    const limitAccessTimesValue = (limitAccessTimes.value === null || limitAccessTimes.value === '') ? null : parseInt(limitAccessTimes.value, 10)

    console.log('ModalFileShare onCreate start', {limitAccessTimes: limitAccessTimesValue,selectionType: selectionType.value, target: targetValue, start: start.value, expire: expire.value, files: props.files && props.files.length })

    if (selectionType.value === 'user' && !targetValue) {
        showToast('Please specify a target.', 'warning')
        return
    }

    if (selectionType.value === 'ticket') {
        if (!targetValue) {
            showToast('Please specify an email for the ticket.', 'warning')
            return
        }
        // check for multiple emails (comma, semicolon, space, newline)
        if (/[,;\s\n\r]/.test(targetValue.trim())) {
            showToast('Only one email is allowed.', 'warning')
            return
        }
    }

    if (!start.value || !expire.value) {
        errors.start = !start.value
        errors.expire = !expire.value
        showToast('Please select a valid From and To date.', 'warning')
        return
    }

    const validStartRaw = start.value
    const validExpireRaw = expire.value

    let tCode = ''
    let tPass = ''

    // If ticket flow, attempt loop: get server ticket code, try create; retry on 409 (collision)
    const MAX_TRIES = 5
    let attempt = 0
    let created = false
    let lastError = null

    while (attempt < MAX_TRIES && !created) {
        attempt += 1

        if (selectionType.value === 'ticket') {
            tCode = await genTicketCode()
            tPass = genPassword()
        }

        const payload = {
            files: props.files,
            type: selectionType.value,
            target: targetValue,
            start: validStartRaw,
            expire: validExpireRaw,
            ticketCode: tCode,
            password: tPass,
            download: permissions.value === 'true',
            limitAccessTimes: (limitAccessTimes.value === null || limitAccessTimes.value === '') ? null : parseInt(limitAccessTimes.value, 10),
            description: descTicket.value 
        }

        try {
            const res = await fetch(API_CREATE_FILE_SHARE(), {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() || ''
                },
                body: JSON.stringify(payload)
            })

            const json = await res.json().catch(() => ({}))

            if (res.ok && json.ok) {
                // success — use server-confirmed ticketCode if provided
                if (selectionType.value === 'ticket') {
                    resultType.value = 'ticket'
                    resultData.value = {
                        recipient: emailTicket.value,
                        ticketCode: json.ticketCode || tCode,
                        password: tPass,
                        validStart: formatDateOnly(validStartRaw),
                        validExpire: formatDateOnly(validExpireRaw),
                        limitAccessTimes: limitAccessTimesValue,

                    }
                } else {
                    resultType.value = 'user'
                    resultData.value = {
                        recipient: shareUser.value,
                        validStart: formatDateOnly(validStartRaw),
                        validExpire: formatDateOnly(validExpireRaw)
                    }
                }

                emit('share', payload)
                emit('update:modelValue', false)
                showResult.value = true
                created = true
                break
            } else if (res.status === 409) {
                // collision — retry (frontend will get a fresh code next loop)
                lastError = json.message || 'Ticket code collision, retrying'
                continue
            } else {
                showToast(json.message || 'Failed to share files', 'error')
                lastError = json.message || 'Failed to share files'
                break
            }
        } catch (e) {
            console.error('onCreate share error', e)
            lastError = e.message || String(e)
            break
        }
    }

    if (!created) {
        showToast(lastError || 'Failed to create ticket after retries', 'error')
    }
}

function closeResult() {
    showResult.value = false
}

async function sendResultByEmail() {
    try {
        // prefer explicit email input if user still has it
        const source = emailTicket.value || resultData.value.recipient || ''
        const recipient = source.trim()
        if (!recipient) {
            await notify('Failed to send email', 'No recipient specified', 'error')
            return closeResult()
        }
        const recipients = [recipient]

        const payload = {
            recipient: recipients,
            subject: resultType.value === 'ticket' ? `Ticket ${resultData.value.ticketCode}` : 'Files shared with you',
            body: `Ticket: ${resultData.value.ticketCode || ''}\nPassword: ${resultData.value.password || ''}\nValid: ${resultData.value.validStart || ''} - ${resultData.value.validExpire || ''}\n\nFiles: ${(props.files || []).map(f => f.file_name || f.fileName || f.file || '').join(', ')}`
        }
            // prefer HTML content from the rendered card if present
            try {
                const card = document.querySelector('#fileShareResult .card-detail-to') || document.querySelector('.card-detail-to')
                if (card) payload.html = card.outerHTML
            } catch (e) {}

            const res = await fetch('/api/send-share-email/', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() || '' },
            body: JSON.stringify(payload)
        })
        const j = await res.json().catch(() => ({}))
        if (res.ok && j.ok) {
            await notify('Success!', 'Email sent successfully.', 'success')
            closeResult()
        } else {
            await notify('Failed to send email', 'Email not found', 'error')
            closeResult()
        }
    } catch (e) {
        console.error('sendResultByEmail error', e)
        await notify('Failed to send email', e.message, 'error')
        closeResult()
    }
}

async function copyCardContent() {
    try {
        // Prefer the ticket card, fallback to generic card
        const card = document.querySelector('#fileShareResult .card-detail-to') || document.querySelector('.card-detail-to') || document.querySelector('#fileShareResult .card') || document.querySelector('.card')
        if (!card) {
            await notify('No content', 'No card content to copy', 'error')
            return
        }

        const text = card.innerText.trim()
        if (!text) {
            await notify('No content', 'Card is empty', 'error')
            return
        }

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

        await notify('Copied', 'Form copied to clipboard', 'success')
    } catch (e) {
        console.error('copyCardContent error', e)
        await notify('Failed to copy', e.message || String(e), 'error')
    }
}

onMounted(() => {
        fetchUsers()
})

// initialize period when modal opens (component may be mounted while modal closed)
watch(() => props.modelValue, async (open) => {
    if (!open) return
    const pad = (n) => String(n).padStart(2, '0')
    // Do not prefill the input display — leave empty until user selects a date.
    const d = new Date()
    const today = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`
    start.value = ''
    expire.value = ''
    errors.start = false
    errors.expire = false
    picker.from = ''
    picker.to = ''

    // wait for DOM/ directive to mount the flatpickr instance (mirrors Home.vue pattern)
    try {
        await nextTick()
            if (fromInput && fromInput.value) {
            // ensure input displays the text
            try { fromInput.value.value = '' } catch (e) {}
            // try known instance names used in project
            const inst = fromInput.value._flatpickrRangeInstance || fromInput.value._flatpickrInstance || fromInput.value._flatpickr
            // Do not programmatically set a date on open — keep input empty until user selects.
            if (inst && typeof inst.setDate === 'function') {
                try { /* intentionally left blank to avoid auto-populating the input */ } catch (e) {}
            }
        }
    } catch (e) {}
})


function formatDate(v) {
    if (!v) return ''
    const d = new Date(v)
    if (isNaN(d.getTime())) return v
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Return date only (YYYY-MM-DD)
function formatDateOnly(v) {
    if (!v) return ''
    if (typeof v === 'string') {
        // if backend format 'YYYY-MM-DD HH:MM(:SS)?' or flatpickr 'YYYY-MM-DD'
        // Preserve time when present and normalize to include seconds.
        const parts = v.split(' ')
        if (parts.length > 1 && parts[0] && parts[0].includes('-')) {
            const datePart = parts[0]
            let timePart = parts.slice(1).join(' ')
            timePart = timePart.split('.')[0].replace(/Z$/, '')
            if (/^\d{1,2}:\d{2}$/.test(timePart)) timePart = `${timePart}:00`
            const m = timePart.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?/) || []
            if (m.length) {
                const pad = (n) => String(n).padStart(2, '0')
                const hh = pad(parseInt(m[1] || '0', 10))
                const mm = pad(parseInt(m[2] || '0', 10))
                const ss = pad(parseInt(m[3] || '0', 10))
                return `${datePart} ${hh}:${mm}:${ss}`
            }
            return `${datePart} ${timePart}`
        }
        // ISO-like with T separator
        if (v.includes('T')) {
            const date = v.split('T')[0]
            let time = (v.split('T')[1] || '').split('Z')[0].split('.')[0]
            if (/^\d{2}:\d{2}$/.test(time)) time = `${time}:00`
            if (time) return `${date} ${time}`
            if (date && date.includes('-')) return date
        }
        // fallback: plain date string
        if (v.includes('-')) return v
    }
    const d = new Date(v)
    if (isNaN(d.getTime())) return v
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function truncateFileName(s) { if (!s) return ''; return s.length > 100 ? s.slice(0, 57) + '...' : s }
</script>
<style scoped>
.custom-role-item {
    padding: 8px 20px;
    margin-bottom: 0px;
}

.input-disabled {
    background: #f3f4f6 !important;
    opacity: 0.7;
    cursor: not-allowed;
}

.group-card-title,
.form-label {
    font-size: 10px;
}

.group-card-desc {
    font-size: 8px;
}

.detail-file-share {
    margin-bottom: 4px;
}

strong {
    font-weight: 500;
}

.strong-title {
    margin-right: 4px;
    font-weight: 500;
}

.btn-file-share {
    display: flex !important;
    flex-direction: row !important;
    gap: 8px;
    padding: 12px 16px;
}

.btn-role {
    border-radius: 25px;
}

.btn-file-share .btn-role {
    flex: 1 1 0;
    min-width: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

</style>