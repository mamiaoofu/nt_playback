<template>
  <header>
    <nav class="navbar navbar-expand-sm navbar-toggleable-sm navbar-light navbar-custom mb-3 fixed-top">
      <div class="container-navbar">
        <div class="d-flex justify-content-between align-items-center">
          <div class="site-title-container">
            <span>
              <a aria-current="page" href="/" class="router-link-active router-link-exact-active no-link"
                style="text-decoration: none; display: inline-flex; align-items: center">
                <img src="/src/assets/images/logo-nichtel.png" class="img-fluid rounded" alt="Nichetel-logo" style="width: 40px; height: auto; margin-right: 10px" />
                <div style="display: flex; flex-direction: column; line-height: 1.2; margin: 9px 0px 10px -5px;">
                  <span style="font-size: 18px; color: #fff;font-weight: 600;">SeekTrack</span>
                  <span style="font-size: 12px; color: #fff">Centralized Search and Playback System</span>
                </div>
              </a>
            </span>
          </div>
        </div>

        <div class="navbar-collapse collapse d-none d-sm-inline-flex justify-content-end">
          <ul class="navbar-nav" id="sidebarTeamToggle" ref="sidebarToggle" @click="toggleMenu">
            <li style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #fff">
              <div class="team-toggle">
                {{ initials }}
              </div>
              <span class="user-nav-name">{{ displayName }}</span>
              <i class="fa-solid fa-angle-down" style="font-size: 12px;"></i>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Breadcrumbs removed from Navbar — pages render breadcrumbs via `Breadcrumbs` component -->

    <!-- Sidebar Menu -->
    <div class="sidebar-team-menu" id="sidebarTeamMenu" ref="sidebarMenu" :style="{ display: menuOpen ? 'block' : 'none' }">
      <!-- Header -->
        <div class="menu-header">
        <div class="user-info-group" :class="{ 'disabled-profile': store.isTicket && store.isTicket() }" @click="goToProfile">
          <div class="menu-avatar">
            {{ initials }}
          </div>
          <div class="menu-user-details">
            <div class="menu-user-name">{{ displayName }}</div>
            <div class="menu-user-role">{{ roleName }}</div>
          </div>
        </div>
        <label class="switch">
          <input type="checkbox" id="themeSwitch" />
          <span class="slider round">
            <i class="fa-regular fa-moon icon-moon"></i>
            <span class="knob" aria-hidden="true">
              <svg class="icon-sun" viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg"
                role="img" aria-hidden="true">
                <g fill="none" stroke="none" stroke-width="1" fill-rule="evenodd">
                  <circle cx="12" cy="12" r="4.2" fill="#000" />
                  <g transform="translate(12,12)" stroke="#000" stroke-width="1.6" stroke-linecap="round">
                    <line x1="0" y1="-8.2" x2="0" y2="-11" />
                    <line x1="0" y1="8.2" x2="0" y2="11" />
                    <line x1="-8.2" y1="0" x2="-11" y2="0" />
                    <line x1="8.2" y1="0" x2="11" y2="0" />
                    <line x1="-5.8" y1="-5.8" x2="-8" y2="-8" />
                    <line x1="5.8" y1="-5.8" x2="8" y2="-8" />
                    <line x1="-5.8" y1="5.8" x2="-8" y2="8" />
                    <line x1="5.8" y1="5.8" x2="8" y2="8" />
                  </g>
                </g>
              </svg>
            </span>
          </span>
        </label>
      </div>

      <!-- Menu List -->
      <ul class="menu-list">
        <li class="menu-item" v-if="store.hasPermission('User Management') || store.hasPermission('Delegate Management') || store.hasPermission('Ticket Management')">
          <a class="menu-link d-flex align-items-center" :class="{ collapsed: !isManagementOpen }"
            @click.prevent="isManagementOpen = !isManagementOpen" role="button" aria-expanded="false">
            <i class="fa-solid fa-briefcase"></i>
            <span>Management</span>
            <i class="fa-solid fa-chevron-down ms-auto" :style="{ transform: isManagementOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }" style="font-size: 12px; margin-left: auto"></i>
          </a>
          <div v-show="isManagementOpen" id="collapseManagement">
            <ul class="menu-list" style="padding-left: 12px; margin-top: 4px">
              <li class="menu-item" v-if="store.hasPermission('User Management')">
                <router-link to="/user-management" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> User</router-link>
              </li>
              <li class="menu-item" v-if="store.hasPermission('Delegate Management')">
                <router-link to="/delegate-management" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Delegate</router-link>
              </li>
              <li class="menu-item" v-if="store.hasPermission('Ticket Management')">
                <router-link to="/ticket-management" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Ticket</router-link>
              </li>
            </ul>
          </div>
        </li>

        <li class="menu-item" v-if="store.hasPermission('Add User')">
          <router-link to="/user-management/add" class="menu-link">
            <i class="fa-solid fa-user-plus"></i>
            <span data-translate="add_user">Add User</span>
          </router-link>
        </li>

        <li class="menu-item" v-if="store.hasPermission('System Log') || store.hasPermission('Audit Log')">
          <a class="menu-link d-flex align-items-center" :class="{ collapsed: !isLogsOpen }"
            @click.prevent="isLogsOpen = !isLogsOpen" role="button" aria-expanded="false">
            <i class="fa-solid fa-clock-rotate-left"></i>
            <span data-translate="Logs">Logs</span>
            <i class="fa-solid fa-chevron-down ms-auto" :style="{ transform: isLogsOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }" style="font-size: 12px; margin-left: auto"></i>
          </a>
          <div v-show="isLogsOpen" id="collapseLogs">
            <ul class="menu-list" style="padding-left: 12px; margin-top: 4px">
              <li class="menu-item" v-if="store.hasPermission('System Log')">
                <router-link to="/logs/system" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> System log</router-link>
              </li>
              <li class="menu-item" v-if="store.hasPermission('Audit Log')">
                <router-link to="/logs/audit" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Audit log</router-link>
              </li>
              <li class="menu-item" v-if="store.hasPermission('Ticket History')">
                <router-link to="/logs/ticket-history" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Ticket History</router-link>
              </li>
            </ul>
          </div>
        </li>
      </ul>

      <div class="menu-divider" v-if="store.hasPermission('User Management') || store.hasPermission('Add User') || store.hasPermission('System Log') || store.hasPermission('Audit Log')"></div>

      <ul class="menu-list">
        <li class="menu-item" v-if="store.hasPermission('Role & Permissions') || store.hasPermission('Group & Team')">
          <a class="menu-link d-flex align-items-center" :class="{ collapsed: !isConfigOpen }"
            @click.prevent="isConfigOpen = !isConfigOpen" role="button" aria-expanded="false">
            <i class="fa-solid fa-sliders"></i>
            <span data-translate="configuration">Configuration</span>
            <i class="fa-solid fa-chevron-down ms-auto" :style="{ transform: isConfigOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }" style="font-size: 12px; margin-left: auto"></i>
          </a>
          <div v-show="isConfigOpen" id="collapseConfig">
            <ul class="menu-list" style="padding-left: 12px; margin-top: 4px">
              <li class="menu-item" v-if="store.hasPermission('Role & Permissions')">
                <router-link to="/configuration/role" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Role & Permissions</router-link>
              </li>
              <li class="menu-item" v-if="store.hasPermission('Group & Team')">
                <router-link to="/configuration/group" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Group & Team</router-link>
              </li>
            </ul>
          </div>
        </li>

        <li class="menu-item" v-if="store.hasPermission('Set Column')">
          <a class="menu-link d-flex align-items-center" :class="{ collapsed: !isSetColumnOpen }"
            @click.prevent="isSetColumnOpen = !isSetColumnOpen" role="button" aria-expanded="false">
            <i class="fa-solid fa-gear"></i>
            <span>Settings</span>
            <i class="fa-solid fa-chevron-down ms-auto" :style="{ transform: isSetColumnOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }" style="font-size: 12px; margin-left: auto"></i>
          </a>
          <div v-show="isSetColumnOpen" id="collapseConfig">
            <ul class="menu-list" style="padding-left: 12px; margin-top: 4px">
              <li class="menu-item" v-if="store.hasPermission('Set Column')">
                <router-link to="/setting/column/audio-record" class="menu-link"><i class="fa-solid fa-circle-dot" style="font-size: 8px"></i> Set Column</router-link>
              </li>
            </ul>
          </div>
        </li>
      </ul>

      <div class="menu-divider" v-if="store.hasPermission('Role & Permissions') || store.hasPermission('Group & Team') || store.hasPermission('Set Column')"></div>

      <button @click="handleLogout" class="logout-btn">
        <i class="fa-solid fa-right-from-bracket"></i>
        <span data-translate="logout">Logout</span>
      </button>

      <button id="sidebarTeamClose" style="position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 22px; color: #888; cursor: pointer; display: none" @click="menuOpen = false"></button>
    </div>

    <button id="scrollTopBtn" style="display: none">
      <svg class="progress-circle" width="40" height="40">
        <circle cx="20" cy="20" r="18" stroke="#e0e0e0" stroke-width="3" fill="none" />
        <circle id="progress-ring" cx="20" cy="20" r="18" stroke="#2872fa" stroke-width="3" fill="none" stroke-linecap="round" />
      </svg>
      <i class="bi bi-arrow-up"></i>
    </button>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useAuthStore } from "../stores/auth.store";
