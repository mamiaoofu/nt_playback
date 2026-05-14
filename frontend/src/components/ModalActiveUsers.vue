<template>
    <div v-if="modelValue" class="modal-backdrop" @click.self="close" id="activeUsersModal">
        <div class="modal-box" style="max-width: 800px;">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 4px">
                    <div class="blue-icon" id="activeUsersModalIcon">
                        <i class="fa-solid fa-users"></i>
                    </div>
                    <h3 class="modal-title ad" id="activeUsersModalTitle">Active Sessions</h3>
                </div>
                <button type="button" class="btn-close" @click="close"></button>
            </div>
            <div class="modal-body">
                <div v-if="loading" class="loading-container">
                    <div class="loading-spinner"></div>
                    <p>Loading active sessions...</p>
                </div>
                <div v-else-if="users.length === 0" class="empty-state">
                    <i class="fa-solid fa-user-slash"></i>
                    <p>No active sessions found.</p>
                </div>
                <div v-else class="table-container">
                    <table class="table-template">
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>IP Address</th>
                                <th>Login Time</th>
                                <th class="text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="user in users" :key="user.id">
                                <td class="username-cell">
                                    <div class="user-avatar">
                                        {{ user.username.charAt(0).toUpperCase() }}
                                    </div>
                                    {{ user.username }}
                                </td>
                                <td><code>{{ user.ip_address }}</code></td>
                                <td>{{ user.login_time }}</td>
                                <td class="text-center">
                                    <button class="btn-kick-action" @click="onKick(user)" title="Kick Out">
                                        <i class="fa-solid fa-user-slash"></i>
                                        Kick
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-role btn-secondary" @click="close">
                    <i class="fas fa-times"></i>
                    Close
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'
import { API_DASHBOARD_ACTIVE_USERS, API_DASHBOARD_ACTION } from '../api/paths'
import { showToast } from '../assets/js/function-all'
import '../assets/js/sweetalert2@11.min.js'

export default {
    name: 'ModalActiveUsers',
    props: {
        modelValue: Boolean
    },
    emits: ['update:modelValue', 'refresh'],
    data() {
        return {
            users: [],
            loading: false
        }
    },
    watch: {
        modelValue(val) {
            if (val) {
                this.fetchActiveUsers()
            }
        }
    },
    methods: {
        async fetchActiveUsers() {
            this.loading = true
            try {
                const response = await axios.get(API_DASHBOARD_ACTIVE_USERS())
                this.users = response.data.users
            } catch (error) {
                console.error('Failed to fetch active users:', error)
            } finally {
                this.loading = false
            }
        },
        close() {
            this.$emit('update:modelValue', false)
        },
        async onKick(user) {
            const swal = window.Swal || window.Sweetalert2
            if (!swal) {
                if (!confirm(`Are you sure you want to kick out ${user.username}?`)) return
            } else {
                const result = await swal.fire({
                    title: 'Are you sure?',
                    text: `You are about to kick out ${user.username}. They will be logged out immediately.`,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#d33',
                    cancelButtonColor: '#3085d6',
                    confirmButtonText: 'Yes, kick them!',
                    background: 'var(--bg-card)',
                    color: 'var(--text-primary)'
                })
                if (!result.isConfirmed) return
            }

            try {
                await axios.post(API_DASHBOARD_ACTION(), {
                    action: 'kick_out',
                    user_id: user.id
                })
                showToast(`${user.username} has been kicked out.`, 'success')
                this.fetchActiveUsers()
                this.$emit('refresh')
            } catch (error) {
                showToast('Failed to kick out user.', 'error')
            }
        }
    }
}
</script>

<style scoped>
.loading-container, .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--text-secondary);
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(0, 123, 255, 0.1);
    border-top: 3px solid var(--blue-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.empty-state i {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
}

.table-container {
    max-height: 400px;
    overflow-y: auto;
}

.username-cell {
    display: flex;
    align-items: center;
    gap: 12px;
}

.user-avatar {
    width: 32px;
    height: 32px;
    background: var(--blue-color-gradient);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 14px;
}

.btn-kick-action {
    background: rgba(220, 53, 69, 0.1);
    color: #dc3545;
    border: 1px solid rgba(220, 53, 69, 0.2);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
    cursor: pointer;
}

.btn-kick-action:hover {
    background: #dc3545;
    color: white;
}

code {
    background: rgba(0, 0, 0, 0.05);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
}
</style>
