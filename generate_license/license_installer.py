"""
SeekTrack License Installer
============================
GUI installer that customers run AFTER the admin sends them
seektrack_fngerprint_Installer.exe.

Bundled files (via PyInstaller --add-data):
    license_files/license.json
    license_files/public_key.pem
    license_files/fingerprint.txt
    seektrack.exe              ← attestation agent

On install this tool:
  1. Copies the 3 license files to the chosen backend/license/ folder.
  2. Extracts seektrack.exe to C:\\SeekTrack\\ (configurable).
  3. Registers a Windows Scheduled Task "SeekTrackAgent" that runs
     seektrack.exe --agent 7890 at system startup (as SYSTEM).
  4. Starts the task immediately so the agent is live right away.
  5. Optionally runs docker-compose up -d.
"""

import ctypes
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path


# ─── Bundle paths ─────────────────────────────────────────────────────────────

if getattr(sys, 'frozen', False):
    _BUNDLE = Path(sys._MEIPASS)
else:
    _BUNDLE = Path(__file__).resolve().parent / 'output'

LICENSE_BUNDLE_DIR = _BUNDLE / 'license_files'
AGENT_EXE_SRC      = _BUNDLE / 'seektrack.exe'
LOGO_PATH          = _BUNDLE / 'logo-nichtel.png'

LICENSE_FILES      = ['license.json', 'public_key.pem', 'fingerprint.txt']
TASK_NAME          = 'SeekTrackAgent'
AGENT_PORT         = 7890
DEFAULT_AGENT_DIR  = Path('C:/SeekTrack')


# ─── Admin elevation ──────────────────────────────────────────────────────────

def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _request_elevation():
    """Re-launch the current exe with UAC elevation."""
    exe = sys.executable
    args = ' '.join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, 'runas', exe, args, None, 1)
    sys.exit(0)


# ─── Bundle status ────────────────────────────────────────────────────────────

def check_bundle():
    """Returns (found: dict[name→Path], missing: list[str], has_agent: bool)."""
    found, missing = {}, []
    for f in LICENSE_FILES:
        p = LICENSE_BUNDLE_DIR / f
        if p.is_file():
            found[f] = p
        else:
            missing.append(f)
    has_agent = AGENT_EXE_SRC.is_file()
    return found, missing, has_agent


# ─── Agent setup ──────────────────────────────────────────────────────────────

