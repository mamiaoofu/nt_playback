<template>
  <MainLayout>
    <div class="main-wrapper-container">

      <!-- 1. Form Section -->
      <div class="card mb-3">
        <div class="card-body">
          <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 18px;">
            <div class="d-flex align-items-center">
              <div class="d-flex align-items-center justify-content-center me-1" style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                <i class="fas fa-database" style="color:#2b6cb0;font-size:18px"></i>
              </div>
              <h5 class="card-title mb-2 mt-1">Data Retention</h5>
            </div>
          </div>
          
          <ul class="nav nav-tabs" id="retentionTabs" role="tablist">
            <li class="nav-item" role="presentation">
              <button class="nav-link" :class="{ active: activeTab === 'auto' }" @click="activeTab = 'auto'" type="button" role="tab">Schedule Retention</button>
            </li>
            <li class="nav-item" role="presentation">
              <button class="nav-link" :class="{ active: activeTab === 'manual' }" @click="activeTab = 'manual'" type="button" role="tab">Immediately Retention</button>
            </li>
          </ul>

          <!-- TAB: Schedule Retention -->
          <div v-if="activeTab === 'auto'" class="tab-pane fade show active">
            <div class="row">
              <!-- Left Column: Retention Period -->
              <div class="col-lg-6 pe-lg-4" style="border-right: 1px solid #f1f5f9;">
                <div class="form-section-title">Retention Period :</div>
                <div class="d-flex flex-column gap-3 mb-4">
                  
                  <!-- Option 1: Older than relative or specific date -->
                  <div class="option-row d-flex align-items-center">
                    <div class="form-check me-3" style="min-width: 100px;">
                      <input class="form-check-input" type="checkbox" id="autoOlderThanCheck" :checked="auto.retentionType === 'OLDER_THAN'" @change="auto.retentionType = 'OLDER_THAN'" :disabled="isScheduleActive" />
                      <label class="form-check-label" for="autoOlderThanCheck" style="font-weight: 500;">Older than</label>
                    </div>
                    
                    <!-- Number Input -->
                    <div class="me-3" style="width: 80px;">
                      <input 
                        type="number" 
                        class="input-custom" 
                        v-model="autoOlderThanValue" 
                        placeholder="Num" 
                        min="1"
                        :disabled="isScheduleActive || auto.retentionType !== 'OLDER_THAN'"
                        style="padding: 6px 12px;"
                      />
                    </div>

                    <!-- Unit Checkboxes -->
                    <div class="d-flex gap-3 align-items-center">
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          id="unitDaily" 
                          :checked="autoOlderThanUnit === 'D'" 
                          @change="autoOlderThanUnit = 'D'"
                          :disabled="isScheduleActive || auto.retentionType !== 'OLDER_THAN'"
                        />
                        <label class="form-check-label" for="unitDaily">Daily</label>
                      </div>
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          id="unitMonthly" 
                          :checked="autoOlderThanUnit === 'M'" 
                          @change="autoOlderThanUnit = 'M'"
                          :disabled="isScheduleActive || auto.retentionType !== 'OLDER_THAN'"
                        />
                        <label class="form-check-label" for="unitMonthly">Monthly</label>
                      </div>
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          id="unitYearly" 
                          :checked="autoOlderThanUnit === 'Y'" 
                          @change="autoOlderThanUnit = 'Y'"
                          :disabled="isScheduleActive || auto.retentionType !== 'OLDER_THAN'"
                        />
                        <label class="form-check-label" for="unitYearly">Yearly</label>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Option 2: Date range -->
                  <div class="option-row d-flex align-items-center">
                    <div class="form-check me-3" style="min-width: 100px;">
                      <input class="form-check-input" type="checkbox" id="autoDateRangeCheck" :checked="auto.retentionType === 'DATE_RANGE'" @change="auto.retentionType = 'DATE_RANGE'" :disabled="isScheduleActive" />
                      <label class="form-check-label" for="autoDateRangeCheck" style="font-weight: 500;">Date Range</label>
                    </div>
                    
                    <div class="d-flex gap-2">
                      <div class="input-group-custom flatpickr-wrap" v-has-value style="width: 140px;">
                        <input 
                          ref="autoStartInput" 
                          v-flatpickr="{ target: auto, key: 'startDate', noTime: true }" 
                          type="text" 
                          autocomplete="off" 
                          class="input-custom" 
                          placeholder="Start Date"
                          :disabled="isScheduleActive || auto.retentionType !== 'DATE_RANGE'" 
                        />
                        <span class="calendar-icon-custom" @click="!isScheduleActive && auto.retentionType === 'DATE_RANGE' && autoStartInput && autoStartInput.focus()">
                          <i class="fa-regular fa-calendar"></i>
                        </span>
                      </div>
                      <div class="input-group-custom flatpickr-wrap" v-has-value style="width: 140px;">
                        <input 
                          ref="autoEndInput" 
                          v-flatpickr="{ target: auto, key: 'endDate', noTime: true }" 
                          type="text" 
                          autocomplete="off" 
                          class="input-custom" 
                          placeholder="End Date"
                          :disabled="isScheduleActive || auto.retentionType !== 'DATE_RANGE'" 
                        />
                        <span class="calendar-icon-custom" @click="!isScheduleActive && auto.retentionType === 'DATE_RANGE' && autoEndInput && autoEndInput.focus()">
                          <i class="fa-regular fa-calendar"></i>
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Option 3: Once vs Recurrence -->
                  <div class="option-row d-flex align-items-center">
                    <div style="min-width: 116px;"></div>
                    <div class="form-check form-check-inline">
                      <input class="form-check-input" type="checkbox" id="autoOnceCheck" :checked="auto.isOnce" @change="auto.isOnce = true; auto.isRecurrence = false" :disabled="isScheduleActive || auto.retentionType === 'DATE_RANGE'" />
                      <label class="form-check-label" for="autoOnceCheck">Once</label>
                    </div>
                    <div class="form-check form-check-inline ms-3">
                      <input class="form-check-input" type="checkbox" id="autoRecCheck" :checked="auto.isRecurrence" @change="auto.isRecurrence = true; auto.isOnce = false" :disabled="isScheduleActive || auto.retentionType === 'DATE_RANGE'" />
                      <label class="form-check-label" for="autoRecCheck">Recurrence</label>
                    </div>
                  </div>
                  
                </div>
              </div>
              
              <!-- Right Column: Run on a Schedule -->
              <div class="col-lg-6 ps-lg-4">
                <div class="form-section-title">Run on a Schedule :</div>
                <div class="d-flex flex-column gap-3 mb-4">
                  
                  <div class="d-flex align-items-center gap-2">
                    <label style="font-weight: 500; font-size: 13px; min-width: 80px;">How often :</label>
                    <div style="width: 200px;">
                      <CustomSelect 
                        v-model="auto.howOften" 
                        :options="howOftenOptions" 
                        placeholder="How often" 
                        :class="{ 'select-disabled': isScheduleActive }" 
                      />
                    </div>
                  </div>
                  
                  <div class="d-flex align-items-center gap-2">
                    <label style="font-weight: 500; font-size: 13px; min-width: 80px;">What day :</label>
                    <div style="width: 200px;">
                      <CustomSelect 
                        v-model="auto.whatDay" 
                        :options="whatDayOptions" 
                        placeholder="What day" 
                        :class="{ 'select-disabled': isScheduleActive || auto.howOften === 'daily' }" 
                      />
                    </div>
                  </div>
                  
                  <div class="d-flex align-items-center gap-2">
                    <label style="font-weight: 500; font-size: 13px; min-width: 80px;">What time :</label>
                    <div class="input-group-custom flatpickr-wrap" v-has-value style="width: 200px;">
                      <input 
                        ref="autoExecutionTimeInput" 
                        v-flatpickr="{ target: auto, key: 'executionTime', options: { enableTime: true, noCalendar: true, time_24hr: true, dateFormat: 'H:i' } }" 
                        type="text" 
                        autocomplete="off" 
                        class="input-custom" 
                        placeholder="What time"
                        :disabled="isScheduleActive" 
                      />
                      <span class="calendar-icon-custom" @click="!isScheduleActive && autoExecutionTimeInput && autoExecutionTimeInput.focus()">
                        <i class="fa-regular fa-clock"></i>
                      </span>
                    </div>
                  </div>
                  
                </div>
              </div>
            </div>
            
            <!-- Bottom Area of Schedule Retention (Delete Option & Active Toggle & Button inline) -->
            <div class="border-top pt-3 mt-2">
              <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex gap-4 align-items-center">
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" id="autoDeleteIndexOnly" :checked="auto.deleteOption === 'INDEX_ONLY'" @change="auto.deleteOption = 'INDEX_ONLY'" :disabled="isScheduleActive" />
                    <label class="form-check-label" for="autoDeleteIndexOnly">Only Indexs</label>
                  </div>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" id="autoDeleteVoiceIndex" :checked="auto.deleteOption === 'VOICE_AND_INDEX'" @change="auto.deleteOption = 'VOICE_AND_INDEX'" :disabled="isScheduleActive" />
                    <label class="form-check-label" for="autoDeleteVoiceIndex">Indexs & Voice Files</label>
                  </div>
                </div>
                <div>
                  <button class="btn btn-primary" type="button" @click="promptPassword('auto')" :disabled="loading || isScheduleActive" style="margin-top: 0;">
                    <i class="fas fa-save"></i> {{ loading ? 'Saving...' : 'Save and Run' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB: Immediately Retention -->
          <div v-if="activeTab === 'manual'" class="tab-pane fade show active">
            <div class="retention-form-grid">
              <div class="form-section-title">Retention Period :</div>
              
              <div class="d-flex gap-2 mb-4">
                <div class="input-group-custom flatpickr-wrap" v-has-value style="width: 200px;">
                  <input 
                    ref="manualStartInput" 
                    v-flatpickr="{ target: manual, key: 'startDate', noTime: true }" 
                    type="text" 
                    autocomplete="off" 
                    class="input-custom" 
                    placeholder="Start Date"
                  />
                  <span class="calendar-icon-custom" @click="manualStartInput && manualStartInput.focus()">
                    <i class="fa-regular fa-calendar"></i>
                  </span>
                </div>
                <div class="input-group-custom flatpickr-wrap" v-has-value style="width: 200px;">
                  <input 
                    ref="manualEndInput" 
                    v-flatpickr="{ target: manual, key: 'endDate', noTime: true }" 
                    type="text" 
                    autocomplete="off" 
                    class="input-custom" 
                    placeholder="End Date"
                  />
                  <span class="calendar-icon-custom" @click="manualEndInput && manualEndInput.focus()">
                    <i class="fa-regular fa-calendar"></i>
                  </span>
                </div>
              </div>
              
              <!-- Delete Options Section & Button inline -->
              <div class="d-flex justify-content-between align-items-center mb-4">
                <div class="d-flex gap-4 align-items-center">
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" id="manualDeleteIndexOnly" :checked="manual.deleteOption === 'INDEX_ONLY'" @change="manual.deleteOption = 'INDEX_ONLY'" />
                    <label class="form-check-label" for="manualDeleteIndexOnly">Only Indexs</label>
                  </div>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" id="manualDeleteVoiceIndex" :checked="manual.deleteOption === 'VOICE_AND_INDEX'" @change="manual.deleteOption = 'VOICE_AND_INDEX'" />
                    <label class="form-check-label" for="manualDeleteVoiceIndex">Indexs & Voice Files</label>
                  </div>
                </div>
                <div>
                  <button class="btn btn-primary" type="button" @click="promptPassword('manual')" :disabled="loading" style="margin-top: 0;">
                    <i class="fas fa-play"></i> {{ loading ? 'Saving...' : 'Save and Run' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
      
      <!-- 2. Task List Section -->
      <div class="card card-custom-role" id="taskListSection" :class="{ 'manual-height': activeTab === 'manual' }">
        <div class="card-body">
          <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 12px">
            <div class="d-flex align-items-center">
              <div class="d-flex align-items-center justify-content-center me-1"
                style="width: 35px; height: 35px; background-color: #d9e2f6; border-radius: 10px !important">
                <i class="fas fa-tasks" style="color: #2b6cb0; font-size: 18px"></i>
              </div>
              <h5 class="card-title mb-2 mt-1">Task List</h5>
            </div>
          </div>

          <!-- Header Row -->
          <div class="retention-header-row">
            <div class="col-no">No.</div>
            <div class="col-id">Retention ID</div>
            <div class="col-count">Index Count</div>
            <div class="col-time">Retention Period</div>
            <div class="col-date">Running Date</div>
            <div class="col-status">Status</div>
            <div class="col-action">Action</div>
          </div>

          <!-- List Container -->
          <div class="retention-list-container" :class="{ 'no-scrollbar': activeTab === 'auto', 'schedule-list-height': activeTab === 'auto', 'manual-list-height': activeTab === 'manual' }">
            <div v-if="loadingTasks" class="empty-state">
              <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
              <span>Loading tasks...</span>
            </div>
            <template v-else>
              <div v-if="filteredTasks.length" class="retention-list-wrapper">
                <div v-for="(row, idx) in filteredTasks" :key="row.id" class="custom-role-item" @click="showTaskDetails(row)">
                  <div class="col-no">{{ idx + 1 }}</div>
                  <div class="col-id text-truncate" :title="row.id">{{ row.id }}</div>
                  <div class="col-count">{{ row.index_count }}</div>
                  <div class="col-time text-truncate" :title="row.time_period">{{ formatRetentionPeriod(row.time_period) }}</div>
                  <div class="col-date text-truncate" :title="getRunningDate(row)">{{ getRunningDate(row) }}</div>
                  <div class="col-status">
                    <span class="role-badge" :class="row.status.toLowerCase()">
                      {{ row.status === 'SUCCESS' ? 'Permanent Delete' : row.status }}
                    </span>
                  </div>
                  <div class="col-action">
                    <div class="group-card-actions justify-content-end">


                      <button v-if="row.status === 'RUNNING'" 
                        type="button" class="group-reset-btn" @click.stop="promptPassword('restore', row.id)">
                        <i class="fas fa-undo" style="font-size: 10px;"></i>
                      </button>
                      
                      <template v-if="row.task_type === 'AUTO_EXECUTION'">
                        <button v-if="row.status === 'STOPPED'"
                          type="button" class="group-send-btn" @click.stop="startTask(row.id)">
                          <i class="fas fa-play" style="font-size: 10px;"></i>
                        </button>
                        <button v-if="row.status === 'READY' || row.status === 'RUNNING'"
                          type="button" class="group-delete-btn" @click.stop="stopTask(row.id)">
                          <i class="fas fa-stop" style="font-size: 10px;"></i>
                        </button>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">
                <i class="fa-solid fa-dove mb-2" style="font-size: 24px; color: #94a3b8;"></i>
                <p class="mb-0 text-muted">No retention tasks found.</p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Password Confirmation Modal -->
    <div v-if="showPasswordModal" class="modal-backdrop" @click.self="showPasswordModal = false" style="z-index: 2000; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center;">
      <div class="modal-box" style="max-width: 450px; width: 100%;">
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid rgba(0,0,0,0.06);">
          <div style="display: flex; align-items: center; gap: 8px">
            <div class="blue-icon" style="width: 35px; height: 35px; background-color: #D9E2F6; border-radius: 10px !important; display: flex; align-items: center; justify-content: center;">
              <i class="fa-solid fa-key" style="color: #2b6cb0;"></i>
            </div>
            <h3 class="modal-title ad" style="font-size: 16px; font-weight: 600; margin: 0;">Confirm Password</h3>
          </div>
          <button type="button" class="btn-close" @click="showPasswordModal = false" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #64748b;">&times;</button>
        </div>
        <div class="modal-body" style="min-height: auto; padding: 20px 24px;">
          <div class="form-group-modal">
            <p class="mb-3 text-muted" style="font-size: 13px; margin-bottom: 16px; color: #64748b;">Please enter your password to confirm this action.</p>
            <div class="input-group" v-has-value>
              <input required v-model="confirmPassword" :type="passwordVisible ? 'text' : 'password'" autocomplete="off" class="input" @keyup.enter="handlePasswordConfirm" />
              <button type="button" class="toggle-visibility" @click="passwordVisible = !passwordVisible" aria-label="Toggle password visibility">
                <i :class="passwordVisible ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'"></i>
              </button>
              <label class="title-label">Password</label>
            </div>
          </div>
        </div>
        <div class="modal-footer" style="padding: 12px 24px; border-top: 1px solid rgba(0,0,0,0.06); display: flex; justify-content: flex-end; gap: 8px;">
          <button class="btn btn-secondary btn-sm" style="border-radius: 20px; padding: 6px 16px; font-size: 12px;" @click="showPasswordModal = false">
            <i class="fas fa-times"></i> Cancel
          </button>
          <button class="btn btn-primary btn-sm" style="border-radius: 20px; padding: 6px 16px; font-size: 12px;" @click="handlePasswordConfirm" :disabled="!confirmPassword || loading">
            <i class="fas fa-check"></i> Confirm
          </button>
        </div>
      </div>
    </div>

    <!-- Task Detail Modal -->
    <div v-if="showDetailModal && selectedTask" class="modal-backdrop" @click.self="showDetailModal = false" style="z-index: 2000; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center;">
      <div class="modal-box" style="max-width: 500px; width: 100%;">
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid rgba(0,0,0,0.06);">
          <div style="display: flex; align-items: center; gap: 8px">
            <div class="blue-icon" style="width: 35px; height: 35px; background-color: #D9E2F6; border-radius: 10px !important; display: flex; align-items: center; justify-content: center;">
              <i class="fa-solid fa-circle-info" style="color: #2b6cb0;"></i>
            </div>
            <h3 class="modal-title ad" style="font-size: 16px; font-weight: 600; margin: 0;">Task Detail</h3>
          </div>
          <button type="button" class="btn-close" @click="showDetailModal = false" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #64748b;">&times;</button>
        </div>
        <div class="modal-body" style="padding: 24px; max-height: 70vh; overflow-y: auto;">
          <div class="detail-grid" style="display: flex; flex-direction: column; gap: 14px;">
            
            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Retention ID</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">{{ selectedTask.id }}</div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Action</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">
                {{ selectedTask.delete_option === 'INDEX_ONLY' ? 'Only Indexs' : selectedTask.delete_option === 'VOICE_AND_INDEX' ? 'Indexs & Voice Files' : selectedTask.delete_option }}
              </div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Retention Type</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">
                {{ selectedTask.task_type === 'AUTO_EXECUTION' ? 'Schedule' : selectedTask.task_type === 'MANUAL' ? 'Immediately' : selectedTask.task_type }}
              </div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; align-items: center;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Status</div>
              <div class="detail-value">
                <span class="role-badge" :class="selectedTask.status.toLowerCase()">
                  {{ selectedTask.status === 'SUCCESS' ? 'Permanent Delete' : selectedTask.status }}
                </span>
              </div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Retention Period</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">
                {{ formatRetentionPeriod(selectedTask.time_period) }}
              </div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Times</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">
                {{ selectedTask.task_type === 'MANUAL' ? 'Once' : (config && config.is_once ? 'Once' : 'Recurrence') }}
              </div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Index Count</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">{{ selectedTask.index_count }}</div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Running Date</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">
                {{ getRunningDate(selectedTask) }}
              </div>
            </div>

            <div class="detail-row" style="display: flex; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Created By</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">{{ selectedTask.user_create }}</div>
            </div>

            <div class="detail-row" style="display: flex; padding-bottom: 4px;">
              <div class="detail-label" style="width: 160px; font-weight: 600; color: #64748b; font-size: 13px;">Created Date</div>
              <div class="detail-value" style="color: #1e293b; font-size: 13px; font-weight: 500;">{{ formatDate(selectedTask.created_at) }}</div>
            </div>

          </div>
        </div>
        <div class="modal-footer" style="padding: 12px 24px; border-top: 1px solid rgba(0,0,0,0.06); display: flex; justify-content: flex-end;">
          <button class="btn btn-secondary btn-sm" style="border-radius: 20px; padding: 6px 16px; font-size: 12px; margin-top: 0;" @click="showDetailModal = false">
            <i class="fas fa-times"></i> Close
          </button>
        </div>
      </div>
    </div>


  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import MainLayout from '../../layouts/MainLayout.vue';
import CustomSelect from '../../components/CustomSelect.vue';
import { showToast } from '../../assets/js/function-all';
import { getCsrfToken } from '../../api/csrf';

const API_BASE = '/api/v1/retention';
const route = useRoute();
const activeTab = ref('auto');
const loading = ref(false);
const loadingTasks = ref(false);
const tasks = ref([]);
const config = ref(null);

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  const pad = (num) => String(num).padStart(2, '0');
  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const date = pad(d.getDate());
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  return `${year}-${month}-${date} ${hours}:${minutes}`;
};

const autoStartInput = ref(null);
const autoEndInput = ref(null);
const autoExecutionTimeInput = ref(null);
const manualStartInput = ref(null);
const manualEndInput = ref(null);
const autoOlderThanValue = ref(1);
const autoOlderThanUnit = ref('Y');
const showPasswordModal = ref(false);
const confirmPassword = ref('');
const passwordAction = ref('');
const isConfigRunning = ref(false);
const passwordVisible = ref(false);

const taskToRestore = ref(null);

const showDetailModal = ref(false);
const selectedTask = ref(null);

const showTaskDetails = (task) => {
  selectedTask.value = task;
  showDetailModal.value = true;
};

const formatRetentionPeriod = (timePeriod) => {
  if (!timePeriod) return '-';
  if (timePeriod.startsWith('Older than ')) {
    return timePeriod.replace('Older than ', 'over ');
  }
  return timePeriod;
};

const calculateNextRun = (task, configVal) => {
  if (!task || task.task_type === 'MANUAL') {
    return '-';
  }
  if (task.status === 'STOPPED') {
    return 'Stopped';
  }
  if (!configVal) {
    return 'Loading...';
  }
  if (!configVal.is_active) {
    return 'Stopped';
  }
  
  const timeStr = configVal.execution_time || '01:00:00';
  const [execHour, execMinute] = timeStr.split(':').map(Number);
  
  const now = new Date();
  
  let lastExecutedToday = false;
  if (task.executed_at) {
    const execDate = new Date(task.executed_at);
    if (execDate.getFullYear() === now.getFullYear() &&
        execDate.getMonth() === now.getMonth() &&
        execDate.getDate() === now.getDate()) {
      lastExecutedToday = true;
    }
  }
  
  let candidate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), execHour, execMinute, 0, 0);
  
  if (candidate <= now || lastExecutedToday) {
    candidate.setDate(candidate.getDate() + 1);
  }
  
  const howOften = configVal.how_often || 'daily';
  const whatDay = configVal.what_day;
  
  for (let i = 0; i < 400; i++) {
    const year = candidate.getFullYear();
    const month = candidate.getMonth();
    const day = candidate.getDate();
    const dayOfWeekName = candidate.toLocaleDateString('en-US', { weekday: 'long' });
    
    let matches = false;
    
    if (howOften === 'daily') {
      matches = true;
    } else if (howOften === 'weekly') {
      if (whatDay && dayOfWeekName.toLowerCase() === whatDay.toLowerCase()) {
        matches = true;
      }
    } else if (howOften === 'monthly') {
      if (whatDay) {
        if (/^\d+$/.test(whatDay)) {
          const targetDay = parseInt(whatDay, 10);
          const lastDayInMonth = new Date(year, month + 1, 0).getDate();
          const effectiveTarget = Math.min(targetDay, lastDayInMonth);
          if (day === effectiveTarget) {
            matches = true;
          }
        } else {
          if (dayOfWeekName.toLowerCase() === whatDay.toLowerCase() && day <= 7) {
            matches = true;
          }
        }
      }
    } else if (howOften === 'yearly') {
      if (month === 0 && whatDay) {
        if (/^\d+$/.test(whatDay)) {
          const targetDay = parseInt(whatDay, 10);
          const lastDayInMonth = new Date(year, 1, 0).getDate();
          const effectiveTarget = Math.min(targetDay, lastDayInMonth);
          if (day === effectiveTarget) {
            matches = true;
          }
        } else {
          if (dayOfWeekName.toLowerCase() === whatDay.toLowerCase() && day <= 7) {
            matches = true;
          }
        }
      }
    }
    
    if (matches) {
      return formatDate(candidate);
    }
    
    candidate.setDate(candidate.getDate() + 1);
  }
  
  return '-';
};

const getRunningDate = (task) => {
  if (!task) return '-';
  if (task.task_type === 'MANUAL') {
    return formatDate(task.created_at);
  }
  return calculateNextRun(task, config.value);
};

const howOftenOptions = [
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly', value: 'monthly' },
  { label: 'Yearly', value: 'yearly' }
];

const whatDayOptions = computed(() => {
  if (auto.value.howOften === 'monthly' || auto.value.howOften === 'yearly') {
    return Array.from({ length: 31 }, (_, i) => {
      const day = i + 1;
      return { label: day.toString(), value: day.toString() };
    });
  }
  return [
    { label: 'Sunday', value: 'Sunday' },
    { label: 'Monday', value: 'Monday' },
    { label: 'Tuesday', value: 'Tuesday' },
    { label: 'Wednesday', value: 'Wednesday' },
    { label: 'Thursday', value: 'Thursday' },
    { label: 'Friday', value: 'Friday' },
    { label: 'Saturday', value: 'Saturday' }
  ];
});

const columns = [
  { key: 'no', label: 'No.', isIndex: true },
  { key: 'id', label: 'Retention ID' },
  { key: 'task_type', label: 'Type' },
  { key: 'index_count', label: 'Index count' },
  { key: 'time_period', label: 'Time' },
  { key: 'user_create', label: 'User create' },
  { key: 'updated_at', label: 'Date update' },
  { key: 'status', label: 'Status' },
  { key: 'action', label: 'Action', sortable: false }
];

const manual = ref({
  deleteOption: 'INDEX_ONLY',
  startDate: '',
  endDate: ''
});

const auto = ref({
  retentionType: 'OLDER_THAN',
  olderThanType: 'RELATIVE',
  retentionPeriod: '1Y',
  olderThanDate: '',
  startDate: '',
  endDate: '',
  isOnce: false,
  isRecurrence: true,
  howOften: 'monthly',
  whatDay: '1',
  executionTime: '01:00',
  deleteOption: 'INDEX_ONLY',
  isActive: true
});

// Date range watchers only

watch(() => auto.value.retentionType, (newVal) => {
  if (newVal === 'DATE_RANGE') {
    auto.value.isOnce = true;
    auto.value.isRecurrence = false;
  }
});

watch(() => auto.value.howOften, (newVal, oldVal) => {
  if (newVal === 'monthly' || newVal === 'yearly') {
    if (oldVal === 'weekly' || !/^\d+$/.test(auto.value.whatDay)) {
      auto.value.whatDay = '1';
    }
  } else if (newVal === 'weekly') {
    if (/^\d+$/.test(auto.value.whatDay)) {
      auto.value.whatDay = 'Sunday';
    }
  }
});

const filteredTasks = computed(() => {
  if (activeTab.value === 'auto') {
    return tasks.value.filter(task => task.task_type === 'AUTO_EXECUTION');
  } else if (activeTab.value === 'manual') {
    return tasks.value.filter(task => task.task_type === 'MANUAL');
  }
  return tasks.value;
});

const isScheduleActive = computed(() => {
  return tasks.value.some(task => 
    task.task_type === 'AUTO_EXECUTION' && (task.status === 'READY' || task.status === 'RUNNING')
  );
});

onMounted(() => {
  if (route.query.tab === 'auto' || route.query.tab === 'manual') {
    activeTab.value = route.query.tab;
  }
  fetchAutoConfig();
  fetchTasks();
  
  if (route.query.scroll === 'tasks' || route.query.tab === 'tasks') {
    nextTick(() => {
      const el = document.getElementById('taskListSection');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    });
  }
});

watch(() => route.query, (newQuery) => {
  if (newQuery.scroll === 'tasks' || newQuery.tab === 'tasks') {
    const el = document.getElementById('taskListSection');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }
});

const fetchAutoConfig = async () => {
  try {
    const res = await axios.get(`${API_BASE}/auto/`, { withCredentials: true });
    if (res.data && res.data.id) {
      config.value = res.data;
      auto.value.retentionType = res.data.retention_type || 'OLDER_THAN';
      auto.value.olderThanType = res.data.older_than_type || 'RELATIVE';
      auto.value.retentionPeriod = res.data.retention_period || '';
      const period = res.data.retention_period || '1Y';
      const valMatch = period.match(/\d+/);
      const unitMatch = period.match(/[a-zA-Z]+/);
      autoOlderThanValue.value = valMatch ? parseInt(valMatch[0]) : 1;
      autoOlderThanUnit.value = unitMatch ? unitMatch[0].toUpperCase() : 'Y';
      auto.value.olderThanDate = res.data.older_than_date || '';
      auto.value.startDate = res.data.start_date || '';
      auto.value.endDate = res.data.end_date || '';
      auto.value.isOnce = res.data.is_once !== undefined ? res.data.is_once : false;
      auto.value.isRecurrence = res.data.is_recurrence !== undefined ? res.data.is_recurrence : true;
      
      auto.value.howOften = res.data.how_often || 'monthly';
      const defaultDay = (auto.value.howOften === 'monthly' || auto.value.howOften === 'yearly') ? '1' : 'Sunday';
      auto.value.whatDay = res.data.what_day || defaultDay;
      auto.value.executionTime = res.data.execution_time ? res.data.execution_time.substring(0,5) : '01:00';
      
      auto.value.deleteOption = res.data.delete_option || 'INDEX_ONLY';
      auto.value.isActive = res.data.is_active !== undefined ? res.data.is_active : true;
      isConfigRunning.value = res.data.is_running === true;
    }
  } catch (err) {
    console.error("Failed to fetch auto config", err);
  }
};

const fetchTasks = async () => {
  loadingTasks.value = true;
  try {
    const res = await axios.get(`${API_BASE}/tasks/`, { withCredentials: true });
    tasks.value = res.data;
  } catch (err) {
    console.error("Failed to fetch tasks", err);
    showToast("Failed to fetch tasks", "error");
  } finally {
    loadingTasks.value = false;
  }
};

const promptPassword = (actionType, taskId = null) => {
  if (actionType === 'manual') {
    if (!manual.value.startDate || !manual.value.endDate) {
      showToast('Please select start and end dates.', 'error');
      return;
    }
  }
  passwordAction.value = actionType;
  if (taskId) {
    taskToRestore.value = taskId;
  }
  confirmPassword.value = '';
  passwordVisible.value = false;
  showPasswordModal.value = true;
};

const handlePasswordConfirm = async () => {
  if (!confirmPassword.value) return;
  const pwd = confirmPassword.value;
  showPasswordModal.value = false;
  confirmPassword.value = '';
  passwordVisible.value = false;
  
  if (passwordAction.value === 'manual') {
    await submitManual(pwd);
  } else if (passwordAction.value === 'auto') {
    await saveAutoConfig(pwd);
  } else if (passwordAction.value === 'restore') {
    await confirmRestore(pwd);
  }
};

const submitManual = async (password) => {
  loading.value = true;
  try {
    const res = await axios.post(`${API_BASE}/manual/`, {
      date_range_start: manual.value.startDate,
      date_range_end: manual.value.endDate,
      delete_option: manual.value.deleteOption,
      password: password
    }, {
      withCredentials: true,
      headers: {
        'X-CSRFToken': getCsrfToken() || ''
      }
    });
    showToast(`Success: Task created. Affected records: ${res.data.count}`, 'success');
    fetchTasks();
  } catch (err) {
    showToast(err.response?.data?.error || 'Execution failed.', 'error');
  } finally {
    loading.value = false;
  }
};

const saveAutoConfig = async (password) => {
  loading.value = true;
  try {
    await axios.put(`${API_BASE}/auto/`, {
      retention_type: auto.value.retentionType,
      older_than_type: auto.value.olderThanType,
      retention_period: `${autoOlderThanValue.value}${autoOlderThanUnit.value}`,
      older_than_date: auto.value.olderThanDate || null,
      start_date: auto.value.startDate || null,
      end_date: auto.value.endDate || null,
      is_once: auto.value.isOnce,
      is_recurrence: auto.value.isRecurrence,
      how_often: auto.value.howOften,
      what_day: auto.value.whatDay,
      execution_time: auto.value.executionTime + ':00',
      delete_option: auto.value.deleteOption,
      is_active: true,
      password: password
    }, {
      withCredentials: true,
      headers: {
        'X-CSRFToken': getCsrfToken() || ''
      }
    });
    showToast('Auto configuration saved successfully.', 'success');
    await fetchAutoConfig();
    await fetchTasks();
  } catch (err) {
    showToast(err.response?.data?.error || 'Save failed.', 'error');
  } finally {
    loading.value = false;
  }
};

const editTask = (row) => {
  if (row.task_type === 'AUTO_EXECUTION') {
    activeTab.value = 'auto';
  } else {
    activeTab.value = 'manual';
    if (row.time_period && row.time_period.includes(' to ')) {
      const parts = row.time_period.split(' to ');
      manual.value.startDate = parts[0].trim();
      manual.value.endDate = parts[1].trim();
    } else if (row.time_period && row.time_period.includes(' - ')) {
      const parts = row.time_period.split(' - ');
      manual.value.startDate = parts[0].trim();
      manual.value.endDate = parts[1].trim();
    }
    manual.value.deleteOption = row.delete_option || 'INDEX_ONLY';
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const confirmRestore = async (password) => {
  if (!taskToRestore.value) return;
  loading.value = true;
  try {
    await axios.post(`${API_BASE}/${taskToRestore.value}/restore/`, {
      password: password
    }, {
      withCredentials: true,
      headers: {
        'X-CSRFToken': getCsrfToken() || ''
      }
    });
    showToast("Data restored successfully.", "success");
    fetchTasks();
  } catch (err) {
    showToast(err.response?.data?.error || "Restore failed.", "error");
    console.error(err);
  } finally {
    loading.value = false;
    taskToRestore.value = null;
  }
};

const startTask = async (taskId) => {
  try {
    await axios.post(`${API_BASE}/${taskId}/start/`, {}, {
      withCredentials: true,
      headers: {
        'X-CSRFToken': getCsrfToken() || ''
      }
    });
    showToast("Task started successfully (status: Ready).", "success");
    fetchTasks();
  } catch (err) {
    showToast(err.response?.data?.error || "Failed to start task.", "error");
    console.error(err);
  }
};

const stopTask = async (taskId) => {
  try {
    await axios.post(`${API_BASE}/${taskId}/stop/`, {}, {
      withCredentials: true,
      headers: {
        'X-CSRFToken': getCsrfToken() || ''
      }
    });
    showToast("Task stopped successfully (status: Stopped).", "success");
    fetchTasks();
  } catch (err) {
    showToast(err.response?.data?.error || "Failed to stop task.", "error");
    console.error(err);
  }
};
</script>

<style scoped>
@import "../../assets/css/user-form.css";
@import "../../assets/css/user-management.css";

label {
  font-size: 13px !important;
}

.role-badge.ready { background: #e0f2fe; color: #0369a1; }
.role-badge.running { background: #dbeafe; color: #1e40af; }
.role-badge.stopped { background: #f1f5f9; color: #475569; }
.role-badge.success { background: #dcfce7; color: #166534; }
.role-badge.failed { background: #fee2e2; color: #991b1b; }
.role-badge.restored { background: #fef9c3; color: #854d0e; }

.form-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin-top: 16px;
  margin-bottom: 12px;
  border-left: 3px solid #2b6cb0;
  padding-left: 8px;
}

.retention-form-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-group-custom {
  position: relative;
  display: flex;
  align-items: center;
}

.input-custom {
  width: 100%;
  border: 1.5px solid #d1d5db;
  border-radius: 20px;
  padding: 6px 36px 6px 16px;
  outline: none;
  font-size: 13px;
  transition: all 0.2s;
  background-color: #fff;
}

.input-custom:focus {
  border-color: #416fd6;
  box-shadow: 0 0 0 3px rgba(65, 111, 214, 0.15);
}

.input-custom:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.6;
}

.calendar-icon-custom {
  position: absolute;
  right: 12px;
  cursor: pointer;
  color: #6b7280;
  font-size: 14px;
  display: flex;
  align-items: center;
}

/* Retention Custom Roles List Styling */
.retention-header-row {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: #f8fafc;
  border-bottom: 2px solid #e2e8f0;
  font-weight: 600;
  color: #64748b;
  font-size: 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
  border-radius: 8px;
}

#taskListSection.card-custom-role {
  flex: none !important;
}

#taskListSection.manual-height {
  min-height: calc(50vh - 68px) !important;
}

.retention-list-container {
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}

.retention-list-container.schedule-list-height {
  min-height: calc(18vh - 12px) !important;
}

.retention-list-container.manual-list-height {
  min-height: calc(24vh - 14px) !important;
}

.retention-list-container.no-scrollbar::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.retention-list-container.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.retention-list-container::-webkit-scrollbar {
  width: 4px;
}

.retention-list-container::-webkit-scrollbar-track {
  background: transparent;
}

.retention-list-container::-webkit-scrollbar-thumb {
  background-color: #416fd6;
  border-radius: 4px;
}

.retention-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.custom-role-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  transition: all 0.2s;
  cursor: pointer;
}

.custom-role-item:hover {
  background: #fff;
  border-color: #416fd6;
  box-shadow: 0 4px 12px rgba(65, 111, 214, 0.15);
}

.col-no {
  width: 4%;
  flex-shrink: 0;
  font-size: 14px !important;
}

.col-id {
  width: 15%;
  flex-shrink: 0;
  font-size: 14px !important;
}

.col-count {
  width: 12%;
  flex-shrink: 0;
  font-size: 14px !important;
}

.col-time {
  width: 23%;
  flex-shrink: 0;
  font-size: 14px !important;
}

.col-date {
  width: 18%;
  flex-shrink: 0;
  font-size: 14px !important;
}

.col-status {
  width: 13%;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-start;
  font-size: 14px !important;
}

.col-action {
  width: 15%;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  font-size: 14px !important;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

:deep(.select-toggle) { 
  margin-bottom: 0px;
}
</style>
