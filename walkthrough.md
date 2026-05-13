# Dashboard Implementation Walkthrough

The dashboard feature has been successfully implemented with all the requested functionalities and the modifications for `is_superuser` and IP addresses.

## What was Changed

### 1. Frontend Updates
- **`auth.store.js` & `useLogin.js`**: Updated to detect if the user `is_superuser`. If true, the system automatically redirects them to `/dashboard` instead of the Home page upon login.
- **`Dashboard.vue`**: Overwritten the existing dummy page with a fully featured Dashboard layout that includes:
  - **Cards:** Total Users (with Role dropdown), Total Audio Plays, Disk Info, and Licenses.
  - **Charts:** Real-time updating CPU and Memory usage graphs utilizing `chart.js` and `vue-chartjs` (dependencies successfully installed).
  - **Alarms Table:** Displays critical events (Failed logins, blocks, etc.), including the **IP Address**, and action buttons to **Kick Out** or **Block IP**.
- **`router/index.js`**: Re-routed `/dashboard` to the new `Dashboard.vue` and ensured the logic handles the superuser edge case properly.
- **`paths.js`**: Added API endpoints for Dashboard queries.

### 2. Backend Updates
- **`models.py` (Authorize):** Added an `IPBlacklist` model to support blocking access from specific IP addresses. Migrations were successfully applied.
- **`dashboard_views.py`**: Created specialized API endpoints for the dashboard:
  - `ApiDashboardStats`: Gathers User Auth counts, `UserLog` Play counts, `psutil` system metrics (CPU, RAM, Disk), and reads the license JSON.
  - `ApiDashboardAlarms`: Queries `UserLog` for `error`, `Failed login`, and `Unauthorized` actions and provides the IP Address.
  - `ApiDashboardAction`: Handles POST requests for actions:
    - **Kick Out:** Blacklists all valid refresh tokens for the given `user_id`.
    - **Block IP:** Adds the target IP to the `IPBlacklist` model.
- **`urls.py`**: Exposed the new dashboard APIs under `/api/dashboard/`.
- **`login/views.py` & `home/views.py`**: Included `is_superuser` in the login payload and the `/home/index/` API so the frontend state knows when the user has admin privileges.

## Verification
- Dependencies (`chart.js`, `vue-chartjs`) were successfully installed via npm.
- Python database migrations for the new `IPBlacklist` table were applied cleanly.
- The Vue routing handles the login bypass accurately for the Superuser.

You can now log in using an account with `is_superuser=True` to test the new redirect and dashboard functionalities!
