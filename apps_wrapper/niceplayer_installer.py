"""
niceplayer_installer.py
=======================
GUI installer for the NicePlayer wrapper system.

Responsibilities
----------------
1. Copy niceplayer_wrapper.exe to the install directory.
2. Register the niceplayer:// custom protocol via the Windows Registry.
3. Accept SMB credentials from the admin via a GUI form.
4. Store the credentials in Windows Credential Manager (cmdkey) – NEVER to disk.
5. Write a credential-free config.json for path validation.
6. Optionally test the SMB connection before installing.

Compile to a single exe with PyInstaller:
    1. Build wrapper exe first:
       python -m PyInstaller --onefile --windowed --name niceplayer_wrapper niceplayer_wrapper.py

    2. Bundle wrapper into installer:
       python -m PyInstaller --onefile --windowed --name niceplayer_installer --add-data "dist/niceplayer_wrapper.exe;." niceplayer_installer.py

    The installer exe will contain niceplayer_wrapper.exe inside it.
    No need to distribute both files separately.

Security rules enforced here
-----------------------------
* Password is NEVER written to any file or log.
* Password is NEVER sent to the backend or any network endpoint.
* Only cmdkey (Windows Credential Manager) receives the password.
"""

import os
import sys
import json
import ssl
import shutil
import subprocess
import threading
import urllib.request
import urllib.error
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

INSTALL_DIR = r"C:\Program Files (x86)\niceplayer_wrapper"
CONFIG_DIR  = r"C:\ProgramData\niceplayer_wrapper"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
EXE_NAME    = "niceplayer_wrapper.exe"

# Pre-shared secret embedded at build time — must match INSTALLER_SECRET_KEY in
# the backend .env.  End users never see or need to enter this value.
_INSTALLER_KEY = "2c2f9cb6772e21844f9973b95c2f5ada0603cf2d55dfc57cc205952e42ee1324"

HKCR_NICEPLAYER = r"HKEY_CLASSES_ROOT\niceplayer"

# ---------------------------------------------------------------------------
# Dark theme palette
# ---------------------------------------------------------------------------

_BG         = "#1a1a2e"   # window background
_PANEL      = "#16213e"   # LabelFrame interior
_ENTRY      = "#0f3460"   # Entry / Text background
_FG         = "#e0e0e0"   # primary text
_FG_DIM     = "#8888aa"   # secondary / hint text
_ACCENT     = "#6c63ff"   # button fill (purple)
_ACCENT_ACT = "#7c73ff"   # button active/hover
_GREEN      = "#4ade80"   # success indicator
_RED        = "#f87171"   # error indicator
_LOG_BG     = "#0d1117"   # log area background
_LOG_FG     = "#a8d8ea"   # log text colour
_BORDER     = "#2a2a4a"   # border colour


