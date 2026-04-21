"""
SeekTrack Hardware Fingerprint Collector & Attestation Agent
=============================================================
Compiled into two deliverables by build_agent.py:

  fingerprint_collector.exe  (give to customer BEFORE license exists)
      No args -> GUI: shows fingerprint hash, auto-saves fingerprint.txt
      to Desktop/seektrack_fngerprint/, customer sends the file to admin.

  seektrack.exe  (bundled INSIDE seektrack_fngerprint_Installer.exe)
      --agent [PORT]  -> local attestation HTTP agent (default port 7890)
                         Django backend queries it on every license check.
                         Raw fingerprint never leaves the machine.
      --headless      -> print hash to stdout (used internally by server.py)

Build
-----
    python build_agent.py   ->  dist/seektrack.exe   +  dist/fingerprint_collector.exe

Algorithm (same across all modes)
----------------------------------
  raw = "{FIRST_IP_ENABLED_MAC_SORTED_UPPER}|{HOSTNAME_UPPER}|{BIOS_SERIAL_TRIMMED}"
  fingerprint = sha256(raw.encode("utf-8")).hexdigest()
"""

import argparse
import hashlib
import hmac
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


# --- Hardware Queries ---------------------------------------------------------

def get_mac_addresses() -> list[str]:
    """Return a sorted list of MAC addresses for all network interfaces."""
    try:
        mac = uuid.getnode()
        primary = ':'.join(f'{(mac >> (8 * i)) & 0xFF:02x}' for i in reversed(range(6)))
        macs = {primary}
    except Exception:
        macs = set()

    if platform.system() == 'Windows':
        try:
            output = subprocess.check_output(
                ['ipconfig', '/all'], text=True, timeout=10, stderr=subprocess.DEVNULL
            )
            for line in output.splitlines():
                line = line.strip()
                if 'Physical Address' in line or 'физический адрес' in line.lower():
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        addr = parts[1].strip().replace('-', ':').lower()
                        if len(addr) == 17:
                            macs.add(addr)
        except Exception:
            pass

    return sorted(macs)


def get_hostname() -> str:
    return socket.gethostname()


def get_bios_serial() -> str:
    if platform.system() == 'Windows':
        try:
            output = subprocess.check_output(
                ['wmic', 'bios', 'get', 'serialnumber'],
                text=True, timeout=10, stderr=subprocess.DEVNULL
            )
            lines = [l.strip() for l in output.splitlines()
                     if l.strip() and l.strip().lower() != 'serialnumber']
            if lines:
                return lines[0]
        except Exception:
            pass

        try:
            output = subprocess.check_output(
                ['powershell', '-Command',
                 '(Get-WmiObject -Class Win32_BIOS).SerialNumber'],
                text=True, timeout=10, stderr=subprocess.DEVNULL
            )
            serial = output.strip()
            if serial:
                return serial
        except Exception:
            pass

    elif platform.system() == 'Linux':
        try:
            output = subprocess.check_output(
                ['sudo', 'dmidecode', '-s', 'system-serial-number'],
                text=True, timeout=10, stderr=subprocess.DEVNULL
            )
            serial = output.strip()
            if serial and serial.lower() not in ('not specified', 'none', ''):
                return serial
        except Exception:
            pass
        try:
            with open('/sys/class/dmi/id/product_serial') as f:
                serial = f.read().strip()
                if serial and serial.lower() not in ('not specified', 'none', ''):
                    return serial
        except Exception:
            pass

    return 'UNKNOWN'


def generate_fingerprint(mac_addresses: list[str], hostname: str, bios_serial: str) -> str:
    first_mac = mac_addresses[0].upper() if mac_addresses else ''
    raw = f"{first_mac}|{hostname.upper()}|{bios_serial.strip()}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


# --- Fingerprint Computation --------------------------------------------------

