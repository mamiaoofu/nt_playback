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
                                        <i class="fas fa-envelope" style="color:#2b6cb0;font-size:18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Mail Settings</h5>
                                </div>
                            </div>

                            <div class="permissions-grid-2">
                                <div class="input-group" v-has-value>
                                    <input v-model="form.host" required type="text" name="host" autocomplete="off" class="input">
                                    <label class="title-label">Host</label>
                                </div>
                                <div class="input-group" v-has-value>
                                    <input v-model="form.port" required type="number" name="port" autocomplete="off" class="input">
                                    <label class="title-label">Port</label>
                                </div>
                                <div class="input-group" v-has-value>
                                    <input v-model="form.fromEmail" required type="email" name="fromEmail" autocomplete="off" class="input">
                                    <label class="title-label">From Email</label>
                                </div>
                                <div class="input-group" style="align-items: center; justify-content: flex-start;">
                                    <label class="permission-item" style="margin: 0;">
                                        <input type="checkbox" v-model="form.tls" />
                                        <span class="perm-checkbox"></span>
                                        <span class="perm-label">Enable TLS</span>
                                    </label>
                                </div>
                                <div class="input-group" v-has-value>
                                    <input v-model="form.username" required type="text" name="username" autocomplete="off" class="input">
                                    <label class="title-label">Username</label>
                                </div>
                                <div class="input-group" v-has-value>
                                    <input v-model="form.password" required type="password" name="password" autocomplete="off" class="input">
                                    <label class="title-label">Password</label>
                                </div>
                            </div>

                            <div class="button-group mt-4">
                                <button class="btn btn-primary" type="button">
                                    <i class="fas fa-save"></i> Save Settings
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
</template>

<script setup>
import { ref } from 'vue'
import MainLayout from '../layouts/MainLayout.vue'

const form = ref({
    host: '',
    port: '',
    tls: false,
    fromEmail: '',
    username: '',
    password: ''
})
</script>
<style>
.permission-item {
    flex: 0 1 292px !important;
    padding: 7px 12px !important;

}
</style>
<style scoped src="../assets/css/user-form.css"></style>
