<template>
  <div class="login-root" style="background-color: #F9FAFB;">
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
  passwordVisible,
  form,
  handleLogin
} = useLogin()
</script>

<style scoped src="../assets/css/login.css"></style>