def compute_fingerprint() -> tuple[str, dict]:
    """Compute fingerprint; return (hash, info) where info['steps'] lists (label, error_or_None)."""
    # Step 1 — MAC
    mac_err = None
    try:
        mac_addresses = get_mac_addresses()
        mac_for_fp = mac_addresses[0] if mac_addresses else ''
        if not mac_for_fp:
            mac_err = 'No network interface found'
    except Exception as e:
        mac_err = str(e)
        mac_for_fp = ''

    # Step 2 — Hostname
    hostname_err = None
    try:
        hostname = get_hostname()
    except Exception as e:
        hostname_err = str(e)
        hostname = 'UNKNOWN'

    # Step 3 — BIOS
    bios_err = None
    try:
        bios = get_bios_serial()
        if bios == 'UNKNOWN':
            bios_err = 'Serial not available on this hardware'
    except Exception as e:
        bios_err = str(e)
        bios = 'UNKNOWN'

    fp = generate_fingerprint([mac_for_fp] if mac_for_fp else [], hostname, bios)
    return fp, {
        'steps': [
            ('Component 1',  mac_err),
            ('Component 2',  hostname_err),
            ('Component 3',  bios_err),
        ]
    }


# --- File Save ----------------------------------------------------------------

def save_fingerprint_file(fingerprint: str, info: dict) -> Path:
    """Save fingerprint.txt + fingerprint_log.txt to Desktop/seektrack_fngerprint/."""
    desktop = Path(os.environ.get('USERPROFILE', Path.home())) / 'Desktop'
    out_dir  = desktop / 'seektrack_fngerprint'
    out_dir.mkdir(parents=True, exist_ok=True)

    fp_file = out_dir / 'fingerprint.txt'
    fp_file.write_text(fingerprint, encoding='utf-8')

    lines = [
        'SeekTrack Fingerprint Report',
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        '---',
    ]
    for i, (label, err) in enumerate(info['steps'], 1):
        status = 'Success' if err is None else f'Error: {err}'
        lines.append(f'[{i}/4] {label:<14}: {status}')
    lines += ['---', f'Fingerprint: {fingerprint}', '']

    log_file = out_dir / 'fingerprint_log.txt'
    log_file.write_text('\n'.join(lines), encoding='utf-8')
    return fp_file


# --- GUI ----------------------------------------------------------------------

def run_gui(fingerprint: str, info: dict, saved_path: Path) -> None:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title('SeekTrack \u2014 Hardware Fingerprint Collector')
    root.resizable(False, False)

    try:
        logo_path = (
            Path(sys._MEIPASS) / 'logo-nichtel.png'
            if getattr(sys, 'frozen', False)
            else Path(__file__).resolve().parent / 'images' / 'logo-nichtel.png'
        )
        if logo_path.exists():
            img = tk.PhotoImage(file=str(logo_path))
            root.iconphoto(True, img)
            tk.Label(root, image=img).pack(pady=(20, 0))
            root._img = img
    except Exception:
        pass

    tk.Label(root, text='SeekTrack Hardware Fingerprint',
             font=('Segoe UI', 14, 'bold'), fg='#1a1a2e').pack(pady=(16, 2))
    tk.Label(root, text='\u0e2a\u0e48\u0e07\u0e44\u0e1f\u0e25\u0e4c fingerprint.txt \u0e43\u0e2b\u0e49 Admin \u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2d\u0e2d\u0e01 License',
             font=('Segoe UI', 10), fg='#555').pack()

    hf = ttk.LabelFrame(root, text='Fingerprint Hash', padding=12)
    hf.pack(fill='x', padx=24, pady=(12, 0))
    fp_var = tk.StringVar(value=fingerprint)
    e = ttk.Entry(hf, textvariable=fp_var, font=('Courier New', 10), width=68, state='readonly')
    e.pack(side='left', fill='x', expand=True, ipady=5)

    def copy_hash():
        root.clipboard_clear()
        root.clipboard_append(fingerprint)
        cb.config(text='\u2713 Copied!')
        root.after(2000, lambda: cb.config(text='Copy'))

    cb = ttk.Button(hf, text='Copy', command=copy_hash, width=8)
    cb.pack(side='left', padx=(8, 0))

    sf = ttk.LabelFrame(root, text='Saved File', padding=12)
    sf.pack(fill='x', padx=24, pady=(8, 0))
    saved_var = tk.StringVar(value=str(saved_path))
    ttk.Entry(sf, textvariable=saved_var,
              font=('Consolas', 9), width=68, state='readonly').pack(
        side='left', fill='x', expand=True, ipady=4)
    ttk.Button(sf, text='Open Folder', width=12,
               command=lambda: subprocess.Popen(['explorer', str(saved_path.parent)])
               ).pack(side='left', padx=(8, 0))

    df = ttk.LabelFrame(root, text='Hardware Status', padding=12)
    df.pack(fill='x', padx=24, pady=(8, 0))
    for lbl, err in info['steps']:
        ok = err is None
        row = ttk.Frame(df)
        row.pack(fill='x', pady=2)
        ttk.Label(row, text=f'{lbl}:', width=14,
                  font=('Segoe UI', 9, 'bold')).pack(side='left')
        ttk.Label(row,
                  text='✓ Success' if ok else f'✗ Error: {err}',
                  font=('Segoe UI', 9),
                  foreground='#2a7a2a' if ok else '#cc0000').pack(side='left')

    ttk.Button(root, text='Close', command=root.destroy, width=12).pack(pady=(12, 20))
    root.mainloop()


