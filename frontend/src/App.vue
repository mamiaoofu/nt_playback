<template>
  <router-view :key="route.fullPath" />
</template>

<script setup>
import { useRoute } from 'vue-router'
import { initNotifications } from './composables/useNotifications'
import { useAuthStore } from './stores/auth.store'

const route = useRoute()
const auth = useAuthStore()

// Kick off restore immediately so the router beforeEach guard can await waitReady().
// Fire-and-forget — the store's _readyPromise will resolve when it finishes.
auth.tryRestoreFromRefresh().catch(() => {})

// initialize global notifications (reconnects automatically)
initNotifications()
</script>
