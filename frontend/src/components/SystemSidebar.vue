<template>
  <nav class="system-sidebar" :class="{ 'expanded': isExpanded }" aria-label="System tools sidebar">
    
    <!-- Collapsed View Toggle -->
    <div v-if="!isExpanded" class="collapsed-toggle">
      <button type="button" class="icon-link toggle-btn" @click="toggleSidebar" aria-label="Expand sidebar">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="2" y="4" width="8" height="16" rx="2" fill="currentColor" />
          <path d="M14 5H20C20.5523 5 21 5.44772 21 6V18C21 18.5523 20.5523 19 20 19H14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M7 9L10 9" stroke="white" stroke-width="2" stroke-linecap="round" />
          <path d="M7 15L10 15" stroke="white" stroke-width="2" stroke-linecap="round" />
        </svg>
      </button>
    </div>

    <!-- Expanded Header -->
    <div v-if="isExpanded" class="expanded-header">
      <span class="header-title">System tools</span>
      <button style="width: 40px;height: 40px;" type="button" class="icon-link toggle-btn shrink-btn" @click="toggleSidebar" aria-label="Collapse sidebar">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="transform: scaleX(-1);">
          <rect x="2" y="4" width="8" height="16" rx="2" fill="currentColor" />
          <path d="M14 5H20C20.5523 5 21 5.44772 21 6V18C21 18.5523 20.5523 19 20 19H14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M7 9L10 9" stroke="white" stroke-width="2" stroke-linecap="round" />
          <path d="M7 15L10 15" stroke="white" stroke-width="2" stroke-linecap="round" />
        </svg>
      </button>
    </div>

    <ul class="icons-list" :class="{ 'expanded-list': isExpanded }">
      <li class="icon-item" :class="{ 'expanded-item': isExpanded }">
      <router-link to="/system-tool/dashboard" class="icon-link">
          <i class="fa-solid fa-chart-line icon-part"></i>
          <span v-if="isExpanded" class="text-part">Dashboard</span>
        </router-link>
      </li>
      <li class="icon-item config-item" :class="{ 'expanded-item': isExpanded }">
        <div class="icon-link" :class="{ 'router-link-active': isConfigActive }" @click="toggleConfigMenu" style="cursor: pointer;">
          <i class="fa-solid fa-screwdriver-wrench icon-part"></i>
          <span v-if="isExpanded" class="text-part">Configuration</span>
          <i v-if="isExpanded" class="fa-solid fa-chevron-down toggle-icon" :class="{ 'rotated': isConfigExpanded }"></i>
        </div>
        <ul v-if="isExpanded && isConfigExpanded" class="sub-menu">
          <li>
            <router-link to="/system-tool/active-directory" class="sub-link">
              <span class="sub-text"><i class="fa-solid fa-circle-dot"></i> Active Directory</span>
            </router-link>
          </li>
          <li>
            <router-link to="/system-tool/network-share" class="sub-link">
              <span class="sub-text"><i class="fa-solid fa-circle-dot"></i> Network share</span>
            </router-link>
          </li>
          <li>
            <router-link to="/system-tool/mail-settings" class="sub-link">
              <span class="sub-text"><i class="fa-solid fa-circle-dot"></i> Mail settings</span>
            </router-link>
          </li>
          <li>
            <router-link to="/system-tool/nice-player" class="sub-link">
              <span class="sub-text"><i class="fa-solid fa-circle-dot"></i> Nice player</span>
            </router-link>
          </li>
        </ul>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const emit = defineEmits(['toggle']);
const isExpanded = ref(true);

const isConfigActive = computed(() => {
  const activePaths = [
    '/system-tool/active-directory',
    '/system-tool/network-share',
    '/system-tool/mail-settings',
    '/system-tool/nice-player'
  ];
  return activePaths.includes(route.path);
});

const isConfigExpanded = ref(isConfigActive.value);

import { watch } from 'vue';
watch(route, () => {
  if (isConfigActive.value && isExpanded.value) {
    isConfigExpanded.value = true;
  }
});

const toggleSidebar = () => {
  isExpanded.value = !isExpanded.value;
  if (!isExpanded.value) {
    isConfigExpanded.value = false;
  }
  emit('toggle', isExpanded.value);
};

const toggleConfigMenu = () => {
  if (!isExpanded.value) {
    isExpanded.value = true;
    emit('toggle', true);
    isConfigExpanded.value = true;
  } else {
    isConfigExpanded.value = !isConfigExpanded.value;
  }
};
</script>

<style scoped>
.system-sidebar {
  position: fixed;
  left: 0;
  top: 60px; /* assume Navbar height */
  bottom: 0;
  width: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #ffffff;
  border-right: 1px solid rgba(15,23,42,0.04);
  box-shadow: 0 1px 0 rgba(2,6,23,0.04);
  z-index: 1050;
  transition: width 0.18s ease;
  overflow: visible;
}

.system-sidebar.expanded {
  width: 240px;
  align-items: stretch;
}

.collapsed-toggle {
  width: 40px;
  height: 40px;
  margin: 16px 0 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
}

.expanded-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 16px 16px;
}

.header-title {
  font-weight: 600;
  color: #64748b;
  font-size: 20px;
}

.shrink-btn {
  /* width: 32px; */
  height: 32px;
  border-radius: 8px;
}

.icons-list { 
  list-style: none; 
  padding: 0; 
  margin: 0; 
  display: flex; 
  flex-direction: column; 
  gap: 8px; 
  align-items: center; 
  width: 100%;
}

.icons-list.expanded-list {
  align-items: stretch;
  padding: 0 12px;
}

.icon-item { 
  width: 40px; 
  height: 40px; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  border-radius: 10px; 
}

.icon-item.expanded-item {
  width: 100%;
}

.icon-link { 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  color: #64748b; 
  width: 100%; 
  height: 100%; 
  text-decoration: none;
}

.nav-link {
  justify-content: center;
}

.expanded-item .nav-link {
  justify-content: flex-start;
  padding: 0 12px;
}

.icon-part {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.expanded-item .icon-part {
  margin-right: 12px;
}

.text-part {
  font-size: 14px;
  font-weight: 500;
}

.icon-link:hover, .router-link-active { 
  color: #416FD6; 
  background: rgba(65,111,214,0.06); 
  border-radius: 10px;
}

.toggle-btn { 
  border: none; 
  background: none; 
  padding: 0; 
  cursor: pointer; 
}

.toggle-btn:focus { outline: none; }

@media (max-width: 768px) {
  .system-sidebar { display: none }
}

.expanded-item .icon-link {
  justify-content: flex-start;
  padding: 6px;
}

.config-item {
  flex-direction: column;
  height: auto;
  align-items: stretch;
}

.toggle-icon {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.2s ease;
}

.toggle-icon.rotated {
  transform: rotate(180deg);
}

.sub-menu {
  list-style: none;
  padding: 0 0 0 32px;
  margin: 4px 0 8px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sub-link {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  color: #64748b;
  text-decoration: none;
  border-radius: 8px;
  font-size: 13px;
  transition: all 0.15s ease;
}

.sub-link:hover, .sub-link.router-link-active {
  color: #416FD6;
  background: rgba(65,111,214,0.06);
}

.fa-circle-dot {
  font-size: 8px;
  color: #64748b;
  margin-right: 8px;
}
</style>
