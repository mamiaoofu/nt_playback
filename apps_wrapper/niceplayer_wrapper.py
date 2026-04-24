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
LOGFILE = r"C:\niceplayer_wrapper\niceplayer_wrapper.log"
CONFIG_FILE = r"C:\ProgramData\niceplayer\config.json"

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

def load_config():
    """Load installer-written config.json.  Returns {} on any error."""
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
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


def run(cmd, timeout=10):
    """Run a command, masking /pass: arguments in the log."""
    cmd_for_log = []
    for c in (cmd if isinstance(cmd, list) else cmd.split()):
        cmd_for_log.append("/pass:****" if c.lower().startswith("/pass:") else c)
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


def netuse_connect(unc_share):
    """Connect to a UNC share using credentials already stored in Credential Manager."""
    return run(["net", "use", unc_share, "/persistent:no"], timeout=20)


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


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def validate_path(path, config):
    r"""
    Reject paths that do not start with the allowed UNC root defined in
    config.json (written by the installer, never contains a password).

    config example:
        {"server": "WIN-O72N8TLKRVU", "share": "Recordings"}

    Allowed root: \\WIN-O72N8TLKRVU\Recordings
    """
    server = config.get("server", "").strip()
    share = config.get("share", "").strip()

    if not server or not share:
        log("WARNING: No server/share whitelist in config. Skipping path validation.")
        return True

    allowed_root = f"\\\\{server}\\{share}".lower()
    if not path.lower().startswith(allowed_root):
        log(f"SECURITY: Rejected path '{path}' – not under '{allowed_root}'")
        return False
    return True


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
    # ── Server mode ──────────────────────────────────────────────────────────
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        log("Argument '--server' detected. Starting in server mode.")
        if not os.path.isfile(NICEPLAYER_EXE):
            log(f"FATAL: Nice Player not found at {NICEPLAYER_EXE}.")
            sys.exit(1)
        run_server()
        sys.exit(0)

    # ── Protocol-handler mode ────────────────────────────────────────────────
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

    if "path" not in qs:
        log("ERROR: No 'path' parameter in protocol URL.")
        sys.exit(1)

    path = urllib.parse.unquote(qs["path"][0]).replace("/", "\\")
    log(f"Decoded path: {path}")

    # ── Path validation ──────────────────────────────────────────────────────
    config = load_config()
    if not validate_path(path, config):
        log("SECURITY: Path rejected by whitelist. Aborting.")
        sys.exit(1)

    # ── Derive the UNC share root  (\\SERVER\SHARE) ──────────────────────────
    parts = path.split("\\")
    # parts: ["", "", "SERVER", "SHARE", ...]
    share = None
    if len(parts) > 3:
        share = "\\".join(parts[:4])   # \\SERVER\SHARE
    elif len(parts) > 2:
        share = f"\\\\{parts[2]}\\IPC$"

    # ── Connect using pre-stored Windows Credential Manager credentials ───────
    if share:
        rc, out, err = netuse_connect(share)
        log(f"netuse_connect '{share}': rc={rc}")

    time.sleep(0.2)

    try:
        if is_niceplayer_running():
            if REPLACE_OLD_FILE:
                log("Replacing old file: killing existing Nice Player")
                kill_niceplayer()
                time.sleep(0.2)
                cmd = f'cmd /c start "" "{NICEPLAYER_EXE}" "{path}"'
            else:
                log("Nice Player already running; opening file in existing instance")
                cmd = f'"{NICEPLAYER_EXE}" "{path}"'
        else:
            cmd = f'cmd /c start "" "{NICEPLAYER_EXE}" "{path}"'

        log("Launching Nice Player")
        run(cmd)
        log("Launched successfully")

    finally:
        if share:
            netuse_disconnect(share)
            log(f"net use '{share}' disconnected")


if __name__ == "__main__":
    main()

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# ----- การตั้งค่า -----
# USERNAME และ PASSWORD จะถูกรับมาจาก URL parameter แทน
USE_CMDKEY = True
USE_NETUSE = True
CLEANUP_CREDENTIAL = True
NICEPLAYER_EXE = r"C:\Program Files (x86)\NICE Systems\NICE Player Release 6\NiceApplications.Playback.GUI.exe"
LOGFILE = r"C:\niceplayer_wrapper\niceplayer_wrapper.log"
REPLACE_OLD_FILE = True   # True = kill file เก่าก่อนเปิดใหม่, False = เปิดไฟล์ใหม่ต่อในโปรแกรมที่รันอยู่
# ------------------