# --- Attestation Agent -------------------------------------------------------

def run_agent(port: int) -> None:
    """
    Local HTTP attestation agent (seektrack.exe --agent mode).

    POST /attest  {nonce: str, ts: float}  ->  {token: HMAC-SHA256 hex}
    token = HMAC-SHA256(key=fingerprint_utf8, msg=b"{nonce}:{int(ts)}")

    Raw fingerprint NEVER transmitted over the network.
    """
    from flask import Flask, jsonify, request as freq

    _MAX_AGE = 30
    _ALLOWED = ('127.', '172.', '10.', '192.168.', '::1')
    app = Flask(__name__)

    @app.get('/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.post('/attest')
    def attest():
        remote = freq.remote_addr or ''
        if not any(remote.startswith(p) for p in _ALLOWED):
            return jsonify({'error': 'forbidden'}), 403
        data   = freq.get_json(silent=True) or {}
        nonce  = str(data.get('nonce', '')).strip()
        ts_raw = data.get('ts')
        if not nonce or ts_raw is None:
            return jsonify({'error': 'missing nonce or ts'}), 400
        try:
            ts = float(ts_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'invalid ts'}), 400
        if abs(time.time() - ts) > _MAX_AGE:
            return jsonify({'error': 'stale request'}), 400
        fp, _ = compute_fingerprint()
        token  = hmac.new(fp.encode('utf-8'),
                          f'{nonce}:{int(ts)}'.encode('utf-8'), 'sha256').hexdigest()
        return jsonify({'token': token})

    print(f'[SeekTrack Agent] Listening on 0.0.0.0:{port}')
    print('[SeekTrack Agent] Raw fingerprint computed live \u2014 never transmitted.')
    app.run(host='0.0.0.0', port=port, debug=False, threaded=False)


# --- Entry Point --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='SeekTrack Hardware Tools')
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--headless', action='store_true',
                   help='Print fingerprint to stdout and exit.')
    g.add_argument('--agent', nargs='?', const=7890, type=int, metavar='PORT',
                   help='Run as attestation agent (default port 7890).')
    args = parser.parse_args()

    if args.headless:
        fp, _ = compute_fingerprint()
        sys.stdout.write(fp)
        sys.exit(0)

    elif args.agent is not None:
        run_agent(args.agent)

    else:
        try:
            fp, info  = compute_fingerprint()
            saved     = save_fingerprint_file(fp, info)
            run_gui(fp, info, saved)
        except Exception as exc:
            try:
                import tkinter as tk
                from tkinter import messagebox
                _r = tk.Tk(); _r.withdraw()
                messagebox.showerror('SeekTrack', f'Unexpected error:\n{exc}')
                _r.destroy()
            except Exception:
                pass
            sys.exit(1)


if __name__ == '__main__':
    main()
