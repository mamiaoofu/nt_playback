<template>
    <MainLayout>
        <div class="main-wrapper container-fluid-home py-3">
            <div class="row col-lg-12" style="margin-left: -8px;">
                <div class="col-lg-12">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start justify-content-between" style="margin-bottom: 18px;">
                                <div class="d-flex align-items-center">
                                    <div class="d-flex align-items-center justify-content-center me-1" style="width:35px;height:35px;background-color: #D9E2F6;border-radius: 10px !important;">
                                        <i class="fas fa-sitemap" style="color:#2b6cb0;font-size:18px"></i>
                                    </div>
                                    <h5 class="card-title mb-2 mt-1">Active Directory</h5>
                                </div>
                            </div>

                            <div class="permissions-grid-2">
                                <div class="input-group" v-has-value>
                                    <input v-model="form.host" required type="text" name="host" autocomplete="off" class="input">
                                    <label class="title-label">Host</label>
                                </div>
                                <div class="input-group" v-has-value>
                                    <input v-model="form.domain" required type="text" name="domain" autocomplete="off" class="input">
                                    <label class="title-label">Domain</label>
                                </div>
                                <div class="input-group" v-has-value style="grid-column: span 2;">
                                    <input v-model="form.baseDn" required type="text" name="baseDn" autocomplete="off" class="input">
                                    <label class="title-label">Base DN</label>
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
                                    <i class="fas fa-save"></i> Save Changes
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
    domain: '',
    baseDn: '',
    username: '',
    password: ''
})
</script>

<style scoped src="../assets/css/user-form.css"></style>
