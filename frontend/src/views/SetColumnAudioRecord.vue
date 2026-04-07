<template>
    <MainLayout>
        <div class="main-wrapper container-fluid py-3">
            <Breadcrumbs :items="[{ text: 'Home', to: '/' }, { text: 'Set Column' }]" />
            <div class="col-lg-12">
                <div class="card">
                    <div class="card-body card-body-datatable" style="position: relative;">
                        <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 6px;">
                            <div class="d-flex align-items-center">
                                <div class="d-flex align-items-center justify-content-center me-1"
                                    style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                    <i class="fa-solid fa-gear" style="color:#2b6cb0;font-size:18px"></i>
                                </div>
                                <h5 class="card-title mb-2 mt-1">Set Column</h5>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div class="search-group" style="width:260px; position:relative;">
                                    <i class="fa-solid fa-magnifying-glass search-icon"></i>
                                    <input v-model="searchQuery" type="text"
                                        class="form-control form-control-sm search-input"
                                        placeholder="Search..." @input="onTyping" @keyup.enter="onSearch" />
                                </div>
                                <button v-if="authStore.hasPermission('Set Column')" class="btn-role btn-primary btn-sm" id="addGroupBtn"
                                    @click.stop="authStore.hasPermission('Set Column') && openCreateGroup()">
                                    <i class="fas fa-plus"></i>
                                    Add New Column
                                </button>
                            </div>
                        </div>

                        <!-- Content Column here. -->
                        <div class="custom-roles-list" id="customRolesList">
                            <template v-if="loading">
                                <div class="table-overlay" style="height: 487px;">
                                    <div class="overlay-box">Loading...</div>
                                </div>
                            </template>
                            <template v-else>
                                <div v-if="columns.length">
                                    <div v-if="filteredColumns.length" class="group-list" style="margin-top: 4px;">
                                        <div v-for="column in filteredColumns" :key="column.id"
                                            :class="['group-card-item', { active: selectedColumnId === column.id }]"
                                            @click.stop="selectColumn(column)">
                                            <div class="group-card-main">
                                                <div class="group-card-header">
                                                    <span class="group-card-title">{{ column.name }}</span>
                                                    <label class="switch_status">
                                                        <input type="checkbox" :checked="column.use"
                                                            @change="() => toggleSetColumnUse(column.user?.id, column)" />
                                                        <span class="slider_status round"></span>
                                                    </label>
                                                </div>
                                                <div class="group-card-desc">
                                                    {{ column.description || 'No description provided for this column.' }}
                                                </div>
                                            </div>

                                            <div class="group-card-actions">
                                                <button v-if="authStore.hasPermission('Set Column')" class="group-edit-btn" @click.stop="authStore.hasPermission('Set Column') && openEditColumn(column.id)">
                                                    Click to edit
                                                </button>
                                                <button v-if="authStore.hasPermission('Set Column')" type="button" class="group-delete-btn"
                                                    @click.stop="deleteColumn(column.id)">
                                                    <i class="fas fa-trash" style="font-size: 12px;"></i>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-else class="empty-state">
                                        <i class="fa-solid fa-dove"></i>
                                        <p>This column not found.</p>
                                    </div>
                                </div>

                                <div v-else class="empty-state">
                                    <i class="fa-solid fa-chart-column"></i>
                                    <p>No columns yet. Click "Add New Column" to create one.</p>
                                </div>
                            </template>
                        </div>


                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
    <ModalSetColumn v-if="authStore.hasPermission('Set Column')" v-model="showModal" :mode="modalMode" :columnData="editColumnData" @saved="onModalSaved"/>
</template>


<script setup>
import MainLayout from '../layouts/MainLayout.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import ModalSetColumn from '../components/ModalSetColumn.vue'
import { useSetColumnAudioRecord } from '../composables/useSetColumnAudioRecord'

const {
    searchQuery,
    authStore,
    columns,
    selectedColumnId,
    loading,
    showModal,
    modalMode,
    editColumnData,
    filteredColumns,
    fetchGetColumnAudioRecord,
    onTyping,
    onSearch,
    selectColumn,
    openCreateGroup,
    openEditColumn,
    deleteColumn,
    toggleSetColumnUse,
    onModalSaved
} = useSetColumnAudioRecord()
</script>

<style scoped src="../assets/css/set-column-audio-record.css"></style>
