import { getRuntime } from './runtimeConfig'

const ENV_API_BASE = import.meta.env.VITE_API_BASE || 'http://172.27.96.1:8080'

export const getApiBase = () => getRuntime('VITE_API_BASE', ENV_API_BASE)

// GET csrf
export const API_GET_CSRF = () => `${getApiBase()}/api/get/csrf/`

// หน้า Home
export const API_HOME_INDEX = () => `${getApiBase()}/api/home/index/`
export const API_AUDIO_LIST = () => `${getApiBase()}/api/audio/list/`
export const API_PLAY_AUDIO = (fileId) => `${getApiBase()}/api/audio/play/${fileId}/`
export const API_PROXY_AUDIO = (fileName) => `${getApiBase()}/api/audio/proxy/?file=${encodeURIComponent(fileName || '')}`
export const API_CHECK_MY_FAVORITE_NAME = () => `${getApiBase()}/api/home/check/my-favorite-search/`
export const API_ADD_MY_FAVORITE_SEARCH = () => `${getApiBase()}/api/home/add/my-favorite-search/`
export const API_EDIT_MY_FAVORITE_SEARCH = (myfavoriteId) => `${getApiBase()}/api/home/edit/my-favorite-search/${myfavoriteId}/`
export const API_LOG_PLAY_AUDIO = () => `${getApiBase()}/api/log/play-audio/`
export const API_GET_CREDENTIALS = () => `${getApiBase()}/api/get/credentials/`
export const API_GET_STORAGE_CONFIG = () => `${getApiBase()}/api/storage-config/`
export const API_LOG_SAVE_FILE = () => `${getApiBase()}/api/log/save-file/`
export const API_LOG_USER_ACTION = () => `${getApiBase()}/api/log/user-action/`
export const API_CREATE_FILE_SHARE = () => `${getApiBase()}/api/file-share/create/`
export const API_CHECK_FILE_SHARE = () => `${getApiBase()}/api/file-share/check/`

// หน้า Login
export const API_LOGIN = () => `${getApiBase()}/login/`
export const API_LOGOUT = () => `${getApiBase()}/api/logout/`

// หน้า Role
export const API_INDEX_ROLE = () => `${getApiBase()}/api/role/index/`
export const API_GET_DETAILS_ROLE = () => `${getApiBase()}/api/role/get-details/`
export const API_CHECK_ROLE_NAME = () => `${getApiBase()}/api/role/check/role-name/`
export const API_CREATE_ROLE = () => `${getApiBase()}/api/role/create/`
export const API_UPDATE_ROLE = (roleId) => `${getApiBase()}/api/role/edit/${roleId}/`
export const API_DELETE_ROLE = (roleId) => `${getApiBase()}/api/role/delete/${roleId}/`

// หน้า  Group and Team
export const API_GROUP_INDEX = () => `${getApiBase()}/api/group/index/`
export const API_TEAM_INDEX = () => `${getApiBase()}/api/team/index/`
export const API_GET_TEAM_BY_GROUP = (groupId) => `${getApiBase()}/api/group/get/team-by-group/${groupId}/`
export const API_GET_DATABASE = () => `${getApiBase()}/api/get/database/`
export const API_CHECK_GROUP_NAME = () => `${getApiBase()}/api/group/check/group-name/`
export const API_CHECK_TEAM_NAME = () => `${getApiBase()}/api/team/check/team-name/`
export const API_SAVE_GROUP = () => `${getApiBase()}/api/group/save/`
export const API_SAVE_TEAM = () => `${getApiBase()}/api/team/save/`

// หน้า  User Management
export const API_GET_USER = () => `${getApiBase()}/api/get/user/`
export const API_GET_USER_ALL = (type) => `${getApiBase()}/api/get/user-all/${type}/`
export const API_USER_MANAGEMENT_CHANGE_STATUS = (id) => `${getApiBase()}/api/user-management/change-status/${id}/`
export const API_DELETE_USER = (id) => `${getApiBase()}/api/user-management/delete-user/${id}/`
export const API_RESET_PASSWORD = (id) => `${getApiBase()}/api/user-management/reset-password/${id}/`

// หน้า log user
export const API_GET_LOG_USER = (type) => `${getApiBase()}/api/log-user/get-log/${type}/`

// หน้า Add User
export const API_GET_ALL_ROLES_PERMISSIONS = () => `${getApiBase()}/api/add-user/get-all-roles-permissions/`
export const API_GET_USER_PROFILE = (id) => `${getApiBase()}/api/user-management/get-profile/${id}/`
export const API_CHECK_USERNAME = () => `${getApiBase()}/api/add-user/check-username/`
export const API_CREATE_USER = () => `${getApiBase()}/api/add-user/`
export const API_UPDATE_USER = (id) => `${getApiBase()}/api/edit-user/${id}/`
export const API_GET_AD_USERS = () => `${getApiBase()}/api/user-management/ad-users/`

// หน้า Settings
export const API_SETTINGS_INDEX = () => `${getApiBase()}/api/settings/index/`
export const API_UPDATE_SETTINGS = () => `${getApiBase()}/api/settings/update/`
export const API_GET_COLUMN_AUDIO_RECORD = () => `${getApiBase()}/api/setting/get/column-audio-record/`
export const API_SAVE_COLUMN_AUDIO_RECORD = () => `${getApiBase()}/api/setting/save/column-audio-record/`

// หน้า Profile
export const API_CHANGE_PASSWORD = () => `${getApiBase()}/api/change-password/`

// หน้า Ticket History
export const API_GET_USER_TICKET = (type) => `${getApiBase()}/api/get/ticket-history/${type}/`
export const API_FILE_SHARE_MANAGEMENT_CHANGE_STATUS = (id, type) => `${getApiBase()}/api/file-share-management/change-status/${id}/${type}/`
export const API_SEND_EMAIL = () => `${getApiBase()}/api/send-share-email/`
export const API_GEN_FORM_TICKET = () => `${getApiBase()}/api/gen-form-ticket/`

// License
export const API_LICENSE_INFO = () => `${getApiBase()}/api/license-info/`

// Dashboard
export const API_DASHBOARD_STATS = () => `${getApiBase()}/api/dashboard/stats/`
export const API_DASHBOARD_ALARMS = () => `${getApiBase()}/api/dashboard/alarms/`
export const API_DASHBOARD_ACTION = () => `${getApiBase()}/api/dashboard/action/`