# ----- การตั้งค่าสำหรับ Local Server -----
LOCAL_SERVER_HOST = '127.0.0.1'
LOCAL_SERVER_PORT = 54321

last_log_pos = 0

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

def run(cmd, timeout=10):
    cmd_for_log = []
    for c in cmd if isinstance(cmd, list) else cmd.split():
        if c.lower().startswith("/pass:"):
            cmd_for_log.append("/pass:****")
        else:
            cmd_for_log.append(c)
    try:
        log(f"RUN: {' '.join(cmd_for_log)}")
        res = subprocess.run(cmd, shell=isinstance(cmd, str), check=False,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        out = res.stdout.decode(errors='ignore')
        err = res.stderr.decode(errors='ignore')
        log(f"RETURN {res.returncode}, OUT: {out}, ERR: {err}")
        return res.returncode, out, err
    except Exception as e:
        log(f"Exception: {e}")
        return 255, "", str(e)

def add_cmdkey(target, user, pwd):
    if not target.startswith("\\\\"):
        target_for_cmdkey = f"\\\\{target}"
    else:
        target_for_cmdkey = target
    return run(["cmdkey", f"/add:{target_for_cmdkey}", f"/user:{user}", f"/pass:{pwd}"])

def delete_cmdkey(target):
    if not target.startswith("\\\\"):
        target_for_cmdkey = f"\\\\{target}"
    else:
        target_for_cmdkey = target
    return run(["cmdkey", f"/delete:{target_for_cmdkey}"])

def netuse_connect(unc_path, user, pwd):
    return run(["net", "use", unc_path, pwd, f"/user:{user}", "/persistent:no"], timeout=20)

def netuse_disconnect(unc_path):
    return run(["net", "use", unc_path, "/delete", "/y"])

def is_niceplayer_running():
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            if proc.info['exe'] and os.path.normcase(proc.info['exe']) == os.path.normcase(NICEPLAYER_EXE):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def kill_niceplayer():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] and os.path.normcase(proc.info['exe']) == os.path.normcase(NICEPLAYER_EXE):
                proc.kill()
                log("Killed existing Nice Player process")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

