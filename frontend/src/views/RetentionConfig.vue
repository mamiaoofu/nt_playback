<template>
  <MainLayout>
    <div class="main-wrapper container-fluid-home py-3">
      <div class="row col-lg-12" style="margin-left: -8px;">
        <div class="col-lg-12" style="margin-bottom: 14px;">
          <div class="card">
            <div class="card-body">
              <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 18px;">
                <div class="d-flex align-items-center">
                  <div class="d-flex align-items-center justify-content-center me-1" style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                    <i class="fas fa-trash-alt" style="color:#2b6cb0;font-size:18px"></i>
                  </div>
                  <h5 class="card-title mb-2 mt-1">Retention Settings</h5>
                </div>
              </div>

              <div class="permissions-grid-2">
                <!-- Value Input -->
                <div class="input-group" v-has-value>
                  <input v-model="form.permanent_delete_value" required type="number" name="permanent_delete_value" autocomplete="off" class="input" min="1" max="365" @input="onPermanentDeleteInput($event)">
                  <label class="title-label">Permanent Delete</label>
                </div>

                <!-- Unit Checkboxes -->
                <div class="input-group d-flex align-items-center gap-3" style="flex-direction: row; justify-content: flex-start;">
                  <label class="permission-item" style="margin: 0; cursor: pointer; flex: 0 1 auto !important; min-width: 110px;">
                    <input type="checkbox" :checked="form.permanent_delete_unit === 'minute'" @change="form.permanent_delete_unit = 'minute'" />
                    <span class="perm-checkbox"></span>
                    <span class="perm-label">Minute</span>
                  </label>
                  <label class="permission-item" style="margin: 0; cursor: pointer; flex: 0 1 auto !important; min-width: 110px;">
                    <input type="checkbox" :checked="form.permanent_delete_unit === 'days'" @change="form.permanent_delete_unit = 'days'" />
                    <span class="perm-checkbox"></span>
                    <span class="perm-label">Days</span>
                  </label>
                </div>
              </div>

              <div class="button-group mt-4">
                <button class="btn btn-primary" type="button" @click="triggerSave" :disabled="saving || loading">
                  <i class="fas fa-save"></i> {{ saving ? 'Saving...' : 'Save Settings' }}
                </button>
              </div>
            </div>
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
              <input required v-model="confirmPassword" :type="passwordVisible ? 'text' : 'password'" autocomplete="off" class="input" @keyup.enter="saveChanges" />
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
          <button class="btn btn-primary btn-sm" style="border-radius: 20px; padding: 6px 16px; font-size: 12px;" @click="saveChanges" :disabled="!confirmPassword || saving">
            <i class="fas fa-check"></i> Confirm
          </button>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import MainLayout from '../layouts/MainLayout.vue';
import { showToast } from '../assets/js/function-all';
import { getCsrfToken } from '../api/csrf';

const API_BASE = '/api/v1/retention';
const config = ref(null);
const form = ref({
  permanent_delete_value: 30,
  permanent_delete_unit: 'days'
});

const loading = ref(false);
const saving = ref(false);
const showPasswordModal = ref(false);
const confirmPassword = ref('');
const passwordVisible = ref(false);

const clampPermanentDelete = (val) => {
  if (val === '' || val === null || val === undefined) return '';
  const n = Number(val);
  if (Number.isNaN(n)) return '';
  if (n < 1) return 1;
  if (n > 365) return 365;
  return Math.floor(n);
};

const onPermanentDeleteInput = (e) => {
  const raw = e.target.value;
  if (raw === '') {
    form.value.permanent_delete_value = '';
    return;
  }
  form.value.permanent_delete_value = clampPermanentDelete(raw);
};

const loadConfig = async () => {
  loading.value = true;
  try {
    const res = await axios.get(`${API_BASE}/auto/`, { withCredentials: true });
    if (res.data && res.data.id) {
      config.value = res.data;
      let pdv = res.data.permanent_delete_value !== undefined ? res.data.permanent_delete_value : 30;
      pdv = clampPermanentDelete(pdv) || 30;
      form.value.permanent_delete_value = pdv;
      form.value.permanent_delete_unit = res.data.permanent_delete_unit || 'days';
    }
  } catch (err) {
    console.error("Failed to load retention settings", err);
    showToast("Failed to load settings.", "error");
  } finally {
    loading.value = false;
  }
};

const triggerSave = () => {
  const val = Number(form.value.permanent_delete_value);
  if (!val || val < 1 || val > 365) {
    showToast("Please enter a valid value between 1 and 365.", "error");
    return;
  }
  confirmPassword.value = '';
  passwordVisible.value = false;
  showPasswordModal.value = true;
};

const saveChanges = async () => {
  if (!confirmPassword.value) return;
  const password = confirmPassword.value;
  showPasswordModal.value = false;
  confirmPassword.value = '';
  passwordVisible.value = false;
  saving.value = true;

  try {
    const payload = {
      ...config.value,
      permanent_delete_value: Number(form.value.permanent_delete_value),
      permanent_delete_unit: form.value.permanent_delete_unit,
      password: password
    };

    await axios.put(`${API_BASE}/auto/`, payload, {
      withCredentials: true,
      headers: {
        'X-CSRFToken': getCsrfToken() || ''
      }
    });

    showToast('Retention settings saved successfully.', 'success');
    await loadConfig();
  } catch (err) {
    showToast(err.response?.data?.error || 'Save failed.', 'error');
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  loadConfig();
});
</script>

<style scoped src="../assets/css/user-form.css"></style>
<style scoped>
.permission-item {
  padding: 7px 12px !important;
}
.gap-3 {
  gap: 1rem !important;
}
</style>
