/* NT License Generator — Frontend Logic */

const API = '';  // same origin

// ─── DOM Elements ──────────────────────────────────────────
const $privateStatus = document.getElementById('private-key-status');
const $publicStatus = document.getElementById('public-key-status');
const $btnGenerateKeys = document.getElementById('btn-generate-keys');
const $btnDownloadPublic = document.getElementById('btn-download-public');
const $keyMessage = document.getElementById('key-message');

const $form = document.getElementById('license-form');
const $licenseMessage = document.getElementById('license-message');

const $outputSection = document.getElementById('output-section');
const $licensePreview = document.getElementById('license-preview');
const $btnDownloadLicense = document.getElementById('btn-download-license');
const $btnCopyLicense = document.getElementById('btn-copy-license');

const $btnVerify = document.getElementById('btn-verify');
const $verifyInput = document.getElementById('verify-input');
const $verifyMessage = document.getElementById('verify-message');

let currentLicense = null;

// ─── Helpers ───────────────────────────────────────────────

function showMessage(el, text, type) {
    el.textContent = text;
    el.className = `message ${type}`;
}

async function api(path, opts = {}) {
    const res = await fetch(`${API}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
    });
    return res.json();
}

// ─── Key Management ────────────────────────────────────────

async function checkKeyStatus() {
    const data = await api('/api/keys-status');

    if (data.has_private_key) {
        $privateStatus.textContent = 'Found';
        $privateStatus.className = 'status-badge status-found';
        $btnDownloadPrivate.disabled = false;
    } else {
        $privateStatus.textContent = 'Not Found';
        $privateStatus.className = 'status-badge status-missing';
        $btnDownloadPrivate.disabled = true;
    }

    if (data.has_public_key) {
        $publicStatus.textContent = 'Found';
        $publicStatus.className = 'status-badge status-found';
        $btnDownloadPublic.disabled = false;
    } else {
        $publicStatus.textContent = 'Not Found';
        $publicStatus.className = 'status-badge status-missing';
        $btnDownloadPublic.disabled = true;
    }
}

$btnGenerateKeys.addEventListener('click', async () => {
    $btnGenerateKeys.disabled = true;
    $btnGenerateKeys.textContent = 'Generating...';
    try {
        const data = await api('/api/generate-keys', { method: 'POST' });
        showMessage($keyMessage, data.message || 'Keys generated.', 'success');
        await checkKeyStatus();
    } catch (e) {
        showMessage($keyMessage, `Error: ${e.message}`, 'error');
    } finally {
        $btnGenerateKeys.disabled = false;
        $btnGenerateKeys.textContent = 'Generate New Keypair';
    }
});

$btnDownloadPublic.addEventListener('click', () => {
    window.open('/api/public-key', '_blank');
});

const $btnDownloadPrivate = document.getElementById('btn-download-private');
const $btnImportPrivate = document.getElementById('btn-import-private');
const $importKeyInput = document.getElementById('import-key-input');

$btnDownloadPrivate.addEventListener('click', () => {
    window.open('/api/download-private-key', '_blank');
});

$btnImportPrivate.addEventListener('click', () => {
    $importKeyInput.value = '';
    $importKeyInput.click();
});

$importKeyInput.addEventListener('change', async () => {
    const file = $importKeyInput.files[0];
    if (!file) return;

    $btnImportPrivate.disabled = true;
    $btnImportPrivate.textContent = 'Importing...';

    try {
        const formData = new FormData();
        formData.append('private_key', file);

        const res = await fetch(`${API}/api/import-keys`, {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();

        if (res.ok) {
            showMessage($keyMessage, data.message, 'success');
            await checkKeyStatus();
        } else {
            showMessage($keyMessage, data.error || 'Import failed.', 'error');
        }
    } catch (e) {
        showMessage($keyMessage, `Error: ${e.message}`, 'error');
    } finally {
        $btnImportPrivate.disabled = false;
        $btnImportPrivate.textContent = '📂 Import Private Key';
    }
});

// ─── License Generation ────────────────────────────────────

$form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fingerprint = document.getElementById('fingerprint').value.trim();
    const licenseId = document.getElementById('license-id').value.trim();
    const customerName = document.getElementById('customer-name').value.trim();
    const expiry = document.getElementById('expiry').value;
    const maxMainDb = parseInt(document.getElementById('max-main-db').value, 10);
    const maxConcurrent = parseInt(document.getElementById('max-concurrent').value, 10);
    const allowedMenusRaw = document.getElementById('allowed-menus').value.trim();
    const configFlagsRaw = document.getElementById('config-flags').value.trim();

    // Parse allowed menus
    const allowedMenus = allowedMenusRaw
        ? allowedMenusRaw.split(',').map(s => s.trim()).filter(Boolean)
        : [];

    // Parse config flags
    let configFlags = {};
    if (configFlagsRaw) {
        try {
            configFlags = JSON.parse(configFlagsRaw);
        } catch {
            showMessage($licenseMessage, 'Invalid JSON in Config Flags.', 'error');
            return;
        }
    }

    const payload = {
        fingerprint,
        license_id: licenseId,
        customer_name: customerName,
        expiry: `${expiry}T23:59:59Z`,
        max_main_db: maxMainDb,
        max_concurrent_users: maxConcurrent,
        allowed_menus: allowedMenus,
        config_flags: configFlags,
    };

    const btn = document.getElementById('btn-generate-license');
    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
        const data = await api('/api/generate-license', {
            method: 'POST',
            body: JSON.stringify(payload),
        });

        if (data.error) {
            showMessage($licenseMessage, data.error, 'error');
            return;
        }

        currentLicense = data.license;
        $licensePreview.textContent = JSON.stringify(data.license, null, 2);
        $outputSection.style.display = '';
        showMessage($licenseMessage, `License generated! Files saved to: ${data.output_path} (license.json, public_key.pem, fingerprint.txt). Run "python build_installer.py" to create installer .exe`, 'success');
    } catch (e) {
        showMessage($licenseMessage, `Error: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate License';
    }
});