# ----- ส่วนของ Local HTTP Server -----
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global last_log_pos
        if self.path == '/check':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            is_installed = os.path.isfile(NICEPLAYER_EXE)
            is_running = is_niceplayer_running()
            response = {'installed': is_installed, 'running': is_running}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        elif self.path == '/get_save_logs':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            logs = []
            log_path = get_niceplayer_log_path()
            
            if log_path and os.path.exists(log_path):
                try:
                    # ถ้าไฟล์ถูก truncate หรือสร้างใหม่ ให้เริ่มอ่านใหม่
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
                                    parts = line.split('|')
                                    timestamp = parts[0].strip()
                                    msg = line.split("SaveMgr.ControllerFactory file name:")[1]
                                    file_path = msg.split(";")[0].strip()
                                    logs.append({
                                        "timestamp": timestamp,
                                        "file_path": file_path
                                    })
                                except:
                                    pass
                except Exception as e:
                    log(f"Error reading log: {e}")
            
            self.wfile.write(json.dumps({"logs": logs}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

def run_server():
    global last_log_pos
    try:
        # เริ่มต้นตำแหน่งไฟล์ที่ท้ายไฟล์ เพื่อไม่ให้อ่าน Log เก่า
        log_path = get_niceplayer_log_path()
        if log_path and os.path.exists(log_path):
             last_log_pos = os.path.getsize(log_path)

        server_address = (LOCAL_SERVER_HOST, LOCAL_SERVER_PORT)
        httpd = HTTPServer(server_address, HealthCheckHandler)
        log(f"Starting local health check server on http://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}")
        httpd.serve_forever()
    except OSError as e:
        if e.winerror == 10048:
             log(f"FATAL: Port {LOCAL_SERVER_PORT} is already in use. The server cannot start.")
        else:
             log(f"FATAL: An OS error occurred while trying to start the server: {e}")
    except Exception as e:
        log(f"FATAL: An unexpected error occurred while starting the server: {e}")

# --- Decryption Helper ---
SECRET_KEY = b"9Xv2M4p7Q8r1Z3w5Y6t8B0n2V4c6X8m0L2k4J6h8F0d2S4a" # ต้องตรงกับ Server

def decrypt_credential(text):
    try:
        encrypted = base64.b64decode(text)
        decrypted = bytes(a ^ b for a, b in zip(encrypted, SECRET_KEY * (len(encrypted) // len(SECRET_KEY) + 1)))
        return decrypted.decode('utf-8')
    except Exception as e:
        log(f"Decryption error: {e}")
        return text # Fallback to original text if decryption fails

# ----- Main -----
def main():
    # Case 1: Running in Server Mode
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        log("Argument '--server' detected. Starting in server mode.")
        if not os.path.isfile(NICEPLAYER_EXE):
            log(f"FATAL: Nice Player not found at {NICEPLAYER_EXE}. Server will not start.")
            sys.exit(1)
        
        run_server()
        sys.exit(0)

    # Case 2: Running as Protocol Handler
    if len(sys.argv) < 2 or not sys.argv[1].startswith("niceplayer://"):
        log(f"Invalid argument: {sys.argv[1:]}. This script should be called by the 'niceplayer://' protocol or with '--server' argument.")
        sys.exit(1)

    log("Running in protocol handler mode.")
    raw = sys.argv[1]
    log(f"Raw arg: {raw}")

    if "kill_niceplayer" in raw:
        log("Command detected: kill_niceplayer")
        kill_niceplayer()
        log("Nice Player process killed by protocol")
        sys.exit(0)

    if raw.startswith("niceplayer://"):
        raw = raw[len("niceplayer://"):]
        log(f"Stripped: {raw}")

    parsed = urllib.parse.urlparse(raw)
    qs = urllib.parse.parse_qs(parsed.query)
    log(f"Parsed QS: {qs}")

    if "path" not in qs:
        log("No path found in QS")
        sys.exit(1)
    
    if "user" not in qs or "pass" not in qs:
        log("Username or Password not provided in QS")
        sys.exit(1)

    path = urllib.parse.unquote(qs["path"][0]).replace("/", "\\")
    
    # รับค่าที่เข้ารหัสมา แล้วทำการถอดรหัส
    username_enc = qs["user"][0]
    password_enc = qs["pass"][0]
    
    username = decrypt_credential(username_enc)
    password = decrypt_credential(password_enc)

    log(f"Decoded path: {path}")
    log(f"Decoded user: {username}") 
    # log(f"Decoded user: {username[:3]}***") # Mask username in log for security

    parts = path.split("\\")
    server = parts[2] if len(parts) > 2 else None
    share = None

    if USE_CMDKEY and server:
        add_cmdkey(server, username, password)
        log("USE_CMDKEY successfully")

    if USE_NETUSE and server:
        if len(parts) > 3:
            share = "\\".join(parts[:4])
        else:
            share = f"\\\\{server}\\IPC$"
        rc, out, err = netuse_connect(share, username, password)
        log(f"netuse_connect {share}: rc={rc}, out={out}, err={err}")

    time.sleep(0.2)

    try:
        if is_niceplayer_running():
            if REPLACE_OLD_FILE:
                log("Replacing old file: killing existing Nice Player")
                kill_niceplayer()
                time.sleep(0.2)
                cmd = f'cmd /c start "" "{NICEPLAYER_EXE}" "{path}"'
            else:
                log("Nice Player already running, opening file without killing")
                cmd = f'"{NICEPLAYER_EXE}" "{path}"'
        else:
            cmd = f'cmd /c start "" "{NICEPLAYER_EXE}" "{path}"'

        log(f"Launching Nice Player: {cmd}")
        run(cmd)
        log("Launched successfully")

    finally:
        if CLEANUP_CREDENTIAL and USE_CMDKEY and server:
            delete_cmdkey(server)
            log("Credential cleaned up")
        if USE_NETUSE and share:
            netuse_disconnect(share)
            log(f"net use {share} disconnected")

if __name__ == "__main__":
    main()
