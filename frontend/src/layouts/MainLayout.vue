<template>
  <div class="layout-wrapper">
    
    <div id="pageload-overlay" v-show="pageLoading">
      <div class="pageload-spinner">
        <div class="spinner-ring">
          <img src="/src/assets/images/logo-nichtel.png" alt="Loading..." />
        </div>
      </div>
    </div>

    <Navbar />
    
    <main class="main-content">
      <slot />
    </main>

    <footer class="footer">
      <div class="container-fluid text-center justify-content-center">
        <span class="text-muted">© 2026 NICHETEL SEEKTRACK PLAN ( Centralize Search & Playback )</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import Navbar from '../components/Navbar.vue'
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { whenIdle } from '../utils/pageLoad'

const pageLoading = ref(true)

onMounted(() => {
  const waitForWindowLoad = new Promise((resolve) => {
    if (document.readyState === 'complete') return resolve()
    window.addEventListener('load', resolve, { once: true })
  })

  // Wait for both window load (assets) and any registered API requests,
  // but ensure the overlay is visible for at least 1 second.
  const minDelay = new Promise((resolve) => setTimeout(resolve, 1000))
  Promise.all([waitForWindowLoad, whenIdle(), minDelay]).then(() => {
    pageLoading.value = false
  }).catch(() => {
    pageLoading.value = false
  })
})

onBeforeUnmount(() => {})
</script>

<style scoped>
/* Page load overlay styles */
#pageload-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  z-index: 9999;
  transition: opacity 0.25s ease;
}

.pageload-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner-ring {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  border: 8px solid #e5e7eb; /* gray-300 */
  border-top-color: #3b82f6; /* blue-500 */
  animation: spin 1s linear infinite;
  position: relative;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Ensure main content is below overlay visually */
.layout-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1 1 auto;
}

/* Small-screen tweak */
@media (max-width: 576px) {
  .spinner-ring { width: 64px; height: 64px; border-width: 6px }
}

.spinner-ring img {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 56%;
  height: 56%;
  max-width: 56%;
  max-height: 56%;
  object-fit: contain;
  pointer-events: none;
  /* keep the logo visually still while ring rotates */
  animation: none;
}
</style>
