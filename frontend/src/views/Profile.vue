<template>
    <MainLayout>
        <div class="main-wrapper container-fluid-home py-3">
            <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: 'Profile' }]" />

            <div class="row col-lg-12">
                <div class="col-lg-12">
                    <div class="card">
                        <div class="card-body" style="height: calc(100vh - 158px);">
                            <!-- Header -->
                            <div class="d-flex align-items-center" style="margin-bottom: 20px;">
                                <div class="d-flex align-items-center justify-content-center me-1"
                                    style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                    <i class="fa-solid fa-circle-user" style="color:#2b6cb0;font-size:18px"></i>
                                </div>
                                <h5 class="card-title mb-2 mt-1">Profile</h5>
                            </div>

                            <!-- Tabs -->
                            <ul class="nav nav-tabs mb-4">
                                <li class="nav-item">
                                    <a class="nav-link" :class="{ active: activeTab === 'personal' }" href="#" @click.prevent="activeTab = 'personal'">Personal info</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" :class="{ active: activeTab === 'password' }" href="#" @click.prevent="activeTab = 'password'">Password</a>
                                </li>
                            </ul>

                            <!-- Tab Content -->
                            <div class="tab-content">
                                <!-- Personal Info -->
                                <div v-if="activeTab === 'personal'" class="tab-pane fade show active">
                                    <div v-if="loading" class="text-center py-4">Loading...</div>
                                    <div v-else class="profile-info ps-2">
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Username</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.username }}</div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Full Name</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.first_name }} {{ userProfile.last_name }}</div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Email</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.email || '-' }}</div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Phone</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.phone || '-' }}</div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Role</div>
                                            <div class="col-md-11 text-profile-info">
                                                <span :class="['role-badge', (['administrator', 'auditor', 'operator'].includes((userProfile.role || '').toLowerCase()) ? (userProfile.role || '').toLowerCase() : 'other')]">
                                                  {{ userProfile.role || '-' }}
                                                </span>
                                            </div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Group</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.group_name || '-' }} </div> 
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Team</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.team_name || '-' }} </div>
                                        </div>
                                        <div class="row mb-3">
                                            <div class="col-md-1 fw-bold text-secondary">Database Server</div>
                                            <div class="col-md-11 text-profile-info">{{ userProfile.db_name || '-' }}</div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Password -->
                                <div v-if="activeTab === 'password'" class="tab-pane fade show active">
                                    <form @submit.prevent="submitPasswordChange" class="col-md-4 ps-2">
                                        <div class="input-group mb-3" v-has-value>
                                            <input :type="showOldPass ? 'text' : 'password'" v-model="passwordForm.old_password" class="input" required>
                                            <button type="button" class="toggle-visibility" @click="showOldPass = !showOldPass">
                                                <i :class="showOldPass ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
                                            </button>
                                            <label class="title-label">Old Password</label>
                                        </div>
                                        <div class="input-group mb-3" v-has-value>
                                            <input :type="showNewPass ? 'text' : 'password'" v-model="passwordForm.new_password" class="input" required minlength="8">
                                            <button type="button" class="toggle-visibility" @click="showNewPass = !showNewPass">
                                                <i :class="showNewPass ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
                                            </button>
                                            <label class="title-label">New Password</label>
                                            <div v-show="errors.password" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ typeof errors.password === 'string' ? errors.password : '' }}</div>
                                        </div>
                                        <div class="input-group mb-3" v-has-value>
                                            <input :type="showConfirmPass ? 'text' : 'password'" v-model="passwordForm.confirm_password" class="input" required>
                                            <button type="button" class="toggle-visibility" @click="showConfirmPass = !showConfirmPass">
                                                <i :class="showConfirmPass ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
                                            </button>
                                            <label class="title-label">Confirm New Password</label>
                                            <div v-if="passwordError" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ passwordError }}</div>
                                        </div>
                                        <button class="btn btn-primary" type="submit" :disabled="submitting || hasError" style="font-size: 10px;">
                                                <i class="fas fa-save"></i>
                                            Save Changes
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
</template>

<script setup>
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useProfile } from '../composables/useProfile'

const {
    authStore,
    activeTab,
    loading,
    submitting,
    userProfile,
    passwordForm,
    passwordError,
    showOldPass,
    showNewPass,
    showConfirmPass,
    errors,
    hasError,
    fetchProfile,
    submitPasswordChange
} = useProfile()
</script>

<style scoped src="../assets/css/profile.css"></style>