// ─── Output Actions ────────────────────────────────────────

$btnDownloadLicense.addEventListener('click', () => {
    if (!currentLicense) return;
    const blob = new Blob([JSON.stringify(currentLicense, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'license.json';
    a.click();
    URL.revokeObjectURL(url);
});

$btnCopyLicense.addEventListener('click', async () => {
    if (!currentLicense) return;
    try {
        await navigator.clipboard.writeText(JSON.stringify(currentLicense, null, 2));
        $btnCopyLicense.textContent = 'Copied!';
        setTimeout(() => { $btnCopyLicense.textContent = 'Copy to Clipboard'; }, 2000);
    } catch {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = JSON.stringify(currentLicense, null, 2);
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        $btnCopyLicense.textContent = 'Copied!';
        setTimeout(() => { $btnCopyLicense.textContent = 'Copy to Clipboard'; }, 2000);
    }
});

// ─── Verify License ────────────────────────────────────────

$btnVerify.addEventListener('click', async () => {
    const raw = $verifyInput.value.trim();
    if (!raw) {
        showMessage($verifyMessage, 'Please paste license JSON.', 'error');
        return;
    }

    let licenseObj;
    try {
        licenseObj = JSON.parse(raw);
    } catch {
        showMessage($verifyMessage, 'Invalid JSON format.', 'error');
        return;
    }

    try {
        const data = await api('/api/verify-license', {
            method: 'POST',
            body: JSON.stringify(licenseObj),
        });
        showMessage($verifyMessage, data.message, data.valid ? 'success' : 'error');
    } catch (e) {
        showMessage($verifyMessage, `Error: ${e.message}`, 'error');
    }
});

// ─── Download Installer ────────────────────────────────────

const $btnDownloadExisting = document.getElementById('btn-download-existing');
const $installerStatus = document.getElementById('installer-status');
const $installerMessage = document.getElementById('installer-message');

async function checkInstallerStatus() {
    try {
        const data = await api('/api/installer-status');
        if (data.exists) {
            $installerStatus.innerHTML = `<span class="status-badge status-found">Download ready (${data.size_mb} MB)</span>`;
            $btnDownloadExisting.disabled = false;
        } else {
            $installerStatus.innerHTML = `<span class="status-badge status-missing">No installer — run: python build_installer.py</span>`;
            $btnDownloadExisting.disabled = true;
        }
    } catch {
        $installerStatus.innerHTML = '';
    }
}

$btnDownloadExisting.addEventListener('click', () => {
    window.open('/api/download-installer', '_blank');
});

// ─── Init ──────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    checkKeyStatus();
    checkInstallerStatus();

    // Set default expiry to 1 year from now
    const d = new Date();
    d.setFullYear(d.getFullYear() + 1);
    document.getElementById('expiry').value = d.toISOString().split('T')[0];
});