def install_agent(agent_dir: Path) -> str:
    """
    Copy seektrack.exe to agent_dir and register/start
    a Scheduled Task that runs seektrack.exe --agent {AGENT_PORT} at startup.
    Returns an empty string on success, error message on failure.
    """
    try:
        agent_dir.mkdir(parents=True, exist_ok=True)
        dst = agent_dir / 'seektrack.exe'
        shutil.copy2(str(AGENT_EXE_SRC), str(dst))
    except Exception as e:
        return f'Failed to copy seektrack.exe: {e}'

    agent_cmd = f'"{dst}" --agent {AGENT_PORT}'

    # Delete existing task if present (suppress errors)
    subprocess.run(
        ['schtasks', '/delete', '/tn', TASK_NAME, '/f'],
        capture_output=True,
    )

    # Create scheduled task: runs as SYSTEM at system startup, highest privileges
    r = subprocess.run(
        [
            'schtasks', '/create',
            '/tn',  TASK_NAME,
            '/tr',  agent_cmd,
            '/sc',  'ONSTART',
            '/ru',  'SYSTEM',
            '/rl',  'HIGHEST',
            '/f',
        ],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return f'schtasks /create failed: {r.stderr.strip() or r.stdout.strip()}'

    # Start the task immediately (won't wait for next reboot)
    r2 = subprocess.run(
        ['schtasks', '/run', '/tn', TASK_NAME],
        capture_output=True, text=True,
    )
    if r2.returncode != 0:
        return f'schtasks /run failed: {r2.stderr.strip() or r2.stdout.strip()}'

    return ''


# ─── Docker-compose helper ────────────────────────────────────────────────────

def find_docker_compose(license_dir: Path):
    cur = license_dir.resolve()
    for _ in range(5):
        cur = cur.parent
        if (cur / 'docker-compose.yml').is_file():
            return cur
    return None


def run_docker_compose(project_dir: Path):
    for cmd in (['docker-compose', 'up', '-d'], ['docker', 'compose', 'up', '-d']):
        try:
            r = subprocess.run(cmd, cwd=str(project_dir),
                               capture_output=True, text=True, timeout=120)
            return r.returncode == 0, r.stdout + r.stderr
        except FileNotFoundError:
            continue
        except Exception as e:
            return False, str(e)
    return False, 'docker / docker-compose not found in PATH'


# ─── GUI ──────────────────────────────────────────────────────────────────────

class InstallerApp:
    BG     = '#1a1a2e'
    CARD   = '#16213e'
    ACCENT = '#4f46e5'
    TEXT   = '#e2e8f0'
    TEXT2  = '#94a3b8'

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('SeekTrack License Installer')
        root.geometry('580x560')
        root.resizable(False, False)
        root.configure(bg=self.BG)

        try:
            icon = tk.PhotoImage(file=str(LOGO_PATH))
            root.iconphoto(True, icon)
            root._icon = icon
        except Exception:
            pass

        self.found, self.missing, self.has_agent = check_bundle()
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _label(self, parent, text, font=None, fg=None, **kw):
        return tk.Label(parent, text=text,
                        font=font or ('Segoe UI', 9),
                        fg=fg or self.TEXT,
                        bg=parent.cget('bg'), **kw)

    def _card(self, title: str):
        outer = tk.Frame(self.root, bg=self.CARD, padx=14, pady=10)
        outer.pack(padx=20, pady=(6, 0), fill='x')
        self._label(outer, title, font=('Segoe UI', 10, 'bold'), anchor='w').pack(fill='x')
        return outer

    def _build_ui(self):
        # Header
        self._label(self.root, '🔐  SeekTrack License Installer',
                    font=('Segoe UI', 15, 'bold')).pack(pady=(18, 2))
        self._label(self.root, 'ติดตั้ง License และ Attestation Agent บน Windows Server',
                    fg=self.TEXT2).pack()

        # ── Bundled files status ──
        card = self._card('Bundled Files')
        for f in LICENSE_FILES:
            ok = f in self.found
            self._label(card, f'  {"✅" if ok else "❌"}  {f}',
                        font=('Consolas', 9),
                        fg='#059669' if ok else '#dc2626',
                        anchor='w').pack(fill='x')
        agent_ok = self.has_agent
        self._label(card, f'  {"✅" if agent_ok else "❌"}  seektrack.exe  (attestation agent)',
                    font=('Consolas', 9),
                    fg='#059669' if agent_ok else '#dc2626',
                    anchor='w').pack(fill='x')

        if self.missing or not agent_ok:
            missing_all = self.missing + ([] if agent_ok else ['seektrack.exe'])
            self._label(card, f'⚠  Missing: {", ".join(missing_all)}',
                        fg='#d97706', anchor='w').pack(fill='x', pady=(4, 0))

        # ── License install path ──
        lc = self._card('License Folder  (backend/license/)')
        row = tk.Frame(lc, bg=self.CARD); row.pack(fill='x', pady=(4, 0))
        self.license_path = tk.StringVar()
        tk.Entry(row, textvariable=self.license_path,
                 font=('Consolas', 9), bg='#0f0f1a', fg=self.TEXT,
                 insertbackground=self.TEXT, relief='flat', bd=4
                 ).pack(side='left', fill='x', expand=True)
        tk.Button(row, text='Browse…', command=self._browse_license,
                  font=('Segoe UI', 9), bg=self.ACCENT, fg='white',
                  relief='flat', padx=8, activebackground='#7c3aed'
                  ).pack(side='right', padx=(6, 0))

        # ── Agent install path ──
        ac = self._card('Agent Install Folder  (seektrack.exe destination)')
        arow = tk.Frame(ac, bg=self.CARD); arow.pack(fill='x', pady=(4, 0))
        self.agent_path = tk.StringVar(value=str(DEFAULT_AGENT_DIR))
        tk.Entry(arow, textvariable=self.agent_path,
                 font=('Consolas', 9), bg='#0f0f1a', fg=self.TEXT,
                 insertbackground=self.TEXT, relief='flat', bd=4
                 ).pack(side='left', fill='x', expand=True)
        tk.Button(arow, text='Browse…', command=self._browse_agent,
                  font=('Segoe UI', 9), bg=self.ACCENT, fg='white',
                  relief='flat', padx=8, activebackground='#7c3aed'
                  ).pack(side='right', padx=(6, 0))
        self._label(ac,
                    'seektrack.exe --agent will be registered as a Windows Scheduled Task (SYSTEM, autostart)',
                    font=('Segoe UI', 8), fg=self.TEXT2, anchor='w').pack(fill='x', pady=(3, 0))

        # ── Docker checkbox ──
        self.docker_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text='Run docker-compose up -d after install',
                       variable=self.docker_var,
                       font=('Segoe UI', 9), bg=self.BG, fg=self.TEXT,
                       selectcolor=self.CARD, activebackground=self.BG,
                       activeforeground=self.TEXT).pack(pady=(10, 0))

        # ── Install button ──
        self.install_btn = tk.Button(
            self.root, text='Install', command=self.install,
            font=('Segoe UI', 12, 'bold'), bg=self.ACCENT, fg='white',
            relief='flat', padx=40, pady=8, cursor='hand2',
            activebackground='#7c3aed',
        )
        self.install_btn.pack(pady=12)

        # ── Status ──
        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var,
                 font=('Segoe UI', 9), bg=self.BG, fg=self.TEXT2,
                 wraplength=540, justify='left').pack(pady=(0, 12))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse_license(self):
        d = filedialog.askdirectory(title='Select backend/license/ folder')
        if d:
            self.license_path.set(d)

    def _browse_agent(self):
        d = filedialog.askdirectory(title='Select agent install folder')
        if d:
            self.agent_path.set(d)

    def _set_status(self, msg: str):
        self.status_var.set(msg)
        self.root.update()

    # ── Install action ────────────────────────────────────────────────────────

    def install(self):
        if self.missing:
            messagebox.showerror('Missing Files',
                                 f'Cannot install — missing:\n{", ".join(self.missing)}')
            return
        if not self.has_agent:
            messagebox.showerror('Missing Agent',
                                 'seektrack.exe is not bundled in this installer.')
            return

        lic_path = self.license_path.get().strip()
        if not lic_path:
            messagebox.showwarning('No Folder', 'Please select a License Folder.')
            return

        agent_dir = Path(self.agent_path.get().strip() or str(DEFAULT_AGENT_DIR))
        license_dir = Path(lic_path)

        self.install_btn.configure(state='disabled', text='Installing…')
        errors = []

        # 1. Copy license files
        try:
            license_dir.mkdir(parents=True, exist_ok=True)
            for name, src in self.found.items():
                shutil.copy2(str(src), str(license_dir / name))
            self._set_status(f'✅ License files copied to {license_dir}')
        except Exception as e:
            errors.append(f'Copy license files: {e}')

        # 2. Install agent + scheduled task
        self._set_status(self.status_var.get() + '\n⏳ Installing attestation agent…')
        err = install_agent(agent_dir)
        if err:
            errors.append(err)
        else:
            self._set_status(
                self.status_var.get().replace('⏳ Installing attestation agent…', '') +
                f'\n✅ Agent installed → {agent_dir / "seektrack.exe"}' +
                f'\n✅ Scheduled Task "{TASK_NAME}" registered & started'
            )

        # 3. Docker (optional)
        if self.docker_var.get() and not errors:
            self._set_status(self.status_var.get() + '\n⏳ Running docker-compose up -d…')
            project_dir = find_docker_compose(license_dir)
            if project_dir:
                ok, out = run_docker_compose(project_dir)
                if ok:
                    self._set_status(self.status_var.get().replace(
                        '⏳ Running docker-compose up -d…', '') +
                        '\n✅ docker-compose up -d completed')
                else:
                    errors.append(f'docker-compose: {out[:200]}')
            else:
                self._set_status(self.status_var.get() +
                                 '\n⚠ docker-compose.yml not found — run manually')

        self.install_btn.configure(state='normal', text='Install')

        if errors:
            messagebox.showwarning('Completed with Errors',
                                   'Installation finished with errors:\n\n' +
                                   '\n'.join(errors))
        else:
            messagebox.showinfo('Success',
                                'SeekTrack License installed successfully!\n\n'
                                f'• License files  → {license_dir}\n'
                                f'• Agent          → {agent_dir / "seektrack.exe"}\n'
                                f'• Scheduled Task → {TASK_NAME}  (SYSTEM, ONSTART)\n\n'
                                'The attestation agent is now running.\n'
                                'It will start automatically on every reboot.')


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    # Request UAC elevation if not already admin (needed for schtasks /ru SYSTEM)
    if not _is_admin():
        _request_elevation()

    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
