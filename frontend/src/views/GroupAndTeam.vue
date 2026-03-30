<template>
    <MainLayout>
        <div class="main-wrapper container-fluid-home py-3" style="display:flex; flex-direction:column; height:100%;">
            <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: 'Group & Team Configuration' }]" />
            <div class="row row-container">
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
                                <div class="d-flex align-items-center">
                                    <div class="d-flex align-items-center justify-content-center me-1"
                                        style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                                        <i class="fa-solid fa-user-group" style="color: #2b6cb0; font-size: 18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Group List</h5>
                                </div>

                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="search-group" style="width:260px; position:relative;">
                                        <i class="fa-solid fa-magnifying-glass search-icon"></i>
                                        <input v-model="searchQuery" type="text"
                                            class="form-control form-control-sm search-input"
                                            placeholder="Search..." @input="onTyping" @keyup.enter="onSearch" />
                                    </div>
                                    <button v-if="authStore.hasPermission('Add New Group')" class="btn-role btn-primary btn-sm" id="addGroupBtn"
                                        @click.stop="openCreateGroup">
                                        <i class="fas fa-plus"></i>
                                        Add New Group
                                    </button>
                                </div>
                            </div>
                            <!-- Content Group here. -->
                            <div class="custom-roles-list" id="customRolesList">
                                <template v-if="loading">
                                    <div class="table-overlay" style="height: 487px;">
                                        <div class="overlay-box">Loading...</div>
                                    </div>
                                </template>
                                <template v-else>
                                    <div v-if="groups.length">
                                        <div v-if="filteredGroups.length" class="group-list">
                                            <div v-for="group in filteredGroups" :key="group.id" :class="['group-card-item', { active: selectedGroupId === group.id }]"
                                                @click.stop="selectGroup(group)">
                                                <div class="group-card-main">
                                                    <div class="group-card-header">
                                                        <span class="group-card-title">{{ group.group_name }}</span>
                                                        <span class="group-card-group-badge">
                                                            <template
                                                                v-if="groupTeamsMap[group.id] && groupTeamsMap[group.id].length">
                                                                <span v-for="(t, idx) in groupTeamsMap[group.id]"
                                                                    :key="t.id">
                                                                    {{ t.name }}<span
                                                                        v-if="idx < groupTeamsMap[group.id].length - 1">,
                                                                    </span>
                                                                </span>
                                                            </template>
                                                            <template v-else>
                                                                Unassigned
                                                            </template>
                                                        </span>
                                                    </div>
                                                    <div class="group-card-desc">
                                                        {{ group.description || 'No description provided for this group.' }}
                                                    </div>
                                                </div>

                                                <div class="group-card-actions">
                                                    <button v-if="authStore.hasPermission('Edit Group')" class="group-edit-btn" @click.stop="authStore.hasPermission('Edit Group') && openEditGroup(group.id)">
                                                        Click to edit
                                                    </button>
                                                    <button v-if="authStore.hasPermission('Delete Group')" type="button" class="group-delete-btn" @click.stop="deleteGroup(group.id)">
                                                        <i class="fas fa-trash" style="font-size: 12px;"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                        <div v-else class="empty-state">
                                            <i class="fa-solid fa-dove"></i>
                                            <p>This group not found.</p>
                                        </div>
                                    </div>

                                    <div v-else class="empty-state">
                                        <i class="fas fa-user-plus"></i>
                                        <p>No groups yet. Click "Add New Group" to create one.</p>
                                    </div>
                                </template>
                            </div>

                        </div>
                    </div>
                </div>

                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px">
                                <div class="d-flex align-items-center">
                                    <div class="d-flex align-items-center justify-content-center me-1"
                                        style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                                        <i class="fa-solid fa-people-group" style="color: #2b6cb0; font-size: 18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Team List</h5>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="search-group" style="width:260px; position:relative;">
                                        <i class="fa-solid fa-magnifying-glass search-icon"></i>
                                        <input v-model="teamSearchQuery" type="text"
                                            class="form-control form-control-sm search-input"
                                            placeholder="Search..." @input="onTypingTeam" @keyup.enter="onSearchTeam" />
                                    </div>
                                    <button v-if="authStore.hasPermission('Add New Team')" class="btn-role btn-primary btn-sm" id="addTeamBtn"
                                        @click.stop="openCreateTeam">
                                        <i class="fas fa-plus"></i>
                                        Add New Team
                                    </button>
                                </div>
                            </div>
                            <!-- Content for Team here. -->
                            <div class="custom-roles-list" id="customTeamList">
                                <div v-if="!selectedGroupId" class="empty-state">
                                    <i class="fa-solid fa-dove"></i>
                                    <p>Select a group to view teams.</p>
                                </div>

                                <template v-else>
                                    <template v-if="loading">
                                        <div class="container-overlay" style="height: 487px;">
                                            <div class="overlay-box">Loading...</div>
                                        </div>
                                    </template>
                                    <template v-else>
                                        <div v-if="filteredTeams.length" class="group-list">
                                            <div v-for="team in filteredTeams" :key="team.id" class="group-card-item">
                                                <div class="group-card-main">
                                                    <div class="group-card-header">
                                                        <span class="group-card-title">{{ team.name }}</span>
                                                        <span class="group-card-team-badge">{{ selectedGroupName || team.group_name }}</span>
                                                    </div>
                                                </div>

                                                <div class="group-card-actions">
                                                    <button v-if="authStore.hasPermission('Edit Team')" class="group-edit-btn" @click.stop="authStore.hasPermission('Edit Team') && openEditTeam(team.id)">
                                                        Click to edit
                                                    </button>
                                                    <button v-if="authStore.hasPermission('Delete Team')" type="button" class="group-delete-btn" @click.stop="deleteTeam(team.id)">
                                                        <i class="fas fa-trash" style="font-size: 12px;"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        <div v-else>
                                            <div v-if="groupTeamsMap[selectedGroupId] && groupTeamsMap[selectedGroupId].length" class="empty-state">
                                                <i class="fa-solid fa-dove"></i>
                                                <p>This team not found.</p>
                                            </div>
                                            <div v-else class="empty-state">
                                                <i class="fas fa-user-plus"></i>
                                                <p>No teams for this group.</p>
                                            </div>
                                        </div>
                                    </template>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
    <ModalGroup v-model="showGroupModal" :mode="selectedModalMode" :group="editGroup" :groups="groups" @saved="onGroupSaved" />

</template>

<script setup>
import MainLayout from '../layouts/MainLayout.vue';
import Breadcrumbs from '../components/Breadcrumbs.vue'
import ModalGroup from '../components/ModalGroup.vue'
import { useGroupAndTeam } from '../composables/useGroupAndTeam'

const {
    authStore,
    searchQuery,
    teamSearchQuery,
    selectedGroupId,
    groups,
    teams,
    groupTeamsMap,
    loading,
    showGroupModal,
    selectedModalMode,
    editGroup,
    filteredGroups,
    filteredTeams,
    selectedGroupName,
    onTyping,
    onSearch,
    selectGroup,
    openCreateGroup,
    openEditGroup,
    deleteGroup,
    onTypingTeam,
    onSearchTeam,
    openCreateTeam,
    openEditTeam,
    deleteTeam,
    onGroupSaved
} = useGroupAndTeam()
</script>

<style scoped src="../assets/css/group-and-team.css"></style>
