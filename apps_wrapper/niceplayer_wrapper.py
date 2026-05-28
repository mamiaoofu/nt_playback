# niceplayer_wrapper.py
import sys
import urllib.parse
import subprocess
import os
import time
import datetime
import psutil
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# ----- Static configuration -----
NICEPLAYER_EXE = r"C:\Program Files (x86)\NICE Systems\NICE Player Release 6\NiceApplications.Playback.GUI.exe"
LOGFILE = r"C:\ProgramData\niceplayer_wrapper\niceplayer_wrapper.log"
CONFIG_FILE = r"C:\ProgramData\niceplayer_wrapper\config.json"

# True  = kill existing NicePlayer before opening a new file
# False = open new file in the already-running NicePlayer instance
REPLACE_OLD_FILE = True

# ----- Local health-check server -----
LOCAL_SERVER_HOST = '127.0.0.1'
LOCAL_SERVER_PORT = 54321

last_log_pos = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_host(server):
    """
    Resolve IP address to NetBIOS/DNS hostname if possible.
    Windows SMB requires the hostname instead of IP address in some security environments.
    """
    server = server.strip()
    import re
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', server):
        try:
            import socket
            hostname, _, _ = socket.gethostbyaddr(server)
            if hostname:
                log(f"Resolved server IP '{server}' to hostname '{hostname}'")
                return hostname
        except Exception as e:
            log(f"Could not resolve server IP '{server}': {e}")
    return server


def load_config():
    """Load installer-written config.json.  Returns {} on any error."""
    try:
        if os.path.isfile(CONFIG_FILE):
            # utf-8-sig silently strips the BOM that PowerShell adds when writing JSON
            with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
                # Clean host and extract share if it was embedded in host field (e.g. Host\Share or Host\User)
                server = cfg.get("server", "").strip()
                share = cfg.get("share", "").strip()
                username = cfg.get("smb_username", "").strip()
                if "\\" in server:
                    parts = server.split("\\", 1)
                    host = parts[0].strip()
                    suffix = parts[1].strip()
                    if suffix.lower() == username.lower():
                        # Suffix is the username, discard it from the server host
                        cfg["server"] = host
                    else:
                        # Suffix is a share name
                        cfg["server"] = host
                        if not share:
                            cfg["share"] = suffix
                else:
                    cfg["server"] = server

                # Resolve server IP to hostname to bypass Windows SMB IP security policy restrictions
                cfg["server"] = resolve_host(cfg["server"])
                return cfg
    except Exception as e:
        log(f"Could not read config file {CONFIG_FILE}: {e}")
    return {}


def get_niceplayer_log_path():
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, r"NicePlayer\Release3\NicePlayerSA.txt")
    return None


def log(msg):
    line = f"{datetime.datetime.now()} - {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"{line}\n")
    except Exception as e:
        print(f"LOG FAIL: {e} :: {msg}")
        try:
            temp_log = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "niceplayer_wrapper.log")
            with open(temp_log, "a", encoding="utf-8") as f:
                f.write(f"{line}\n")
        except Exception:
            pass


def run(cmd, timeout=10, mask_indices=None):
    """Run a command, masking sensitive arguments in the log."""
    cmd_for_log = list(cmd) if isinstance(cmd, list) else cmd.split()
    cmd_for_log = [
        ("****" if (mask_indices and i in mask_indices) or c.lower().startswith("/pass:")
         else c)
        for i, c in enumerate(cmd_for_log)
    ]
    try:
        log(f"RUN: {' '.join(cmd_for_log)}")
        res = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        out = res.stdout.decode(errors="ignore")
        err = res.stderr.decode(errors="ignore")
        log(f"RETURN {res.returncode}, OUT: {out}, ERR: {err}")
        return res.returncode, out, err
    except Exception as e:
        log(f"Exception: {e}")
        return 255, "", str(e)


