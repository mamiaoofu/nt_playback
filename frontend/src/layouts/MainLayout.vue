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

    <SystemSidebar v-if="showSystemSidebar" @toggle="onSidebarToggle" />

    <main :class="['main-content', { 'with-system-sidebar': showSystemSidebar, 'system-sidebar-expanded': isSidebarExpanded }]">
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
import SystemSidebar from '../components/SystemSidebar.vue'
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'
import { whenIdle } from '../utils/pageLoad'

const pageLoading = ref(true)
const route = useRoute()
const isSidebarExpanded = ref(true)

const onSidebarToggle = (expanded) => {
  isSidebarExpanded.value = expanded
}
const showSystemSidebar = computed(() => {
  try {
    return (route && route.path && String(route.path).startsWith('/system-tool'))
  } catch (e) { return false }
})

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
  transition: padding-left 0.18s ease;
}

.main-content.with-system-sidebar { padding: 58px 8px 0px 56px; }
.main-content.with-system-sidebar.system-sidebar-expanded { padding-left: 240px; }

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
