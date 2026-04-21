<template>
  <div class="login-root" style="background-color: #F9FAFB;">

    <!-- Modal for License Error -->
    <div v-if="authStore.licenseError" class="modal-backdrop" style="z-index: 9999;">
        <div class="modal-box" style="max-width: 420px; padding: 24px; border-radius: 12px; background: #fff; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
            <div class="modal-header" style="border-bottom: none; padding-bottom: 0;">
                <div style="display: flex; align-items: center; gap: 8px">
                    <div class="blue-icon" style="background: #fee2e2; color: #dc2626;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <h3 class="modal-title ad" style="font-size: 18px; font-weight: bold;">License Error</h3>
                </div>
            </div>
            <div class="modal-body" style="padding-top: 12px;">
                <p style="font-size: 13px; margin-bottom: 20px; color: #64748b;">{{ authStore.licenseError }}</p>
                <button class="btn-submit" @click="authStore.licenseError = null" style="width: 100%; border-radius: 25px;">
                    <i class="fa-solid fa-xmark" style="margin-right: 6px;"></i>
                    Close
                </button>
            </div>
        </div>
    </div>

    <!-- Modal for Force Password Change -->
    <div v-if="authStore.passwordResetRequired" class="modal-backdrop" style="z-index: 9999;">
        <div class="modal-box" style="max-width: 400px; padding: 24px; border-radius: 12px; background: #fff; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
            <div class="modal-header" style="border-bottom: none; padding-bottom: 0;">
                <div style="display: flex; align-items: center; gap: 8px">
                    <div class="blue-icon" style="background: #fef08a; color: #b45309;"><i class="fa-solid fa-shield-halved"></i></div>
                    <h3 class="modal-title ad" style="font-size: 18px; font-weight: bold;">Change your password.</h3>
                </div>
            </div>
            <div class="modal-body" style="padding-top: 8px;">
                <p style="font-size: 13px; margin-bottom: 20px; color: #64748b;">Please set a new password for security.</p>
                
                <form @submit.prevent="submitPasswordChange" class="col-md-12">
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
                    <div class="input-group mb-4" v-has-value>
                        <input :type="showConfirmPass ? 'text' : 'password'" v-model="passwordForm.confirm_password" class="input" required>
                        <button type="button" class="toggle-visibility" @click="showConfirmPass = !showConfirmPass">
                            <i :class="showConfirmPass ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
                        </button>
                        <label class="title-label">Confirm New Password</label>
                        <div v-if="passwordError" class="validate"><i class="fa-solid fa-circle-exclamation"></i> {{ passwordError }}</div>
                    </div>
                    <button class="btn-submit" type="submit" :disabled="submitting || hasError" style="width: 100%; border-radius: 25px;">
                         <i class="fas fa-save" style="margin-right: 6px;"></i>
                         Save Changes
                     </button>
                </form>
            </div>
        </div>
    </div>

    <div class="login-card">

    <div class="login-header">
      <img src="/src/assets/images/logo-nichtel.png" alt="logo" class="logo" />
      <h1 class="app-title">SeekTrack</h1>
      <div class="app-sub">Centralized Search and Playback System</div>
    </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-left">
          <div class="input-group" style="margin-bottom: 12.2px;" v-has-value>
            <input v-model="form.username" required type="text" name="username" autocomplete="off" class="input"
              maxlength="30">
            <label class="title-label">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="#64748b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
                focusable="false">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>Username
            </label>
          </div>

          <div class="input-group" v-has-value>
            <input v-model="form.password" required :type="passwordVisible ? 'text' : 'password'" name="password"
              autocomplete="off" class="input" maxlength="30">
            <button type="button" class="toggle-visibility" @click="passwordVisible = !passwordVisible"
              aria-label="Toggle password visibility">
              <i :class="passwordVisible ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
            </button>
            <label class="title-label">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="#64748b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
                focusable="false">
                <rect x="3" y="11" width="18" height="10" rx="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>Password
            </label>
          </div>

          <div class="checkbox-left">
            <input type="checkbox" id="remember" v-model="form.rememberMe" />
            <label for="remember">Remember</label>
          </div>
        </div>

        <div class="form-bottom">
          <button type="submit" class="btn-submit"><i class="fa-solid fa-arrow-right-to-bracket"></i> Login</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { useLogin } from '../composables/useLogin'

const {
  authStore,
  passwordVisible,
  form,
  handleLogin,
  submitting,
  passwordForm,
  passwordError,
  showOldPass,
  showNewPass,
  showConfirmPass,
  errors,
  hasError,
  submitPasswordChange
} = useLogin()
</script>

<style scoped src="../assets/css/login.css"></style>