def dpapi_unprotect(b64: str) -> str:
    """Decrypt a DPAPI (CRYPTPROTECT_LOCAL_MACHINE) base64-encoded blob."""
    import base64 as _b64
    import ctypes
    import ctypes.wintypes as wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    raw = _b64.b64decode(b64)
    buf = (ctypes.c_ubyte * len(raw))(*raw)
    inp = DATA_BLOB(len(raw), buf)
    out = DATA_BLOB()
    CRYPTPROTECT_LOCAL_MACHINE = 0x4
    if not ctypes.WinDLL("crypt32").CryptUnprotectData(
        ctypes.byref(inp), None, None, None, None, CRYPTPROTECT_LOCAL_MACHINE, ctypes.byref(out)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    decrypted = bytes(out.pbData[: out.cbData]).decode("utf-16-le")
    ctypes.windll.kernel32.LocalFree(out.pbData)
    return decrypted


def get_smb_credentials():
    """Return (username, password) from config.json, or ('', '') if not stored."""
    cfg = load_config()
    username = cfg.get("smb_username", "")
    password = ""
    enc = cfg.get("smb_password", "")
    if enc:
        if enc.startswith("b64:"):
            try:
                import base64 as _b64
                password = _b64.b64decode(enc[4:]).decode("utf-8")
            except Exception as e:
                log(f"b64 credential decode failed: {e}")
        else:
            try:
                password = dpapi_unprotect(enc)
            except Exception as e:
                log(f"DPAPI credential decrypt failed: {e}")
    return username, password


def netuse_connect(unc_share, username="", password=""):
    """Connect to a UNC share, passing explicit credentials if provided."""
    # Mask both the server name (index 2) and password (index 3) in logs.
    if username and password:
        return run(
            ["net", "use", unc_share, password, f"/user:{username}", "/persistent:no"],
            timeout=20,
            mask_indices={2, 3},
        )
    return run(["net", "use", unc_share, "/persistent:no"], timeout=20, mask_indices={2})


def netuse_disconnect(unc_share):
    return run(["net", "use", unc_share, "/delete", "/y"])


def is_niceplayer_running():
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if proc.info["exe"] and os.path.normcase(proc.info["exe"]) == os.path.normcase(NICEPLAYER_EXE):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def kill_niceplayer():
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if proc.info["exe"] and os.path.normcase(proc.info["exe"]) == os.path.normcase(NICEPLAYER_EXE):
                proc.kill()
                log("Killed existing Nice Player process")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def translate_local_to_unc(path, config):
    """
    Translate a server-local absolute path to a UNC path accessible from this client.

    Strategy (in order):
    1. If already a UNC path  → just resolve any IP to hostname.
    2. If the path is locally accessible  → use as-is.
    3. If the path has a drive letter (X:\\...)  → use Windows admin share X$
       e.g.  C:\\Users\\foo.nmf  →  \\\\SERVER\\C$\\Users\\foo.nmf
             D:\\Recordings\\bar.nmf  →  \\\\SERVER\\D$\\Recordings\\bar.nmf
       This works for any drive letter (C, D, E, …) automatically.
    4. Fallback: use the configured share + base_path from config.json.
    """
    server = config.get("server", "").strip()
    if not server:
        return path

    # ── 1. Already a UNC path ──────────────────────────────────────────────
    if path.startswith("\\\\"):
        parts = path.split("\\")
        if len(parts) > 2:
            host_part = parts[2]
            resolved = resolve_host(host_part)
            if resolved != host_part:
                path = "\\\\" + resolved + "\\" + "\\".join(parts[3:])
                log(f"Replaced UNC IP with resolved hostname: '{path}'")
        return path

    # ── 2. Already accessible locally ─────────────────────────────────────
    if os.path.exists(path):
        return path

    # ── 3. Drive letter path → admin share (X$) ───────────────────────────
    # Windows exposes every drive as a hidden admin share: C$, D$, E$, etc.
    # We extract the drive letter and build the UNC path automatically.
    if len(path) >= 3 and path[1] == ":" and path[2] == "\\":
        drive_letter = path[0].upper()          # e.g. "C", "D", "E"
        admin_share  = f"{drive_letter}$"       # e.g. "C$", "D$"
        rel_path     = path[3:].lstrip("\\")    # everything after "X:\"
        unc_path = f"\\\\{server}\\{admin_share}"
        if rel_path:
            unc_path = os.path.join(unc_path, rel_path)
        log(f"Translated '{path}' → '{unc_path}' (admin share {admin_share})")
        return unc_path

    # ── 4. Fallback: use configured share from config.json ─────────────────
    share     = config.get("share", "").strip()
    base_path = config.get("base_path", "").strip().rstrip("\\")
    if share:
        unc_path = f"\\\\{server}\\{share}"
        if base_path:
            unc_path = os.path.join(unc_path, base_path)
        if path:
            unc_path = os.path.join(unc_path, path.lstrip("\\"))
        log(f"Translated '{path}' → '{unc_path}' (configured share '{share}')")
        return unc_path

    return path


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def validate_path(path, config):
    r"""
    Validate that the path is a valid UNC path or drive letter path.
    """
    path_lower = path.lower()
    # Accept UNC paths (e.g., \\server\share) or drive letter paths (e.g., Z:\...)
    if path_lower.startswith("\\\\") or (len(path_lower) >= 3 and path_lower[1] == ":" and path_lower[2] == "\\"):
        return True

    log(f"SECURITY: Rejected path '{path}' – must be a UNC path or drive letter path.")
    return False


def resolve_unc_file_path(server, share, base_path, file_value):
    """
    Build and validate a UNC path for file playback.
    If direct path is missing, perform a best-effort recursive lookup under
    the configured base directory using filename match.
    """
    root = f"\\\\{server}\\{share}"
    if base_path:
        root = os.path.join(root, base_path)

    decoded = urllib.parse.unquote(file_value or "")
    normalized = decoded.replace("/", "\\").lstrip("\\")

    direct_path = os.path.join(root, normalized)
    if os.path.isfile(direct_path):
        log(f"Resolved file path directly: {direct_path}")
        return direct_path

    basename = os.path.basename(normalized)
    if not basename:
        log("ERROR: Empty filename after decode/normalize.")
        return direct_path

    target_lower = basename.lower()
    log(f"Direct file not found. Searching recursively under: {root} for '{basename}'")
    try:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if name.lower() == target_lower:
                    found = os.path.join(dirpath, name)
                    log(f"Resolved file path by recursive search: {found}")
                    return found
    except Exception as e:
        log(f"Recursive file search failed: {e}")

    log(f"File not found under configured root. Using direct candidate: {direct_path}")
    return direct_path


# ---------------------------------------------------------------------------
# Local HTTP health-check server
# ---------------------------------------------------------------------------

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global last_log_pos
        if self.path == "/check":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "installed": os.path.isfile(NICEPLAYER_EXE),
                "running": is_niceplayer_running(),
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif self.path == "/get_save_logs":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json")
            self.end_headers()

            logs = []
            log_path = get_niceplayer_log_path()
            if log_path and os.path.exists(log_path):
                try:
                    current_size = os.path.getsize(log_path)
                    if current_size < last_log_pos:
                        last_log_pos = 0
                    with open(log_path, "r", encoding="cp874", errors="ignore") as f:
                        f.seek(last_log_pos)
                        lines = f.readlines()
                        last_log_pos = f.tell()
                        for line in lines:
                            if "SaveMgr.ControllerFactory file name" in line:
                                try:
                                    parts = line.split("|")
                                    timestamp = parts[0].strip()
                                    msg = line.split("SaveMgr.ControllerFactory file name:")[1]
                                    file_path = msg.split(";")[0].strip()
                                    logs.append({"timestamp": timestamp, "file_path": file_path})
                                except Exception:
                                    pass
                except Exception as e:
                    log(f"Error reading NicePlayer log: {e}")

            self.wfile.write(json.dumps({"logs": logs}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return  # suppress default HTTP access log


def run_server():
    global last_log_pos
    try:
        log_path = get_niceplayer_log_path()
        if log_path and os.path.exists(log_path):
            last_log_pos = os.path.getsize(log_path)

        httpd = HTTPServer((LOCAL_SERVER_HOST, LOCAL_SERVER_PORT), HealthCheckHandler)
        log(f"Starting local health-check server on http://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}")
        httpd.serve_forever()
    except OSError as e:
        if getattr(e, "winerror", None) == 10048:
            log(f"FATAL: Port {LOCAL_SERVER_PORT} is already in use.")
        else:
            log(f"FATAL: OS error starting server: {e}")
    except Exception as e:
        log(f"FATAL: Unexpected error starting server: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load config.json written by the installer so NICEPLAYER_EXE can be
    # overridden without rebuilding the exe.
    global NICEPLAYER_EXE
    _cfg = load_config()
    if _cfg.get('niceplayer_exe'):
        NICEPLAYER_EXE = _cfg['niceplayer_exe']
        log(f'NICEPLAYER_EXE overridden from config: {NICEPLAYER_EXE}')

    # â”€â”€ Server mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        log("Argument '--server' detected. Starting in server mode.")
        if not os.path.isfile(NICEPLAYER_EXE):
            log(f"FATAL: Nice Player not found at {NICEPLAYER_EXE}.")
            sys.exit(1)
        # Pre-mount the SMB share at startup using explicit credentials from config.
        _pre_cfg = load_config()
        _pre_server = _pre_cfg.get('server', '')
        _pre_share  = _pre_cfg.get('share', '')
        if _pre_server and _pre_share:
            _unc = f"\\\\{_pre_server}\\{_pre_share}"
            _pre_user, _pre_pass = get_smb_credentials()
            _masked_unc = f"\\\\***\\{_pre_share}"
            log(f"Pre-mounting share at startup: {_masked_unc}")
            _rc, _out, _err = netuse_connect(_unc, _pre_user, _pre_pass)
            if _rc == 0:
                log(f"Share pre-mounted successfully: {_masked_unc}")
            else:
                log(f"Share pre-mount failed (rc={_rc}) — will retry on first play.")
        else:
            log("No server/share in config; skipping pre-mount.")
        run_server()
        sys.exit(0)

    # â”€â”€ Protocol-handler mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if len(sys.argv) < 2 or not sys.argv[1].startswith("niceplayer://"):
        log(f"Invalid argument: {sys.argv[1:]}. Expected 'niceplayer://' URL or '--server'.")
        sys.exit(1)

    log("Running in protocol-handler mode.")
    raw = sys.argv[1]
    log(f"Raw arg: {raw}")

    if "kill_niceplayer" in raw:
        log("Command detected: kill_niceplayer")
        kill_niceplayer()
        log("Nice Player process killed by protocol")
        sys.exit(0)

    if raw.startswith("niceplayer://"):
        raw = raw[len("niceplayer://"):]

    parsed = urllib.parse.urlparse(raw)
    qs = urllib.parse.parse_qs(parsed.query)
    log(f"Parsed QS keys: {list(qs.keys())}")

    # Support both ?file_name=...&file_path=... (new) and legacy parameters (?file, ?path)
    if "file_path" in qs and qs["file_path"][0].strip():
        file_path_val = urllib.parse.unquote(qs["file_path"][0]).replace("/", "\\")
        filename_val = urllib.parse.unquote(qs.get("file_name", [""])[0])
        # Join filename if not already part of file_path
        if filename_val:
            fp_clean = file_path_val.lower().replace('/', '\\')
            fn_clean = filename_val.lower().replace('/', '\\')
            if not (fp_clean.endswith('\\' + fn_clean) or fp_clean == fn_clean):
                path = os.path.join(file_path_val, filename_val)
            else:
                path = file_path_val
        else:
            path = file_path_val
        log(f"Decoded file_path: {path}")
    elif "file" in qs:
        filename = qs["file"][0]
        server   = _cfg.get("server", "").strip()
        share_n  = _cfg.get("share", "").strip()
        base     = _cfg.get("base_path", "").strip()
        if not server or not share_n:
            log("ERROR: config.json missing server/share. Re-run installer.")
            sys.exit(1)
        path = resolve_unc_file_path(server, share_n, base, filename)
        log(f"Built UNC path from config: {path}")
    elif "path" in qs:
        path = urllib.parse.unquote(qs["path"][0]).replace("/", "\\")
        log(f"Decoded path from URL: {path}")
    else:
        log("ERROR: No 'file_path', 'file' or 'path' parameter in protocol URL.")
        sys.exit(1)

    path = translate_local_to_unc(path, _cfg)

    # â”€â”€ Path validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not validate_path(path, _cfg):
        log("SECURITY: Path rejected by whitelist. Aborting.")
        sys.exit(1)

    # ── Derive the UNC share root  (\\SERVER\SHARE) ───────────────────────
    share = None
    if path.startswith("\\\\"):
        parts = path.split("\\")
        # parts: ["", "", "SERVER", "SHARE", ...]
        if len(parts) > 3:
            share = "\\".join(parts[:4])   # \\SERVER\SHARE
        elif len(parts) > 2:
            share = f"\\\\{parts[2]}\\IPC$"
    else:
        # Fallback to configured server/share to authenticate/wake up mapped drive
        server_cfg = _cfg.get("server", "").strip()
        share_cfg = _cfg.get("share", "").strip()
        _smb_user, _smb_pass = get_smb_credentials()
        if "\\" in server_cfg:
            parts_srv = server_cfg.split("\\", 1)
            server_cfg = parts_srv[0].strip()
            if not share_cfg and len(parts_srv) > 1 and parts_srv[1].strip():
                candidate = parts_srv[1].strip()
                if candidate.lower() != _smb_user.lower():
                    share_cfg = candidate
        if server_cfg:
            if share_cfg:
                share = f"\\\\{server_cfg}\\{share_cfg}"
            else:
                share = f"\\\\{server_cfg}\\IPC$"

    # ── Connect using credentials from config.json ────────────────────────
    if os.path.exists(path):
        log(f"Path '{path}' is already accessible. Skipping netuse_connect.")
        share = None

    if share:
        _smb_user, _smb_pass = get_smb_credentials()
        rc, out, err = netuse_connect(share, _smb_user, _smb_pass)
        log(f"netuse_connect '{share}': rc={rc}")

    # If the path is a drive letter path (e.g. Z:\...) and is not accessible,
    # attempt to map the drive automatically using configured server/share/base_path.
    if len(path) >= 2 and path[1] == ":" and not os.path.exists(path):
        drive_letter = path[:2].upper()
        server_cfg = _cfg.get("server", "").strip()
        share_cfg = _cfg.get("share", "").strip()
        base_cfg = _cfg.get("base_path", "").strip()
        _smb_user, _smb_pass = get_smb_credentials()
        if "\\" in server_cfg:
            parts_srv = server_cfg.split("\\", 1)
            server_cfg = parts_srv[0].strip()
            if not share_cfg and len(parts_srv) > 1 and parts_srv[1].strip():
                candidate = parts_srv[1].strip()
                if candidate.lower() != _smb_user.lower():
                    share_cfg = candidate
        if server_cfg and share_cfg:
            unc_target = f"\\\\{server_cfg}\\{share_cfg}"
            if base_cfg:
                unc_target = os.path.join(unc_target, base_cfg)
            log(f"Path '{path}' not found. Attempting to map {drive_letter} to {unc_target}...")
            # Ensure connection is established
            netuse_connect(unc_target, _smb_user, _smb_pass)
            # Map the drive
            m_rc, m_out, m_err = run(["net", "use", drive_letter, unc_target, "/persistent:no"])
            log(f"Mapped {drive_letter} to {unc_target}: rc={m_rc}")

    time.sleep(0.2)

    if is_niceplayer_running():
        if REPLACE_OLD_FILE:
            log("Replacing old file: killing existing Nice Player")
            kill_niceplayer()
            time.sleep(0.2)
        else:
            log("Nice Player already running; opening file in existing instance")

    log(f"Launching Nice Player: {NICEPLAYER_EXE} {path}")
    try:
        wdir = os.path.dirname(path)
        if not wdir or not os.path.isdir(wdir):
            wdir = None
        subprocess.Popen(f'"{NICEPLAYER_EXE}" "{path}"', cwd=wdir)
        log("Launched successfully")
    except Exception as e:
        log(f"Failed to launch Nice Player: {e}")
    # NOTE: share is intentionally NOT disconnected — cmd /c start is non-blocking
    # and NicePlayer needs the share mounted to read the file.


if __name__ == "__main__":
    main()
