<template>
        <div v-if="modelValue" class="modal-backdrop" @click.self="closeResult" id="fileShareResult">
        <div class="modal-box" style="max-width: 400px;">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 8px">
                    <div class="green-icon"><i class="fa-solid fa-ticket"></i></div>
                    <h3 class="modal-title ad" v-if="resultType === 'ticket'">Ticket Resend</h3>
                    <h3 class="modal-title ad" v-else>File shared successfully!</h3>
                </div>
                <button type="button" class="btn-close" @click="closeResult"></button>
            </div>

            <div class="modal-body">
                <div v-if="resultType === 'ticket'">
                    <div style="text-align:center; margin-bottom:12px;">
                        <i class="fa-solid fa-envelope" style="color:#10b981;margin-bottom: 15px;font-size: 45px;"></i>
                        <p style="margin:0">Ticket <strong style="color:#2563eb">{{ resultData.code }}</strong> created Resend successfully!</p>
                    </div>

                    <div class="card card-detail-to" style="padding:16px; border:1px solid #e6eef8;">
                        <p style="margin:0 0 8px 0">Dear Sir,</p>
                        <p style="margin:0 0 12px 0">An access ticket has been created for you to listen to specific audio records on SeekTrack.</p>
                        <div style="border:1px dashed #e6eef8; padding:12px; margin-bottom:12px;">
                            <div class="detail-file-share"><strong class="strong-title">Ticket Code:</strong> <span style="color:#2563eb">{{ resultData.code }}</span></div>
                            <div class="detail-file-share"><strong class="strong-title">Password:</strong> <code style="background:#f3f4f6; padding:4px 8px; border-radius:4px">{{ resultData.password }}</code>
                            </div>
                            <div class="detail-file-share"><strong class="strong-title">Valid Start:</strong> {{ resultData.start_at }}</div>
                            <div class="detail-file-share"><strong class="strong-title">Valid Expire:</strong> {{ resultData.expire_at }}</div>
                        </div>
                        <p style="margin:0 0 8px 0">Please visit our portal to login using the credentials above.</p>
                        <div style="margin-bottom:12px;"><a href="/login">https://192.168.1.95/login</a></div>
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

</template>

<script setup>
import { defineProps, defineEmits, ref } from 'vue'
import { API_SEND_EMAIL } from '../api/paths'
import { getCsrfToken } from '../api/csrf'
import '../assets/css/modal-favorite.css'
import { showToast, notify } from '../assets/js/function-all'

const props = defineProps({
    modelValue: { type: Boolean, default: false },
    resultType: { type: String, default: '' },
    resultData: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['update:modelValue'])

function closeResult() {
    emit('update:modelValue', false)
}

async function copyCardContent() {
    try {
        const d = props.resultData || {}
        const text = `Ticket Code: ${d.code || ''}\nPassword: ${d.password || ''}\nValid Start: ${d.start_at || ''}\nValid Expire: ${d.expire_at || ''}`
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text)
            showToast('Copied to clipboard', 'success')
        } else {
            // fallback
            const ta = document.createElement('textarea')
            ta.value = text
            document.body.appendChild(ta)
            ta.select()
            document.execCommand('copy')
            document.body.removeChild(ta)
            showToast('Copied to clipboard', 'success')
        }
    } catch (e) {
        console.error('copyCardContent error', e)
        showToast('Copy failed', 'error')
    }
}

async function sendResultByEmail() {
    try {
        const d = props.resultData || {}
        // derive recipients: prefer explicit recipient field and normalize formats
        const source = d.recipient || d.email || ''
        function normalizeRecipients(src) {
            if (!src) return []
            // join arrays into a single string so we can uniformly split
            let combined
            if (Array.isArray(src)) {
                combined = src.join(',')
            } else if (typeof src === 'object') {
                try {
                    combined = JSON.stringify(src)
                } catch (e) {
                    combined = String(src)
                }
            } else {
                combined = String(src)
            }

            // remove surrounding braces/brackets
            combined = combined.replace(/^[\{\[]+|[\}\]]+$/g, '')

            // split on commas, semicolons or newlines and trim quotes/spaces
            return combined.split(/[,;\n\r]+/)
                .map(s => s.trim().replace(/^"+|"+$/g, '').replace(/^'+|'+$/g, '').trim())
                .filter(Boolean)
        }

        const recipients = normalizeRecipients(source)
        if (!recipients.length) {
            await notify('Failed to send email', 'No recipient specified', 'error')
            return closeResult()
        }

        const payload = {
            recipient: recipients,
            subject: `Ticket ${d.code || ''}`,
            body: `Ticket: ${d.code || ''}\nPassword: ${d.password || ''}\nValid: ${d.start_at || ''} - ${d.expire_at || ''}`
        }
        // try include rendered card HTML
        try {
            const card = document.querySelector('#fileShareResult .card-detail-to') || document.querySelector('.card-detail-to')
            if (card) payload.html = card.outerHTML
        } catch (e) {}

        const csrf = getCsrfToken()
        const res = await fetch(API_SEND_EMAIL(), {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf || '' },
            body: JSON.stringify(payload)
        })
        const json = await res.json().catch(() => ({}))
        if (res.ok && json.ok) {
            await notify('Success!', 'Email sent successfully.', 'success')
            closeResult()
        } else {
            await notify('Failed to send email', json.message || 'Email not found', 'error')
            closeResult()
        }
    } catch (e) {
        console.error('sendResultByEmail error', e)
        await notify('Failed to send email', e.message || String(e), 'error')
        closeResult()
    }
}
</script>
<style scoped>
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