import "../assets/css/navbar.css";
import { useRouter } from "vue-router";

const store = useAuthStore();
const router = useRouter();

const menuOpen = ref(false);
const sidebarMenu = ref(null);
const sidebarToggle = ref(null);

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
}

function onClickOutside(e) {
  if (!menuOpen.value) return;
  const menuEl = sidebarMenu.value;
  const toggleEl = sidebarToggle.value;
  const target = e.target;
  if (menuEl && toggleEl && !menuEl.contains(target) && !toggleEl.contains(target)) {
    menuOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", onClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onClickOutside);
});

const isLogsOpen = ref(false);
const isConfigOpen = ref(false);
const isSetColumnOpen = ref(false);
const isManagementOpen = ref(false);

const displayName = computed(() => store.fullName() ?? "Guest User");
const initials = computed(() => {
  const name = store.fullName() || "U";
  return name
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
});

const roleName = computed(() => store.roleName() || "Other");

const handleLogout = () => {
  try { store.logout() } catch (e) { store.clear(); router.push('/login') }
};

function goToProfile() {
  if (store.isTicket && store.isTicket()) return;
  menuOpen.value = false;
  try { router.push('/profile') } catch (e) { console.error('Navigate to profile failed', e) }
}

</script>

<style scoped>
.user-info-group {
  cursor: pointer;
}
.user-info-group.disabled-profile {
  cursor: default;
}
</style>