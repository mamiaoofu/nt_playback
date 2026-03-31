<template>
  <div class="page-title text-primary-d2 text-140" style="font-size: 12px; margin-bottom: 12px">
    <template v-for="(crumb, idx) in items" :key="idx">
      <small v-if="idx === 0" class="crumb" :class="{ active: idx === activeIndex }">
        <router-link :to="crumb.to || '/'" class="no-link">
          <i class="fa-solid fa-house crumb-icon" :class="{ active: idx === activeIndex }"></i>
          {{ crumb.text }}
        </router-link>
      </small>

      <small v-else-if="crumb.to" class="crumb" :class="{ active: idx === activeIndex }">
        <router-link :to="crumb.to" class="no-link">
          <i class="fa-solid fa-angle-right crumb-icon" :class="{ active: idx === activeIndex }"></i>
          {{ crumb.text }}
        </router-link>
      </small>

      <small v-else class="page-info text-dark-m3" :class="{ active: idx === activeIndex }">
        <i class="fa-solid fa-angle-right crumb-icon" :class="{ active: idx === activeIndex }"></i>
        {{ crumb.text }}
      </small>
    </template>
  </div>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [{ text: 'Home', to: '/' }]
  }
})

const items = props.items
const activeIndex = computed(() => Math.max(0, (items && items.length ? items.length - 1 : 0)))
</script>

<style scoped>
.no-link { text-decoration: none; color: inherit }

/* Breadcrumb color tokens (use CSS variables so dark-mode can override) */
.crumb {
  margin-right: -4px;
  color: var(--breadcrumb-inactive-color, #6c757d);
  font-size: 12px;
}
.crumb.active {
  color: var(--breadcrumb-active-color, #416FD6);
}
.crumb .crumb-icon,
.page-info .crumb-icon {
  color: inherit;
}
.page-info {
  color: var(--breadcrumb-inactive-color, #6c757d);
}
.page-info.active {
  color: var(--breadcrumb-active-color, #416FD6);
}
</style>