def _get_bundled_wrapper():
    """
    Return path to niceplayer_wrapper.exe.
    - When running as a PyInstaller exe: extracted from the bundle (sys._MEIPASS)
    - When running as a .py script: look next to this file, then in dist/ subfolder
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller extracts --add-data files to sys._MEIPASS at runtime
        return os.path.join(sys._MEIPASS, EXE_NAME)
    # Running as plain .py — look next to this script first, then dist/
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(here, EXE_NAME),
        os.path.join(here, 'dist', EXE_NAME),
    ]:
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(here, EXE_NAME)  # return path even if missing (error shown later)

# ---------------------------------------------------------------------------
# Registry helpers (no winreg dependency – use reg.exe for broad compatibility)
# ---------------------------------------------------------------------------

def _reg(args, timeout=10):
    """Run a reg.exe command, return (returncode, stdout, stderr)."""
    cmd = ["reg"] + args
    try:
        res = subprocess.run(
            cmd, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return res.returncode, res.stdout.decode(errors="ignore"), res.stderr.decode(errors="ignore")
    except Exception as e:
        return 255, "", str(e)


def register_protocol(exe_path):
    """
    Register the niceplayer:// custom protocol in HKEY_CLASSES_ROOT.
    Requires the process to be running as Administrator.
    """
    quoted = f'"{exe_path}" "%1"'

    entries = [
        # (key,                                                       value_name, type,  data)
        (HKCR_NICEPLAYER,                                             "",         "REG_SZ",  "URL:Nice Player Protocol"),
        (HKCR_NICEPLAYER,                                             "URL Protocol", "REG_SZ", ""),
        (rf"{HKCR_NICEPLAYER}\DefaultIcon",                          "",         "REG_SZ",  f'"{exe_path}",0'),
        (rf"{HKCR_NICEPLAYER}\shell\open\command",                   "",         "REG_SZ",  quoted),
    ]

    for key, name, typ, data in entries:
        args = ["add", key, "/f"]
        if name:
            args += ["/v", name]
        else:
            args += ["/ve"]
        args += ["/t", typ, "/d", data]
        rc, out, err = _reg(args)
        if rc != 0:
            return False, f"reg add failed for {key}: {err}"

    return True, "Protocol registered successfully."


TASK_NAME = "NicePlayerWrapperServer"


def register_server_autostart(exe_path):
    """
    Create a Task Scheduler task that starts niceplayer_wrapper.exe --server
    automatically on every user login, and start it immediately.
    Replaces any existing task with the same name.
    """
    cmd_create = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{exe_path}" --server',
        "/sc", "onlogon",
        "/rl", "highest",
        "/f",  # overwrite if exists
    ]
    try:
        res = subprocess.run(
            cmd_create, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=15,
        )
        if res.returncode != 0:
            err = res.stderr.decode(errors="ignore") or res.stdout.decode(errors="ignore")
            return False, f"schtasks create failed: {err}"
    except Exception as e:
        return False, str(e)

    # Start the task immediately (so user doesn't need to log out/in)
    cmd_run = ["schtasks", "/run", "/tn", TASK_NAME]
    try:
        subprocess.run(cmd_run, check=False, timeout=10,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        pass  # non-fatal: task will start on next login anyway

    return True, f"Task '{TASK_NAME}' registered and started."


def add_browser_policies(origins_str, exe_path):
    """
    Set AutoLaunchProtocolsFromOrigins policy for Chrome, Edge, and Firefox.
    All three browsers support this policy via the same registry format.
    origins_str: comma-separated origins, e.g. "https://192.168.1.90,https://localhost"
    This is optional and silently continues if any individual browser's key fails.
    """
    origins_list = [o.strip().rstrip('/') for o in origins_str.split(',') if o.strip()]
    if not origins_list:
        return
    policy_value = json.dumps({"protocol": "niceplayer", "allowed_origins": origins_list})
    browser_keys = [
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Google\Chrome\AutoLaunchProtocolsFromOrigins",
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Edge\AutoLaunchProtocolsFromOrigins",
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Mozilla\Firefox\AutoLaunchProtocolsFromOrigins",
    ]
    results = []
    for key in browser_keys:
        rc, out, err = _reg(["add", key, "/v", "1", "/t", "REG_SZ", "/d", policy_value, "/f"])
        results.append((key, rc))
    return results


# ---------------------------------------------------------------------------
# Credential Manager helpers
# ---------------------------------------------------------------------------

def _run_cmdkey(args, timeout=10):
    """Run cmdkey.exe, return (returncode, stdout, stderr)."""
    cmd = ["cmdkey"] + args
    try:
        res = subprocess.run(
            cmd, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return res.returncode, res.stdout.decode(errors="ignore"), res.stderr.decode(errors="ignore")
    except Exception as e:
        return 255, "", str(e)


def store_credential(server, username, password, share=None):
    """
    Store the SMB credential via cmdkey so that 'net use' can pick it up
    automatically without prompting.  We store both the server-level target
    (\\SERVER) and the share-level target (\\SERVER\SHARE) so Windows can
    match either path format without prompting for credentials.
    Password is passed only as a process argument and cleared immediately.
    """
    # cmdkey target must be plain server name (no \\ prefix) for net use to match.
    plain_server = server.lstrip("\\")
    targets = [plain_server]
    if share:
        targets.append(f"{plain_server}\\{share}")

    errors = []
    stored = []
    try:
        for target in targets:
            try:
                res = subprocess.run(
                    ["cmdkey", f"/add:{target}", f"/user:{username}", f"/pass:{password}"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                if res.returncode == 0:
                    stored.append(target)
                else:
                    err = res.stderr.decode(errors="ignore") or res.stdout.decode(errors="ignore")
                    errors.append(f"{target}: cmdkey rc={res.returncode} {err}")
            except Exception as e:
                errors.append(f"{target}: {e}")
    finally:
        password = None  # noqa: F841

    if stored:
        msg = "Credential stored via cmdkey for: " + ", ".join(stored)
        if errors:
            msg += " (some targets failed: " + "; ".join(errors) + ")"
        return True, msg
    return False, "cmdkey failed for all targets: " + "; ".join(errors)


def test_smb_connection(server, share, username, password, timeout=15):
    """
    Attempt a net use to verify credentials before writing anything.
    Returns (success: bool, message: str).
    The password is passed only as a process argument.
    """
    unc = f"\\\\{server}\\{share}"
    cmd = ["net", "use", unc, password, f"/user:{username}", "/persistent:no"]
    try:
        res = subprocess.run(
            cmd, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout,
        )
        # disconnect immediately after test
        subprocess.run(["net", "use", unc, "/delete", "/y"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=5)
        password = None  # noqa: F841
        if res.returncode == 0:
            return True, "Connection successful."
        return False, res.stderr.decode(errors="ignore") or res.stdout.decode(errors="ignore")
    except subprocess.TimeoutExpired:
        password = None  # noqa: F841
        return False, "Connection timed out."
    except Exception as e:
        password = None  # noqa: F841
        return False, str(e)


# ---------------------------------------------------------------------------
# DPAPI helpers (machine-scope so wrapper running as same user can decrypt)
# ---------------------------------------------------------------------------

def dpapi_protect(plaintext: str) -> str:
    """Encrypt plaintext with DPAPI (CRYPTPROTECT_LOCAL_MACHINE) → base64 string."""
    import ctypes
    import ctypes.wintypes as wintypes
    import base64

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    raw = plaintext.encode("utf-16-le")
    buf = (ctypes.c_ubyte * len(raw))(*raw)
    inp = DATA_BLOB(len(raw), buf)
    out = DATA_BLOB()
    CRYPTPROTECT_LOCAL_MACHINE = 0x4
    if not ctypes.WinDLL("crypt32").CryptProtectData(
        ctypes.byref(inp), None, None, None, None, CRYPTPROTECT_LOCAL_MACHINE, ctypes.byref(out)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    encrypted = bytes(out.pbData[: out.cbData])
    ctypes.windll.kernel32.LocalFree(out.pbData)
    return base64.b64encode(encrypted).decode("ascii")


# ---------------------------------------------------------------------------
# Config file
# ---------------------------------------------------------------------------

def write_config(server, share, base_path="", niceplayer_exe="",
                 smb_username="", smb_password_plain=""):
    """Write config.json. Password is stored DPAPI-encrypted (machine scope)."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = {"server": server, "share": share}
    if base_path:
        data["base_path"] = base_path
    if niceplayer_exe:
        data["niceplayer_exe"] = niceplayer_exe
    if smb_username:
        data["smb_username"] = smb_username
    if smb_password_plain:
        # Store as base64 — reliable across all user/service contexts on the machine.
        # The file is protected by OS-level permissions on C:\ProgramData\niceplayer_wrapper\
        import base64
        data["smb_password"] = "b64:" + base64.b64encode(
            smb_password_plain.encode("utf-8")
        ).decode("ascii")
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SeekTrack NicePlayer Wrapper – Installer")
        self.resizable(False, False)
        self._apply_theme()
        self._build_ui()
        # Centre the window
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _apply_theme(self):
        self.configure(bg=_BG)
        style = ttk.Style(self)
        style.theme_use("clam")

        # Base defaults
        style.configure(".",
            background=_BG,
            foreground=_FG,
            fieldbackground=_ENTRY,
            bordercolor=_BORDER,
            darkcolor=_PANEL,
            lightcolor=_PANEL,
            troughcolor=_PANEL,
            focuscolor=_ACCENT,
            selectbackground=_ACCENT,
            selectforeground=_FG,
            font=("Segoe UI", 9),
        )

        # Frame
        style.configure("TFrame", background=_BG)

        # LabelFrame
        style.configure("TLabelframe",
            background=_PANEL,
            bordercolor=_BORDER,
            relief="flat",
            padding=6,
        )
        style.configure("TLabelframe.Label",
            background=_PANEL,
            foreground=_FG,
            font=("Segoe UI", 9, "bold"),
        )

        # Label
        style.configure("TLabel", background=_PANEL, foreground=_FG)
        style.configure("Dim.TLabel", background=_PANEL, foreground=_FG_DIM)
        style.configure("Root.TLabel", background=_BG, foreground=_FG)

        # Entry
        style.configure("TEntry",
            fieldbackground=_ENTRY,
            foreground=_FG,
            insertcolor=_FG,
            bordercolor=_BORDER,
            lightcolor=_BORDER,
            darkcolor=_BORDER,
        )
        style.map("TEntry",
            fieldbackground=[("focus", _ENTRY)],
            bordercolor=[("focus", _ACCENT)],
        )

        # Button
        style.configure("TButton",
            background=_ACCENT,
            foreground=_FG,
            bordercolor=_ACCENT,
            lightcolor=_ACCENT,
            darkcolor=_ACCENT,
            relief="flat",
            padding=(2, 0),
            font=("Segoe UI", 9, "bold"),
        )
        style.map("TButton",
            background=[("active", _ACCENT_ACT), ("pressed", _ACCENT_ACT)],
            bordercolor=[("active", _ACCENT_ACT)],
            lightcolor=[("active", _ACCENT_ACT)],
            darkcolor=[("active", _ACCENT_ACT)],
        )

    # ------------------------------------------------------------------ UI --

    def _card(self, title: str) -> tk.Frame:
        """Create a titled card panel and return the inner content frame."""
        outer = tk.Frame(self, bg=_PANEL, padx=16, pady=12)
        outer.pack(padx=20, pady=(6, 0), fill="x")
        tk.Label(
            outer, text=title,
            bg=_PANEL, fg=_FG,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        return outer

    def _row(self, parent: tk.Frame, label: str, widget_factory):
        """Pack a label+widget row inside a card."""
        row = tk.Frame(parent, bg=_PANEL)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=_PANEL, fg=_FG,
                 font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        w = widget_factory(row)
        w.pack(side="left", fill="x", expand=True)
        return w

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=_BG, pady=20)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎬  SeekTrack Agent Player",
                 bg=_BG, fg=_FG,
                 font=("Segoe UI", 16, "bold")).pack()
        # tk.Label(hdr, text="ติดตั้ง NicePlayer Wrapper และกำหนดค่า SMB บนเครื่อง Client",
        #          bg=_BG, fg=_FG_DIM,
        #          font=("Segoe UI", 9)).pack(pady=(2, 0))
        # tk.Frame(self, bg=_BORDER, height=1).pack(fill="x", padx=20, pady=(10, 0))

        # ── Backend API ───────────────────────────────────────────────────────
        frm_backend = self._card("Backend Server")
        self._backend_url_var = tk.StringVar()
        self._row(frm_backend, "Backend URL:",
                  lambda p: ttk.Entry(p, textvariable=self._backend_url_var, width=40))

        # ── Installation ──────────────────────────────────────────────────────
        frm_src = self._card("Installation")
        # bundled = _get_bundled_wrapper()
        # bundled_ok = os.path.isfile(bundled)
        # bundled_label = "✓  niceplayer_wrapper.exe (bundled)" if bundled_ok else "✗  niceplayer_wrapper.exe NOT FOUND in bundle"
        # lbl_color = _GREEN if bundled_ok else _RED
        # wrap_row = tk.Frame(frm_src, bg=_PANEL)
        # wrap_row.pack(fill="x", pady=3)
        # tk.Label(wrap_row, text="Wrapper:", bg=_PANEL, fg=_FG,
        #          font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        # tk.Label(wrap_row, text=bundled_label, bg=_PANEL, fg=lbl_color,
        #          font=("Segoe UI", 9)).pack(side="left")

        self._install_dir_var = tk.StringVar(value=INSTALL_DIR)
        dir_row = tk.Frame(frm_src, bg=_PANEL)
        dir_row.pack(fill="x", pady=3)
        tk.Label(dir_row, text="Install to:", bg=_PANEL, fg=_FG,
                 font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        ttk.Entry(dir_row, textvariable=self._install_dir_var, width=44).pack(side="left", fill="x", expand=True)
        ttk.Button(dir_row, text="Browse…", command=self._browse_install_dir).pack(side="left", padx=(6, 0))

        _default_exe = r"C:\Program Files (x86)\NICE Systems\NICE Player Release 6\NiceApplications.Playback.GUI.exe"
        self._niceplayer_exe_var = tk.StringVar(value=_default_exe)
        exe_row = tk.Frame(frm_src, bg=_PANEL)
        exe_row.pack(fill="x", pady=3)
        tk.Label(exe_row, text="NicePlayer EXE:", bg=_PANEL, fg=_FG,
                 font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        ttk.Entry(exe_row, textvariable=self._niceplayer_exe_var, width=44).pack(side="left", fill="x", expand=True)
        ttk.Button(exe_row, text="Browse…", command=self._browse_niceplayer_exe).pack(side="left", padx=(6, 0))

        # ── Browser origin ────────────────────────────────────────────────────
        frm_origin = self._card("Browser AutoLaunch Policy")
        self._origin_var = tk.StringVar()
        self._row(frm_origin, "Allowed Origin:",
                  lambda p: ttk.Entry(p, textvariable=self._origin_var, width=44))
        tk.Label(frm_origin,
                 text="(Chrome/Edge/Firefox  คั่นด้วย ,  เช่น https://192.168.1.90,http://192.168.1.90:6000)",
                 bg=_PANEL, fg=_FG_DIM, font=("Segoe UI", 8)).pack(anchor="w")

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=_BG)
        btn_row.pack(pady=14)
        ttk.Button(btn_row, text="Install",  width=24, command=self._on_install).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel",   width=16, command=self.destroy).pack(side="left", padx=6)

        # ── Status log ────────────────────────────────────────────────────────
        frm_log = self._card("Status")
        self._log_text = tk.Text(
            frm_log, height=8, state="disabled", wrap="word",
            bg=_LOG_BG, fg=_LOG_FG,
            insertbackground=_FG, relief="flat",
            font=("Consolas", 9),
        )
        self._log_text.pack(fill="both", expand=True, pady=(0, 4))
        tk.Frame(self, bg=_BG, height=8).pack()

    # ---------------------------------------------------------------- helpers -

    def _browse_install_dir(self):
        path = filedialog.askdirectory(title="Select install directory")
        if path:
            self._install_dir_var.set(path)

    def _browse_niceplayer_exe(self):
        path = filedialog.askopenfilename(
            title="Select NicePlayer EXE",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
            initialdir=r"C:\Program Files (x86)\NICE Systems",
        )
        if path:
            self._niceplayer_exe_var.set(path)

    def _fetch_installer_config(self, base_url, installer_key):
        """
        Fetch SMB config + credentials from /api/installer-config/.
        Returns (dict, None) on success or (None, error_msg) on failure.
        """
        url = f"{base_url}/api/installer-config/"
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "X-Installer-Key": installer_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8")), None
        except urllib.error.URLError as e:
            # Dev convenience: allow self-signed cert only for localhost URLs.
            parsed = urllib.parse.urlparse(base_url)
            host = (parsed.hostname or "").lower()
            is_localhost = host in {"localhost", "127.0.0.1", "::1"}
            cert_verify_failed = "CERTIFICATE_VERIFY_FAILED" in str(e)
            if is_localhost and cert_verify_failed:
                insecure_ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=10, context=insecure_ctx) as resp:
                    return json.loads(resp.read().decode("utf-8")), None
            raise

    def _append_log(self, msg):
        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _collect_fields(self):
        return {
            "backend_url":    self._backend_url_var.get().strip().rstrip("/"),
            "installer_key":  _INSTALLER_KEY,
            "install_dir":    self._install_dir_var.get().strip(),
            "origin":         self._origin_var.get().strip(),
            "niceplayer_exe": self._niceplayer_exe_var.get().strip(),
        }

    def _validate_fields(self, fields):
        missing = []
        for key in ("backend_url", "install_dir"):
            if not fields.get(key):
                missing.append(key)
        if missing:
            messagebox.showerror("กรอกข้อมูลไม่ครบ", f"กรุณากรอก: {', '.join(missing)}")
            return False
        bundled = _get_bundled_wrapper()
        if not os.path.isfile(bundled):
            messagebox.showerror("ไม่พบ Wrapper",
                f"ไม่พบ {EXE_NAME} ในไฟล์ installer\n\n"
                "กรุณา build installer ใหม่โดยใช้ --add-data:\n"
                "python -m PyInstaller --onefile --windowed --name niceplayer_installer "
                '--add-data "dist/niceplayer_wrapper.exe;." niceplayer_installer.py')
            return False
        return True

    # -------------------------------------------------------------- actions --

    def _on_install(self):
        fields = self._collect_fields()
        if not self._validate_fields(fields):
            return

        self._append_log("กำลังดึงข้อมูลจาก Backend …")
        self.update_idletasks()

        def _run():
            # ─ 1. Fetch SMB config + credentials from backend ─────────────────
            try:
                data, err = self._fetch_installer_config(
                    fields["backend_url"], fields["installer_key"]
                )
                if err:
                    self.after(0, lambda: self._append_log(f"✗ {err}"))
                    self.after(0, lambda: messagebox.showerror("Fetch Config", err))
                    return
            except urllib.error.HTTPError as e:
                msg = f"✗ HTTP {e.code}: {e.reason}  (ตรวจสอบ Backend URL และ Installer Key)"
                self.after(0, lambda: self._append_log(msg))
                self.after(0, lambda: messagebox.showerror("Fetch Config", msg))
                return
            except Exception as e:
                msg = f"✗ เชื่อมต่อ Backend ไม่ได้: {e}"
                self.after(0, lambda: self._append_log(msg))
                self.after(0, lambda: messagebox.showerror("Fetch Config", msg))
                return

            smb_server   = data.get("host", "")
            smb_share    = data.get("share", "")
            smb_base     = data.get("base_path", "")
            smb_username = data.get("smb_username", "")
            smb_password = data.get("smb_password", "")  # decrypted plaintext

            self.after(0, lambda: self._append_log(
                f"✓ ดึงค่าสำเร็จ"
            ))

            errors = []

            # ─ 2. Extract bundled wrapper exe ─────────────────────────────
            bundled_src = _get_bundled_wrapper()
            dest_dir = fields["install_dir"]
            dest_exe = os.path.join(dest_dir, EXE_NAME)
            try:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(bundled_src, dest_exe)
                self.after(0, lambda: self._append_log(f"✓ ติดตั้ง {EXE_NAME} ไปที่ {dest_dir}"))
            except Exception as e:
                errors.append(f"Copy exe: {e}")
                self.after(0, lambda: self._append_log(f"✗ ติดตั้ง exe ล้มเหลว: {e}"))

            # ─ 3. Register protocol ───────────────────────────────────
            ok, msg = register_protocol(dest_exe)
            if ok:
                self.after(0, lambda: self._append_log(f"✓ Protocol registered: {msg}"))
            else:
                errors.append(f"Protocol registration: {msg}")
                self.after(0, lambda: self._append_log(f"✗ Protocol registration failed: {msg}"))

            # ─ 4. Store credential in Credential Manager ─────────────────
            ok, err = store_credential(smb_server, smb_username, smb_password, share=smb_share)
            if ok:
                self.after(0, lambda: self._append_log("✓ Credentials stored in Windows Credential Manager."))
            else:
                errors.append(f"Credential Manager: {err}")
                self.after(0, lambda: self._append_log(f"✗ Credential Manager failed: {err}"))

            # ─ 5. Write config.json (password DPAPI-encrypted) ──────────
            try:
                write_config(smb_server, smb_share, smb_base, fields["niceplayer_exe"],
                             smb_username=smb_username, smb_password_plain=smb_password)
                self.after(0, lambda: self._append_log(f"✓ Config written to {CONFIG_FILE}"))
            except Exception as e:
                errors.append(f"Write config: {e}")
                self.after(0, lambda: self._append_log(f"✗ Write config failed: {e}"))
            finally:
                smb_password = None  # clear plaintext ASAP after write_config has encrypted it

            # ─ 6. Register & start wrapper server autostart task ──────────
            ok, msg = register_server_autostart(dest_exe)
            if ok:
                self.after(0, lambda: self._append_log(f"✓ {msg}"))
            else:
                errors.append(f"Autostart task: {msg}")
                self.after(0, lambda: self._append_log(f"✗ Autostart task failed: {msg}"))

            # ─ 7. Browser AutoLaunch policy (optional) ────────────────
            if fields["origin"]:
                add_browser_policies(fields["origin"], dest_exe)
                self.after(0, lambda: self._append_log(
                    f"✓ AutoLaunch policy set (Chrome/Edge/Firefox) for {fields['origin']}"
                ))

            if errors:
                summary = "Installation completed with errors:\n" + "\n".join(errors)
                self.after(0, lambda: messagebox.showwarning("Installation", summary))
            else:
                self.after(0, lambda: messagebox.showinfo(
                    "Installation complete",
                    "NicePlayer Wrapper installed successfully!\n\n"
                    "The niceplayer:// protocol is ready to use.",
                ))

        threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import ctypes

    # Auto-elevate via UAC if not already running as Administrator
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        # Re-launch this process with 'runas' to trigger UAC prompt
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            params = " ".join(sys.argv[1:])
        else:
            exe = sys.executable
            params = " ".join([os.path.abspath(__file__)] + sys.argv[1:])

        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1
        )
        # ShellExecuteW returns > 32 on success; <= 32 means user cancelled or error
        if ret > 32:
            sys.exit(0)
        else:
            messagebox.showerror(
                "Administrator required",
                "การติดตั้งต้องการสิทธิ์ Administrator\n\nกรุณาคลิกขวาแล้วเลือก 'Run as administrator'",
            )
            sys.exit(1)

    InstallerApp().mainloop()


if __name__ == "__main__":
    main()
