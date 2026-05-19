<template>
  <div class="page-title text-primary-d2 text-140" style="font-size: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
    <div>
      <template v-for="(crumb, idx) in items" :key="idx">
        <small v-if="idx === 0" :style="{ color: idx === activeIndex ? '#416FD6' : '#6c757d', marginRight: '1px' }">
          <router-link :to="crumb.to || '/'" class="no-link"><i class="fa-solid fa-house" :style="{ color: idx === activeIndex ? '#416FD6' : '#6c757d' }"></i> {{ crumb.text }}</router-link>
        </small>

        <small v-else-if="crumb.to" :style="{ color: idx === activeIndex ? '#416FD6' : '#6c757d', marginRight: '1px' }">
          <router-link :to="crumb.to" class="no-link"><i class="fa-solid fa-angle-right" :style="{ color: idx === activeIndex ? '#416FD6' : '#6c757d' }"></i> {{ crumb.text }}</router-link>
        </small>

        <small v-else :style="{ color: idx === activeIndex ? '#416FD6' : '#6c757d' }" class="page-info text-dark-m3"> <i class="fa-solid fa-angle-right" :style="{ color: idx === activeIndex ? '#416FD6' : '#6c757d' }"></i> {{ crumb.text }}</small>
      </template>
    </div>

    <div v-if="isSuperadmin">
      <router-link to="/system-tool/dashboard" class="no-link">
        <i class="fa-solid fa-gear breadcrumb-gear"></i>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { defineProps, computed } from 'vue'
import { useAuthStore } from '../stores/auth.store'

const props = defineProps({
  items: {
    type: Array,
    default: () => [{ text: 'Home', to: '/' }]
  }
})

const authStore = useAuthStore()
const items = props.items
const activeIndex = computed(() => Math.max(0, (items && items.length ? items.length - 1 : 0)))
const isSuperadmin = computed(() => !!authStore.user?.is_superuser)
</script>

<style scoped>
.no-link { text-decoration: none; color: inherit }
.breadcrumb-gear {
  font-size: 14px;
  color: #6c757d;
  cursor: pointer;
}
.breadcrumb-gear:hover {
  color: #416FD6;
}
</style>
